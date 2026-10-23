<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { Mic, Square, Send, X } from 'lucide-vue-next'
import { api, state } from '../state'
const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string; busy?: boolean; label?: string }>(), { placeholder: '写下你的问题，也可以用语音开始…', label: '发送' })
const emit = defineEmits<{ 'update:modelValue': [value: string]; submit: [mode: string] }>()
const mode = ref<'idle'|'recording'|'transcribing'|'review'|'error'>('idle')
const error = ref(''), seconds = ref(0), showConsent = ref(false), consent = ref(false)
const starting = ref(false)
let recorder: MediaRecorder | null = null, stream: MediaStream | null = null, timer: ReturnType<typeof setInterval> | undefined
let abort: AbortController | null = null, chunks: Blob[] = [], canceled = false
let generation = 0
const inputMode = ref('text')
function release() { stream?.getTracks().forEach(t => t.stop()); stream = null; if (timer) clearInterval(timer) }
async function start() {
  error.value = ''
  if (!state.user) { error.value = '语音输入需要登录。你仍可键盘输入。'; return }
  if (!state.health?.stt_configured) { error.value = 'STT 服务尚未配置，当前可使用文字输入。'; return }
  if (!consent.value) { showConsent.value = true; return }
  if (starting.value) return
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { error.value = '浏览器不支持录音，请使用文字输入。'; return }
  const ownGeneration = ++generation
  starting.value = true
  try {
    const acquired = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (ownGeneration !== generation) { acquired.getTracks().forEach(t => t.stop()); return }
    stream = acquired
    const mime = ['audio/webm', 'audio/mp4', 'audio/ogg'].find(m => MediaRecorder.isTypeSupported(m))
    if (!mime) { release(); error.value = '此浏览器没有兼容的录音格式'; return }
    recorder = new MediaRecorder(stream, { mimeType: mime })
    chunks = []; canceled = false; seconds.value = 0
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data) }
    recorder.onstop = async () => {
      if (ownGeneration !== generation) return
      release()
      if (canceled) return
      mode.value = 'transcribing'; abort = new AbortController()
      try {
        const body = new FormData(); body.append('file', new Blob(chunks, { type: mime }), 'voice.' + mime.split('/')[1]); body.append('consent', 'true')
        const result = await api('/ai/transcriptions', { method: 'POST', body, signal: abort.signal })
        if (canceled || ownGeneration !== generation) return
        emit('update:modelValue', [props.modelValue, result.transcript].filter(Boolean).join('\n'))
        mode.value = 'review'; inputMode.value = 'voice'
      } catch (e: any) { if (!canceled && ownGeneration === generation) { mode.value = 'error'; error.value = e.message } }
      finally { chunks = [] }
    }
    recorder.start(1000); mode.value = 'recording'
    timer = setInterval(() => { seconds.value++; if (seconds.value >= 120) stop() }, 1000)
  } catch { if (ownGeneration === generation) { release(); mode.value = 'error'; error.value = '无法获取麦克风权限，请检查浏览器授权或继续键盘输入。' } }
  finally { if (ownGeneration === generation) starting.value = false }
}
function stop() { if (recorder?.state === 'recording') recorder.stop() }
function cancel() { generation++; starting.value=false; canceled = true; abort?.abort(); stop(); release(); chunks = []; mode.value = 'idle' }
function send() { if (props.modelValue.trim() && !props.busy && !['recording','transcribing'].includes(mode.value)) { emit('submit', inputMode.value); mode.value = 'idle'; inputMode.value = 'text' } }
onBeforeUnmount(cancel)
</script>
<template>
  <div class="composer">
    <label class="sr-only" :for="'composer-' + $.uid">{{ placeholder }}</label>
    <textarea :id="'composer-' + $.uid" :value="modelValue" @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" :placeholder="placeholder" rows="3" @keydown.ctrl.enter.prevent="send" :disabled="busy"></textarea>
    <div class="composer-toolbar">
      <div class="voice-tools">
        <button v-if="mode !== 'recording'" class="icon-button" type="button" @click="start" :disabled="busy || starting || mode === 'transcribing'" aria-label="开始语音输入"><Mic :size="18" /></button>
        <button v-else class="icon-button recording" @click="stop" aria-label="停止录音"><Square :size="16" /></button>
        <span class="meta">{{ mode === 'recording' ? `录音中 ${seconds}s / 120s` : mode === 'transcribing' ? '正在转写…' : mode === 'review' ? '已回填，请校对后发送' : '语音输入 · 确认后发送' }}</span>
        <button v-if="['recording','transcribing'].includes(mode)" class="icon-button" @click="cancel" aria-label="取消录音"><X :size="16" /></button>
      </div>
      <button class="primary compact" @click="send" :disabled="busy || !modelValue.trim() || ['recording','transcribing'].includes(mode)">{{ busy ? '处理中…' : label }}<Send :size="14" /></button>
    </div>
    <div v-if="showConsent" class="voice-consent"><label><input v-model="consent" type="checkbox"> 我同意将本次录音发送至配置的 STT 服务，转写后不保存原音频。</label><button @click="showConsent = false; start()" :disabled="!consent">同意并开始录音</button></div>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
  </div>
</template>
