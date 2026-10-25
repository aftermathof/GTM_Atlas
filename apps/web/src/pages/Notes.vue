<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Plus, ArrowLeft, Save, Trash2, BookOpen, Bold, Italic, Heading2, List, Code2, Link, Quote, Columns2, Pencil, Eye } from 'lucide-vue-next'
import { api } from '../state'
import Markdown from '../components/Markdown.vue'
import ChatPanel from '../components/ChatPanel.vue'

type Note = { id: string; title: string; body: string; created_at: string; updated_at: string; revision: number }
const route = useRoute(), router = useRouter()
const cards = ref<Note[]>([]), note = ref<Note | null>(null)
const title = ref(''), body = ref(''), original = ref(''), error = ref(''), loading = ref(false), saving = ref(false)
const mode = ref<'split' | 'edit' | 'preview'>('split'), showAI = ref(false)
const editor = ref<HTMLTextAreaElement>(), preview = ref<HTMLElement>()
const id = computed(() => String(route.params.id || ''))
const editing = computed(() => !!id.value)
const dirty = computed(() => editing.value && JSON.stringify([title.value, body.value]) !== original.value)
const words = computed(() => body.value.replace(/\s/g, '').length)
const date = (value: string) => new Date(value).toLocaleString('zh-CN', {year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false})
let generation = 0
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''; showAI.value = false; note.value = null
  title.value = ''; body.value = ''; original.value = JSON.stringify(['', ''])
  try {
    if (!id.value) {
      const rows = await api('/notes')
      if (current === generation) cards.value = rows
    } else {
      const row: Note | null = id.value === 'new' ? null : await api('/notes/' + encodeURIComponent(id.value))
      if (current !== generation) return
      note.value = row; title.value = row?.title || ''; body.value = row?.body || ''
      original.value = JSON.stringify([title.value, body.value])
    }
  } catch (e: any) { if (current === generation) error.value = e.message }
  finally { if (current === generation) loading.value = false }
}
watch(id, load, { immediate: true })
async function save() {
  if (saving.value || loading.value || !title.value.trim()) return
  saving.value = true; error.value = ''
  const savedTitle = title.value.trim(), savedBody = body.value
  try {
    const row: Note = await api('/notes' + (note.value ? '/' + note.value.id : ''), {
      method: note.value ? 'PUT' : 'POST', body: JSON.stringify({title:savedTitle, body:savedBody, ...(note.value ? {revision:note.value.revision} : {})})
    })
    note.value = row
    if (body.value === savedBody && title.value.trim() === savedTitle) title.value = savedTitle
    original.value = JSON.stringify([savedTitle, savedBody])
    if (id.value === 'new') { saving.value = false; await router.replace('/notes/' + row.id) }
  } catch (e: any) { error.value = e.message }
  finally { saving.value = false }
}
async function remove() {
  if (!note.value || saving.value || !window.confirm('删除这篇笔记？此操作无法恢复，已有聊天中的引用快照会保留。')) return
  saving.value = true; error.value = ''
  try {
    await api('/notes/' + note.value.id, {method:'DELETE'})
    original.value = JSON.stringify([title.value, body.value])
    saving.value = false
    await router.push('/notes')
  } catch (e: any) { error.value = e.message }
  finally { saving.value = false }
}
function canLeave() { return !saving.value && (!dirty.value || window.confirm('笔记尚未保存，确定离开并放弃修改？')) }
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate((to, from) => to.params.id === from.params.id || canLeave())
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value || saving.value) { event.preventDefault(); event.returnValue = '' } }
window.addEventListener('beforeunload', beforeUnload)
onBeforeUnmount(() => { generation++; window.removeEventListener('beforeunload', beforeUnload) })
async function insert(before: string, after = '', placeholder = '内容') {
  if (saving.value) return
  const field = editor.value
  if (!field) return
  const start = field.selectionStart, end = field.selectionEnd, selected = body.value.slice(start, end) || placeholder
  body.value = body.value.slice(0, start) + before + selected + after + body.value.slice(end)
  await nextTick(); field.focus(); field.setSelectionRange(start + before.length, start + before.length + selected.length)
}
function keydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save() }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') { event.preventDefault(); void insert('**', '**') }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'i') { event.preventDefault(); void insert('*', '*') }
}
function syncPreview() {
  const source = editor.value, target = preview.value
  if (!source || !target) return
  target.scrollTop = source.scrollTop / Math.max(1, source.scrollHeight - source.clientHeight) * (target.scrollHeight - target.clientHeight)
}
</script>

<template>
  <section class="container notes-page" @keydown="keydown">
    <template v-if="!editing">
      <div class="notes-hero"><div><span class="eyebrow">YOUR PERSONAL KNOWLEDGE</span><h1>学习笔记<span class="blue-dot">.</span></h1><p>把读过的知识，写成自己的理解。</p></div><RouterLink to="/notes/new" class="button primary"><Plus :size="17"/>新建笔记</RouterLink></div>
      <div class="collection-line"><span>我的笔记 <b>{{ cards.length.toString().padStart(2, '0') }}</b></span><span>仅自己可见 · AI 可参考已保存内容</span></div>
      <p v-if="loading" class="note-message" role="status">正在整理你的笔记…</p>
      <p v-else-if="error" class="error" role="alert">{{ error }} <button @click="load">重新加载</button></p>
      <div v-else-if="cards.length" class="note-grid"><RouterLink v-for="card in cards" :key="card.id" :to="'/notes/' + card.id" class="note-card"><h2>{{ card.title }}</h2><div><time :datetime="card.updated_at">{{ date(card.updated_at) }}</time><ArrowUpRight :size="18" aria-hidden="true"/></div></RouterLink></div>
      <div v-else class="notes-empty"><BookOpen :size="34" :stroke-width="1"/><h2>留一页，给新的理解。</h2><p>从一次学习、一个想法，或一场复盘开始。</p><RouterLink to="/notes/new" class="text-link">写下第一篇笔记 <ArrowUpRight :size="15"/></RouterLink></div>
    </template>
    <template v-else>
      <div class="editor-top"><RouterLink to="/notes" class="back-link"><ArrowLeft :size="15"/>全部笔记</RouterLink><div class="note-actions"><span class="save-status" role="status">{{ saving ? '正在保存…' : dirty ? '有未保存的修改' : note ? '已保存 · ' + date(note.updated_at) : '新笔记' }}</span><button v-if="note" class="icon-button" aria-label="删除笔记" :disabled="saving || loading" @click="remove"><Trash2 :size="17"/></button><button class="button primary" :disabled="saving || loading || !title.trim() || (!!note && !dirty)" @click="save"><Save :size="16"/>保存笔记</button></div></div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="loading" class="note-message" role="status">正在打开笔记…</p>
      <template v-else-if="!error || note || id === 'new'">
        <label class="sr-only" for="note-title">笔记标题</label><input id="note-title" v-model="title" class="note-title" placeholder="给这篇笔记一个标题" maxlength="160" :disabled="saving"/>
        <div class="editor-caption"><span>PRIVATE NOTE / MARKDOWN</span><span>{{ words.toLocaleString() }} 字</span></div>
        <div class="writing-tools"><div class="format-tools" v-show="mode !== 'preview'">
          <button title="标题" aria-label="插入标题" @click="insert('\n## ', '', '标题')"><Heading2 :size="17"/></button><button title="粗体 Ctrl+B" aria-label="插入粗体" @click="insert('**', '**')"><Bold :size="16"/></button><button title="斜体 Ctrl+I" aria-label="插入斜体" @click="insert('*', '*')"><Italic :size="16"/></button><button title="列表" aria-label="插入列表" @click="insert('\n- ', '', '列表项')"><List :size="18"/></button><button title="引用" aria-label="插入引用" @click="insert('\n> ', '', '引用内容')"><Quote :size="16"/></button><button title="代码块" aria-label="插入代码块" @click="insert('\n```text\n', '\n```\n', '代码')"><Code2 :size="17"/></button><button title="链接" aria-label="插入链接" @click="insert('[', '](https://)', '链接文字')"><Link :size="16"/></button>
        </div><div class="view-tools" aria-label="编辑视图"><button :class="{selected:mode==='edit'}" :aria-pressed="mode==='edit'" @click="mode='edit'"><Pencil :size="14"/>编辑</button><button :class="{selected:mode==='split'}" :aria-pressed="mode==='split'" @click="mode='split'"><Columns2 :size="14"/>实时预览</button><button :class="{selected:mode==='preview'}" :aria-pressed="mode==='preview'" @click="mode='preview'"><Eye :size="14"/>阅读</button></div></div>
        <div class="writing-area" :class="mode"><div v-show="mode !== 'preview'" class="source-pane"><span class="pane-label">MARKDOWN</span><textarea ref="editor" v-model="body" aria-label="笔记 Markdown 正文" spellcheck="false" :disabled="saving" placeholder="从这里开始记录…&#10;&#10;## 一个值得记住的观点&#10;用 **粗体** 标出重点，用 - 整理清单。&#10;&#10;> 把知识变成自己的语言。" @scroll="syncPreview"/></div><div v-show="mode !== 'edit'" class="render-pane"><span class="pane-label">{{ mode === 'preview' ? 'READING' : 'LIVE PREVIEW' }}</span><div ref="preview" class="preview-scroll"><Markdown v-if="body.trim()" :source="body"/><p v-else class="preview-placeholder">你的想法，会在这里慢慢成形。</p></div></div></div>
        <div class="editor-bottom"><span>支持标题、列表、任务清单、引用、表格、代码块与链接 · Ctrl / ⌘ + S 保存</span><button class="text-link" :disabled="!note || dirty || saving" @click="showAI = !showAI">{{ showAI ? '收起 AI' : '与 AI 讨论这篇笔记' }} <ArrowUpRight :size="14"/></button></div>
        <p v-if="dirty" class="note-hint">保存后，AI 就能参考本次修改。</p>
        <section v-if="note" v-show="showAI" class="note-assistant"><h2>从记录，到理解。</h2><p>AI 检索已保存笔记的相关片段；较长笔记建议按章节提问，全站助手也可参考。</p><ChatPanel :key="note.id" scope="notes" :document-id="note.id"/></section>
      </template>
    </template>
  </section>
</template>

<style scoped>
.notes-page{padding-top:48px;padding-bottom:64px;min-height:75vh}.notes-hero{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin:14px 0 48px}.notes-hero h1{font-size:46px;font-weight:400;letter-spacing:-2px;margin:16px 0}.blue-dot{color:var(--blue)}.notes-hero p{color:var(--muted);font-size:15px}.button,.back-link,.text-link{display:inline-flex;align-items:center;gap:8px}.collection-line{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--ink);padding:18px 0 26px;font-size:12px;color:var(--muted)}.collection-line b{font-weight:400;color:var(--blue);margin-left:12px}.note-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.note-card{border:1px solid var(--line);padding:28px 24px 22px;min-height:194px;display:flex;flex-direction:column;justify-content:space-between;background:var(--paper,#fafaf8);transition:border-color .18s,background .18s}.note-card:hover{border-color:var(--blue);background:#fff}.note-card h2{font-size:21px;line-height:1.6;font-weight:400;margin:0 0 36px;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}.note-card>div{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--muted)}.note-card svg{color:var(--blue)}.notes-empty{text-align:center;padding:72px 16px;border:1px solid var(--line)}.notes-empty svg{color:var(--blue)}.notes-empty h2{font-weight:400;font-size:26px;margin:22px 0 12px}.notes-empty p{font-size:14px;color:var(--muted);margin-bottom:28px}.text-link{color:var(--blue);font-size:13px}.editor-top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:32px}.note-actions{display:flex;align-items:center;gap:18px}.save-status{font-size:11px;color:var(--muted)}.note-title{display:block;width:100%;font-size:36px;font-weight:400;letter-spacing:-1px;line-height:1.5;border:0;background:transparent;padding:8px 0!important;outline:none;box-shadow:none}.note-title:focus{outline:none;box-shadow:none}.note-title::placeholder{color:#aaa}.editor-caption{display:flex;justify-content:space-between;margin:20px 0 28px;color:var(--muted);font-size:10px;letter-spacing:1.2px}.writing-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;border-top:1px solid var(--ink);border-bottom:1px solid var(--line);padding:10px 0;flex-wrap:wrap}.format-tools,.view-tools{display:flex;align-items:center;gap:4px}.format-tools button,.view-tools button{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px;color:var(--muted);font-size:12px}.format-tools button:hover,.view-tools button.selected{color:var(--blue);background:#002fa709}.view-tools{margin-left:auto}.writing-area{display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid var(--line)}.writing-area.edit,.writing-area.preview{grid-template-columns:1fr}.source-pane,.render-pane{min-width:0;padding-top:16px}.source-pane{border-right:1px solid var(--line)}.edit .source-pane{border:0}.pane-label{display:block;margin-bottom:14px;color:#909089;font-size:9px;letter-spacing:1.6px}.source-pane .pane-label{padding-left:2px}.render-pane .pane-label{padding-left:28px}.source-pane textarea{display:block;width:100%;height:54vh;min-height:360px;resize:vertical;border:0;outline:0;box-shadow:none;background:transparent;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:14px;line-height:1.95;padding:0 24px 28px 0}.preview-scroll{height:54vh;min-height:360px;overflow:auto;padding:0 28px 28px;overflow-wrap:anywhere}.preview-placeholder{font-size:14px;color:#aaa}.preview .preview-scroll{max-width:800px;margin:auto}.preview .pane-label{text-align:center;padding-left:0}.editor-bottom{display:flex;justify-content:space-between;align-items:center;gap:24px;padding:18px 0}.editor-bottom>span,.note-hint{font-size:11px;color:var(--muted);line-height:1.8}.editor-bottom button:disabled{opacity:.4;cursor:not-allowed}.note-assistant{border-top:1px solid var(--line);margin-top:28px;padding-top:28px}.note-assistant h2{font-size:24px;font-weight:400}.note-assistant>p{font-size:13px;color:var(--muted)}.note-message{padding:48px 0;color:var(--muted)}
@media(max-width:1050px){.note-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.notes-page{padding-top:28px}.notes-hero{align-items:flex-start;margin-bottom:32px}.notes-hero h1{font-size:34px}.notes-hero .eyebrow{font-size:9px}.notes-hero p{font-size:12px}.notes-hero .button{font-size:12px;white-space:nowrap;margin-top:24px}.collection-line{flex-wrap:wrap;font-size:11px;gap:10px}.note-grid{grid-template-columns:1fr;gap:14px}.note-card{min-height:166px}.editor-top{flex-wrap:wrap;margin-bottom:22px}.note-actions{gap:10px;margin-left:auto}.save-status{font-size:10px}.note-actions .button{font-size:12px;padding:10px}.note-title{font-size:27px}.writing-area.split{grid-template-columns:1fr}.split .source-pane{border-right:0;border-bottom:1px solid var(--line)}.split textarea,.split .preview-scroll{height:38vh;min-height:260px}.source-pane textarea{padding-right:0}.render-pane .pane-label{padding-left:0}.preview-scroll{padding-left:0;padding-right:0}.editor-bottom{align-items:flex-start;flex-direction:column;gap:12px}.view-tools button{font-size:11px}.format-tools button{padding:7px}}
</style>
