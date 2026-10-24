<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ArrowLeft, Check } from 'lucide-vue-next'
import { post } from '../state'
import Composer from './Composer.vue'
import Markdown from './Markdown.vue'
const props = defineProps<{ block: any; sessionId: string; baseVersionId?: string; dialogue: { turns: any[]; draft: string; original: string } }>()
const emit = defineEmits<{ close: []; accept: [text: string, original: string] }>()
const busy = ref(false), error = ref(''), content = ref<HTMLElement>(), dialog = ref<HTMLElement>()
let active = true
const previousOverflow = document.body.style.overflow
onMounted(() => { document.body.style.overflow = 'hidden'; dialog.value?.focus() })
onBeforeUnmount(() => { active = false; document.body.style.overflow = previousOverflow })
function trap(event: KeyboardEvent) {
  if (event.key === 'Escape' && !busy.value) emit('close')
  if (event.key !== 'Tab') return
  const nodes = dialog.value?.querySelectorAll<HTMLElement>('button:not(:disabled),textarea:not(:disabled),a,summary')
  if (!nodes?.length) return
  const first=nodes[0], last=nodes[nodes.length-1]
  if (event.shiftKey && document.activeElement===first) { event.preventDefault(); last.focus() }
  if (!event.shiftKey && document.activeElement===last) { event.preventDefault(); first.focus() }
}
async function ask() {
  if (busy.value || !props.dialogue.draft.trim()) return
  const message = props.dialogue.draft
  const turns = props.dialogue.turns
  busy.value = true; error.value = ''
  try {
    const result = await post(`/career/sessions/${props.sessionId}/block-dialogue`, {
      fact_ids: props.block.fact_ids, base_version_id: props.baseVersionId || null,
      draft_text: [...turns].reverse().find(t => t.text)?.text || props.dialogue.original,
      message, history: turns.slice(-12).map(t => ({ message:t.message, text:t.text, analysis:t.analysis, questions:t.questions }))
    })
    if (!active) return
    turns.push({ message, ...result }); props.dialogue.draft = ''
    await nextTick(); if (content.value) content.value.scrollTop = content.value.scrollHeight
  } catch(e:any) { if (active) error.value = e.message } finally { if (active) busy.value = false }
}
</script>
<template>
  <section ref="dialog" class="block-dialog" role="dialog" aria-modal="true" :aria-label="block.title+' · AI 改写'" tabindex="-1" @keydown="trap">
    <header><button class="text-link" :disabled="busy" @click="emit('close')"><ArrowLeft :size="16"/>返回修改与版本</button><h2>{{ block.title }}</h2><span class="meta">结合岗位 JD 与知识库 · 多轮修改</span></header>
    <div ref="content" class="block-conversation" role="region" aria-label="改写对话记录" tabindex="0">
      <details v-if="dialogue.original"><summary>查看当前原文</summary><p class="block-text">{{ dialogue.original }}</p></details>
      <p v-if="!dialogue.turns.length" class="notice">{{ dialogue.original ? '说说想突出、补充或调整什么。AI 会结合目标岗位、JD 与知识库直接给出完整候选稿，按你的反馈继续修改。' : '告诉 AI 想写的方向或目标岗位，先生成可编辑的候选稿，再一起补充完善。' }}</p>
      <article v-for="(turn,index) in dialogue.turns" :key="index" class="rewrite-turn">
        <p class="question">{{ turn.message }}</p>
        <template v-if="turn.text"><h3>修改建议</h3><p class="block-text">{{ turn.text }}</p></template>
        <template v-if="turn.analysis"><h3>分析</h3><Markdown :source="turn.analysis"/></template>
        <Markdown v-if="turn.questions" :source="turn.questions"/>
        <div v-if="turn.citations?.length" class="citations"><span class="eyebrow">岗位与知识参考</span><RouterLink v-for="c in turn.citations" :key="c.chunk_id" :to="c.url+'?heading='+encodeURIComponent(c.heading_path)" target="_blank">{{ c.title }} · {{ c.heading_path }} ↗</RouterLink></div>
        <div v-if="index===dialogue.turns.length-1 && turn.text" class="dialog-actions"><button class="text-link" :disabled="busy" @click="emit('close')">忽略</button><button class="primary" :disabled="busy" @click="emit('accept',turn.text,dialogue.original)"><Check :size="16"/>确认替换</button></div>
      </article>
      <p v-if="busy" class="notice" role="status">正在检索岗位资料并生成改写建议…</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
    <Composer v-model="dialogue.draft" :busy="busy" label="生成改写建议" placeholder="" @submit="ask"/>
  </section>
</template>
<style scoped>
.block-dialog{position:fixed;inset:0;z-index:120;background:var(--bg);padding:24px max(20px,calc((100vw - 1120px)/2));display:flex;flex-direction:column;min-width:0;outline:none}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding-bottom:18px;border-bottom:1px solid var(--line)}
header h2{font-size:22px;margin:0}
.block-conversation{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:24px 4px;scrollbar-gutter:stable}
.block-text,.question{white-space:pre-wrap;overflow-wrap:anywhere}
.block-text{font-size:15px;line-height:1.95}
.rewrite-turn{padding:20px 0;border-bottom:1px solid var(--line)}
.rewrite-turn h3{font-size:16px;white-space:nowrap;margin:20px 0 12px}
.rewrite-turn :deep(.prose){max-width:none;font-size:14px}
.dialog-actions{display:flex;justify-content:flex-end;gap:20px;align-items:center;margin-top:24px}
.dialog-actions button{white-space:nowrap;flex-shrink:0}
.block-dialog :deep(.composer){flex-shrink:0;margin-top:16px;max-height:38dvh;overflow:auto}
.block-dialog :deep(.composer textarea){min-height:70px;max-height:20dvh}
summary{cursor:pointer;color:var(--blue);font-size:13px}
@media(max-width:760px){.block-dialog{padding:16px 20px}header .meta{display:none}header h2{font-size:18px}}
</style>
