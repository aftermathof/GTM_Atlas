<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Plus, ArrowLeft, Save, Trash2, BookOpen, Bold, Italic, Heading2, List, Code2, Link, Quote, Pencil, Eye, Folder, FolderPlus } from 'lucide-vue-next'
import { api, state } from '../state'
import Markdown from '../components/Markdown.vue'
import ChatPanel from '../components/ChatPanel.vue'
import type NoteEditorType from '../components/NoteEditor.vue'
import LoadingState from '../components/LoadingState.vue'
const NoteEditor=defineAsyncComponent({loader:()=>import('../components/NoteEditor.vue'),loadingComponent:LoadingState,delay:0})
import NoteMark from '../components/NoteMark.vue'
import CardPagination from '../components/CardPagination.vue'
import ConfirmDelete from '../components/ConfirmDelete.vue'
import { cardPage } from '../features/knowledge/resourceGallery'
import { warmNote } from '../preload'
import { cachedNotes, cachedNote, cachedNoteFolders, fetchNoteFolders, fetchNotes, fetchNote, cacheSavedNote, cacheSavedNoteFolder, deleteNoteFolder, deleteNote, forgetNote, type Note } from '../features/notes/notesStore'

import { folderNotes, noteNumbers, type NoteFolder } from '../features/notes/noteFolders'

const route = useRoute(), router = useRouter()
const folders = ref<NoteFolder[]>([]), folderTitle = ref(''), creatingFolder = ref(false), folderForm = ref(false)
const folderInput = ref<HTMLInputElement>()
const pendingFolderDelete=ref<NoteFolder | null>(null)
function requestFolderDelete(folder: NoteFolder) { pendingFolderDelete.value=folder }
async function removeFolder() {
  if(!pendingFolderDelete.value)return
  const selected=pendingFolderDelete.value
  pendingFolderDelete.value=null
  const pending=deleteNoteFolder(selected)
  folders.value=cachedNoteFolders() || folders.value.filter(folder=>folder.id!==selected.id)
  cards.value=cachedNotes() || cards.value.filter(note=>note.folder_id!==selected.id)
  try {await pending} catch { /* The shared store restores the folder and its notes. */ }
}
const folderId = computed(() => typeof route.query.folder === 'string' ? route.query.folder : '')
const currentFolder = computed(() => folders.value.find(folder => folder.id === (note.value?.folder_id || folderId.value)))
const listLocation = computed(() => ({path:'/notes', query:currentFolder.value ? {folder:currentFolder.value.id} : {}}))
const newLocation = computed(() => ({path:'/notes/new', query:folderId.value ? {folder:folderId.value} : {}}))
const visibleCards = computed(() => folderNotes(cards.value, folderId.value))
async function openFolderForm() {
  folderForm.value = true; await nextTick(); folderInput.value?.focus()
}
async function createFolder() {
  if (creatingFolder.value || !folderTitle.value.trim()) return
  creatingFolder.value = true; error.value = ''
  const account = state.user?.id, current = generation
  try {
    const folder: NoteFolder = await api('/notes/folders', {method:'POST', body:JSON.stringify({title:folderTitle.value.trim()})})
    if (account !== state.user?.id || current !== generation) return
    cacheSavedNoteFolder(folder)
    folders.value = cachedNoteFolders() || [...folders.value, folder]; folderTitle.value = ''; folderForm.value = false
    await router.push({path:'/notes', query:{folder:folder.id}})
  } catch (e: any) { if (account === state.user?.id && current === generation) error.value = e.message }
  finally { creatingFolder.value = false }
}
const cards = ref<Note[]>([]), note = ref<Note | null>(null)
const title = ref(''), body = ref(''), original = ref(''), error = ref(''), loading = ref(false), saving = ref(false)
const mode = ref<'live' | 'edit' | 'preview'>('live'), showAI = ref(false)
const editor = ref<InstanceType<typeof NoteEditorType>>()
const pendingDelete = ref<Note | null>(null), deleting = ref(false), deleteError = ref(''), cancelDelete = ref<HTMLButtonElement>()
const deleteDialog = ref<HTMLElement>()
let deleteTrigger: HTMLElement | undefined
async function requestDelete(card: Note, event: Event) {
  deleteTrigger = event.currentTarget as HTMLElement
  pendingDelete.value = card; deleteError.value = ''
  await nextTick(); cancelDelete.value?.focus()
}
function closeDelete() {
  if (deleting.value) return
  pendingDelete.value = null
  nextTick(() => { if (deleteTrigger?.isConnected) deleteTrigger.focus(); else document.querySelector<HTMLElement>('.notes-hero .primary')?.focus() })
}
function trapDelete(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); closeDelete() }
  if (event.key === 'Tab') {
    const buttons = (event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('button:not(:disabled)')
    if (!buttons.length) { event.preventDefault(); deleteDialog.value?.focus(); return }
    const first = buttons[0], last = buttons[buttons.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}
async function deleteCard() {
  if (!pendingDelete.value || deleting.value) return
  const selected = pendingDelete.value
  closeDelete()
  const pending = deleteNote(selected)
  cards.value = cards.value.filter(card => card.id !== selected.id)
  if (id.value === selected.id) {
    original.value = JSON.stringify([title.value, body.value])
    void router.push(listLocation.value)
  }
  try { await pending } catch { /* The shared store restores the note and publishes the error. */ }
}
const id = computed(() => String(route.params.id || ''))
const editing = computed(() => !!id.value)
const dirty = computed(() => editing.value && JSON.stringify([title.value, body.value]) !== original.value)
const words = computed(() => body.value.replace(/\s/g, '').length)
const numbers = computed(() => noteNumbers(visibleCards.value))
const pagination = computed(() => cardPage(visibleCards.value, route.query.page))
async function changePage(page: number) {
  await router.replace({query: {...route.query, page: String(page)}})
  await nextTick(); document.querySelector('.collection-line')?.scrollIntoView({block:'start'})
}
const date = (value: string) => new Date(value).toLocaleString('zh-CN', {year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false})
let generation = 0
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''; showAI.value = false; note.value = null
  pendingDelete.value = null; pendingFolderDelete.value=null
  title.value = ''; body.value = ''; original.value = JSON.stringify(['', ''])
  try {
    folders.value = []; cards.value = []; folderForm.value = false; folderTitle.value = ''
    if (!state.user) { cards.value = []; return }
    const cachedFolders = cachedNoteFolders(), cachedCards = cachedNotes()
    const cachedRow = id.value && id.value !== 'new' ? cachedNote(id.value) : null
    folders.value = cachedFolders || []; cards.value = cachedCards || []
    if (cachedRow) {
      note.value = cachedRow; title.value = cachedRow.title; body.value = cachedRow.body
      original.value = JSON.stringify([title.value, body.value])
    }
    loading.value = id.value ? id.value !== 'new' && !cachedRow : !cachedCards
    const [folderRows, row] = await Promise.all([
      cachedFolders || fetchNoteFolders(),
      !id.value ? cachedCards || fetchNotes() : id.value === 'new' ? null : cachedRow || fetchNote(id.value),
    ])
    if (current !== generation) return
    folders.value = folderRows
    if (folderId.value && !folders.value.some(folder => folder.id === folderId.value)) throw new Error('文件夹不存在或无权访问')
    if (!id.value) {
      error.value = state.notesDeleteError
      cards.value = cachedNotes() || row as Note[]
    } else if (id.value !== 'new' && !cachedRow) {
      note.value = row as Note | null; title.value = note.value?.title || ''; body.value = note.value?.body || ''
      original.value = JSON.stringify([title.value, body.value])
    }
  } catch (e: any) { if (current === generation) error.value = e.message }
  finally { if (current === generation) loading.value = false }
}
watch(() => [id.value, folderId.value, state.user?.id], load, { immediate: true })
async function save() {
  if (saving.value || loading.value || !title.value.trim()) return
  saving.value = true; error.value = ''
  const savedTitle = title.value.trim(), savedBody = body.value, account = state.user?.id, current = generation
  try {
    const row: Note = await api('/notes' + (note.value ? '/' + note.value.id : ''), {
      method: note.value ? 'PUT' : 'POST', body: JSON.stringify({title:savedTitle, body:savedBody, folder_id:note.value ? note.value.folder_id || null : folderId.value || null, ...(note.value ? {revision:note.value.revision} : {})})
    })
    if (account !== state.user?.id || current !== generation) return
    note.value = row; cacheSavedNote(row)
    if (body.value === savedBody && title.value.trim() === savedTitle) title.value = savedTitle
    original.value = JSON.stringify([savedTitle, savedBody])
    if (id.value === 'new') { saving.value = false; await router.replace({path:'/notes/' + row.id, query:row.folder_id ? {folder:row.folder_id} : {}}) }
  } catch (e: any) { if (note.value) forgetNote(note.value.id); error.value = e.message }
  finally { saving.value = false }
}
function remove(event: Event) {
  if (!note.value || saving.value) return
  void requestDelete(note.value, event)
}
watch(() => state.notesRevision, () => {
  cards.value = cachedNotes() || cards.value
  folders.value = cachedNoteFolders() || folders.value
  error.value = state.notesDeleteError
})
function canLeave() { return !saving.value && (!dirty.value || window.confirm('笔记尚未保存，确定离开并放弃修改？')) }
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate((to, from) => (to.params.id === from.params.id && to.query.folder === from.query.folder) || canLeave())
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value || saving.value) { event.preventDefault(); event.returnValue = '' } }
window.addEventListener('beforeunload', beforeUnload)
onBeforeUnmount(() => { generation++; window.removeEventListener('beforeunload', beforeUnload) })
function insert(before: string, after = '', placeholder = '内容') {
  if (before === '**' || before === '*') editor.value?.toggle(before)
  else editor.value?.insert(before, after, placeholder)
}
function keydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save() }
}

</script>

<template>
  <section class="container notes-page" @keydown="keydown">
    <template v-if="!editing">
      <div class="notes-hero"><div><span class="eyebrow">YOUR PERSONAL KNOWLEDGE</span><h1>学习笔记</h1><p>把读过的知识，写成自己的理解。</p></div><div class="notes-create-actions"><button v-if="!folderId" class="button secondary" @click="openFolderForm"><FolderPlus :size="17"/>新建文件夹</button><RouterLink :to="newLocation" class="button primary"><Plus :size="17"/>新建笔记</RouterLink></div></div>
      <form v-if="folderForm" class="folder-form" @submit.prevent="createFolder"><label for="folder-title">文件夹名称</label><input id="folder-title" ref="folderInput" v-model="folderTitle" maxlength="160" placeholder="例如：产品营销" :disabled="creatingFolder" @keydown.esc="folderForm=false"/><button class="button primary" :disabled="creatingFolder || !folderTitle.trim()">{{ creatingFolder ? '创建中…' : '创建文件夹' }}</button><button type="button" class="text-link" :disabled="creatingFolder" @click="folderForm=false">取消</button></form>
      <nav v-if="folderId" class="folder-breadcrumb" aria-label="笔记位置"><RouterLink to="/notes"><ArrowLeft :size="15"/>全部笔记</RouterLink><span>/</span><span>{{ currentFolder?.title }}</span></nav>
      <div v-if="!loading && !folderId && folders.length" class="folder-grid"><article v-for="folder in folders" :key="folder.id" class="folder-card"><RouterLink :to="{path:'/notes',query:{folder:folder.id}}" class="folder-card-link"><Folder :size="26" :stroke-width="1.3"/><span>{{ folder.title }}</span><small>{{ folderNotes(cards, folder.id).length }} 篇笔记</small><ArrowUpRight :size="16"/></RouterLink><button class="folder-delete" :aria-label="'删除文件夹：'+folder.title" @click="requestFolderDelete(folder)"><Trash2 :size="14"/>删除</button></article></div>
      <div class="collection-line"><span>{{ currentFolder?.title || '我的笔记' }} <b>{{ visibleCards.length.toString().padStart(2, '0') }}</b></span><span>仅自己可见 · AI 可参考已保存内容</span></div>
      <p v-if="loading" class="note-message" role="status">正在整理你的笔记…</p>
      <p v-if="error" class="error" role="alert">{{ error }} <button @click="load">重新加载</button></p>
      <div v-if="!loading && visibleCards.length" class="note-grid"><article v-for="card in pagination.items" :key="card.id" class="note-card"><RouterLink :to="{path:'/notes/' + card.id,query:folderId ? {folder:folderId} : {}}" class="note-card-link" @mouseenter="warmNote(card.id,true)" @focus="warmNote(card.id,true)"><div class="note-cover"><span class="eyebrow">LEARNING NOTES</span><NoteMark/><span class="note-number">{{ numbers.get(card.id) }}</span></div><div class="note-card-content"><h2>{{ card.title }}</h2><div class="note-card-footer"><time :datetime="card.updated_at">{{ date(card.updated_at) }}</time><ArrowUpRight :size="18" aria-hidden="true"/></div></div></RouterLink><button class="note-card-delete" :aria-label="'删除笔记：'+card.title" @click="requestDelete(card,$event)"><Trash2 :size="14"/>删除</button></article></div>
      <div v-else-if="!loading && !error" class="notes-empty"><BookOpen :size="34" :stroke-width="1"/><h2>留一页，给新的理解。</h2><p>从一次学习、一个想法，或一场复盘开始。</p><RouterLink :to="newLocation" class="text-link">写下第一篇笔记 <ArrowUpRight :size="15"/></RouterLink></div>
      <CardPagination v-if="!loading" :page="pagination.page" :pages="pagination.pages" :total="pagination.total" @change="changePage"/>
    </template>
    <template v-else>
      <div class="editor-top"><RouterLink :to="listLocation" class="back-link"><ArrowLeft :size="15"/>{{ currentFolder?.title || '全部笔记' }}</RouterLink><div class="note-actions"><span class="save-status" role="status">{{ saving ? '正在保存…' : dirty ? '有未保存的修改' : note ? '已保存 · ' + date(note.updated_at) : '新笔记' }}</span><button v-if="note" class="icon-button" aria-label="删除笔记" :disabled="saving || loading" @click="remove"><Trash2 :size="17"/></button><button class="button primary" :disabled="saving || loading || !title.trim() || (!!note && !dirty)" @click="save"><Save :size="16"/>保存笔记</button></div></div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="loading" class="note-message" role="status">正在打开笔记…</p>
      <template v-else-if="!error || note || id === 'new'">
        <label class="sr-only" for="note-title">笔记标题</label><input id="note-title" v-model="title" autocomplete="off" class="note-title" placeholder="给这篇笔记一个标题" maxlength="160" :disabled="saving"/>
        <div class="editor-caption"><span>PRIVATE NOTE / MARKDOWN</span><span>{{ words.toLocaleString() }} 字</span></div>
        <div class="writing-tools"><div class="format-tools" v-show="mode !== 'preview'" @mousedown.prevent>
          <button title="标题" aria-label="插入标题" @click="insert('\n## ', '', '标题')"><Heading2 :size="17"/></button><button title="粗体 Ctrl+B" aria-label="插入粗体" @click="insert('**', '**')"><Bold :size="16"/></button><button title="斜体 Ctrl+I" aria-label="插入斜体" @click="insert('*', '*')"><Italic :size="16"/></button><button title="列表" aria-label="插入列表" @click="insert('\n- ', '', '列表项')"><List :size="18"/></button><button title="引用" aria-label="插入引用" @click="insert('\n> ', '', '引用内容')"><Quote :size="16"/></button><button title="代码块" aria-label="插入代码块" @click="insert('\n```text\n', '\n```\n', '代码')"><Code2 :size="17"/></button><button title="链接" aria-label="插入链接" @click="insert('[', '](https://)', '链接文字')"><Link :size="16"/></button>
        </div><div class="view-tools" aria-label="编辑视图"><button :class="{selected:mode==='edit'}" :aria-pressed="mode==='edit'" @click="mode='edit'"><Pencil :size="14"/>编辑</button><button :class="{selected:mode==='live'}" :aria-pressed="mode==='live'" @click="mode='live'"><Pencil :size="14"/>实时预览</button><button :class="{selected:mode==='preview'}" :aria-pressed="mode==='preview'" @click="mode='preview'"><Eye :size="14"/>阅读</button></div></div>
        <div class="writing-surface">
          <NoteEditor v-show="mode !== 'preview'" :key="id" ref="editor" v-model="body" :live="mode === 'live'" :disabled="saving"/>
          <div v-if="mode === 'preview'" class="note-reading"><Markdown :source="body" :breaks="true"/></div>
        </div>
        <div class="editor-bottom"><span>支持标题、列表、任务清单、引用、表格、代码块与链接 · Ctrl / ⌘ + S 保存</span><button class="text-link" :disabled="!note || dirty || saving" @click="showAI = !showAI">{{ showAI ? '收起 AI' : '与 AI 讨论这篇笔记' }} <ArrowUpRight :size="14"/></button></div>
        <p v-if="dirty" class="note-hint">保存后，AI 就能参考本次修改。</p>
        <section v-if="note" v-show="showAI" class="note-assistant"><h2>从记录，到理解。</h2><p>AI 检索已保存笔记的相关片段；较长笔记建议按章节提问，全站助手也可参考。</p><ChatPanel :key="note.id" scope="notes" :document-id="note.id"/></section>
      </template>
    </template>
    <ConfirmDelete v-if="pendingFolderDelete" title="删除这个文件夹？" :name="pendingFolderDelete.title" :description="'文件夹及其中 '+folderNotes(cards,pendingFolderDelete.id).length+' 篇笔记将一并删除，无法恢复。已有聊天中的引用快照会保留。'" @cancel="pendingFolderDelete=null" @confirm="removeFolder"/>
    <div v-if="pendingDelete" class="note-delete-backdrop" @click.self="closeDelete">
      <section ref="deleteDialog" class="note-delete-dialog" role="alertdialog" aria-modal="true" :aria-busy="deleting" aria-labelledby="delete-note-title" aria-describedby="delete-note-description" tabindex="-1" @keydown="trapDelete">
        <span class="eyebrow">MANAGE YOUR NOTES</span><h2 id="delete-note-title">删除这篇笔记？</h2>
        <p class="delete-note-name">{{ pendingDelete.title }}</p><p id="delete-note-description">删除后无法恢复。已有聊天中保存的笔记引用快照会保留。</p>
        <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
        <div class="delete-note-actions"><button ref="cancelDelete" class="secondary" :disabled="deleting" @click="closeDelete">取消</button><button class="primary delete-note-confirm" :disabled="deleting" @click="deleteCard">{{ deleting ? '正在删除…' : '确认删除' }}</button></div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.notes-create-actions{display:flex;gap:12px;flex-wrap:wrap}.folder-form{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:28px;padding:20px;border:1px solid var(--line)}.folder-form label{font-size:13px}.folder-form input{flex:1;min-width:140px}.folder-breadcrumb{display:flex;gap:12px;align-items:center;font-size:13px;margin-bottom:24px;overflow-wrap:anywhere}.folder-breadcrumb a{display:inline-flex;align-items:center;gap:6px;color:var(--blue)}.folder-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:32px}.folder-card{display:flex;align-items:center;gap:14px;padding:24px;border:1px solid var(--line);min-width:0}.folder-card-link{display:flex;align-items:center;gap:14px;flex:1;min-width:0}.folder-delete{display:inline-flex;align-items:center;gap:4px;flex-shrink:0;padding:6px;color:var(--muted);font-size:11px}.folder-delete:hover{color:#a52c2c;background:#a52c2c08}.folder-card:hover{border-color:var(--blue)}.folder-card svg{color:var(--blue);flex-shrink:0}.folder-card span{flex:1;overflow-wrap:anywhere}.folder-card small{color:var(--muted);white-space:nowrap;font-size:11px}
@media(max-width:1050px){.folder-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.notes-hero{flex-wrap:wrap}.notes-create-actions{width:100%}.notes-create-actions .button{margin-top:0!important}.folder-grid{grid-template-columns:1fr}.folder-card{padding:20px}}

.notes-page{padding-top:48px;padding-bottom:64px;min-height:75vh}.notes-hero{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin:14px 0 48px}.notes-hero h1{font-size:46px;font-weight:400;letter-spacing:-2px;margin:16px 0}.notes-hero p{color:var(--muted);font-size:15px}.button,.back-link,.text-link{display:inline-flex;align-items:center;gap:8px}.collection-line{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--ink);padding:18px 0 26px;font-size:12px;color:var(--muted)}.collection-line b{font-weight:400;color:var(--blue);margin-left:12px}.note-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.note-card{position:relative;border:1px solid var(--line);padding:0;min-height:260px;display:flex;flex-direction:column;justify-content:space-between;background:var(--paper,#fafaf8);transition:border-color .18s,background .18s}.note-card-link{display:flex;flex:1;flex-direction:column;min-width:0}.note-card:hover{border-color:var(--blue);background:#fff}.note-card h2{font-size:21px;line-height:1.6;font-weight:400;margin:0 0 36px;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}.note-cover{position:relative;height:112px;background:var(--gray);border-bottom:1px solid var(--line);padding:18px 24px;display:flex;align-items:flex-end;justify-content:space-between;color:var(--blue)}.note-cover .eyebrow{position:absolute;top:17px;left:24px;font-size:9px;margin:0}.note-number{font-family:var(--sans);font-size:38px;line-height:1;font-weight:200;letter-spacing:-1px}.note-cover svg{transition:transform .2s}.note-card:hover .note-cover svg{transform:translateY(-3px) rotate(-4deg)}.note-card-content{padding:24px;flex:1;display:flex;flex-direction:column;justify-content:space-between}.note-card-footer{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--muted)}.note-card svg{color:var(--blue)}.notes-empty{text-align:center;padding:72px 16px;border:1px solid var(--line)}.notes-empty svg{color:var(--blue)}.notes-empty h2{font-weight:400;font-size:26px;margin:22px 0 12px}.notes-empty p{font-size:14px;color:var(--muted);margin-bottom:28px}.text-link{color:var(--blue);font-size:13px}.editor-top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:32px}.note-actions{display:flex;align-items:center;gap:18px}.save-status{font-size:11px;color:var(--muted)}.note-title{display:block;width:100%;font-size:36px;font-weight:400;letter-spacing:-1px;line-height:1.5;border:0;background:transparent;padding:8px 0!important;outline:none;box-shadow:none}.note-title:focus{outline:none;box-shadow:none}.note-title::placeholder{color:#aaa}.editor-caption{display:flex;justify-content:space-between;margin:20px 0 28px;color:var(--muted);font-size:10px;letter-spacing:1.2px}.writing-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;border-top:1px solid var(--ink);border-bottom:1px solid var(--line);padding:10px 0;flex-wrap:wrap}.format-tools,.view-tools{display:flex;align-items:center;gap:4px}.format-tools button,.view-tools button{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px;color:var(--muted);font-size:12px}.format-tools button:hover,.view-tools button.selected{color:var(--blue);background:#002fa709}.view-tools{margin-left:auto}.writing-surface{border-bottom:1px solid var(--line);max-width:900px;margin:0 auto}.note-reading{min-height:54vh;padding:28px 8px}.note-reading :deep(blockquote){background:#002fa708;border-left:3px solid #002fa740;padding:12px 18px;margin:16px 0;color:var(--ink)}.note-reading :deep(blockquote p){margin:0}.editor-bottom{display:flex;justify-content:space-between;align-items:center;gap:24px;padding:18px 0}.editor-bottom>span,.note-hint{font-size:11px;color:var(--muted);line-height:1.8}.editor-bottom button:disabled{opacity:.4;cursor:not-allowed}.note-assistant{border-top:1px solid var(--line);margin-top:28px;padding-top:28px}.note-assistant h2{font-size:24px;font-weight:400}.note-assistant>p{font-size:13px;color:var(--muted)}.note-message{padding:48px 0;color:var(--muted)}
.note-card-delete{position:absolute;right:52px;bottom:17px;display:flex;align-items:center;gap:5px;border:0;font-size:11px;color:var(--muted);padding:7px}.note-card-delete:hover{color:#a52c2c;background:#a52c2c08}.note-delete-backdrop{position:fixed;inset:0;z-index:70;background:#0a0a0a40;display:grid;place-items:center;padding:24px}.note-delete-dialog{width:min(440px,100%);background:var(--bg);border:1px solid var(--line);padding:32px}.note-delete-dialog h2{font-size:26px;margin:18px 0}.note-delete-dialog p{font-size:13px;color:var(--muted);line-height:1.9;overflow-wrap:anywhere}.note-delete-dialog .delete-note-name{font-size:17px;color:var(--ink);margin-bottom:14px}.delete-note-actions{display:flex;justify-content:flex-end;gap:12px;margin-top:28px}.delete-note-confirm{background:#a52c2c;border-color:#a52c2c}
@media(prefers-reduced-motion:reduce){.note-cover svg{transition:none}.note-card:hover .note-cover svg{transform:none}}
@media(max-width:1050px){.note-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.notes-page{padding-top:28px}.notes-hero{align-items:flex-start;margin-bottom:32px}.notes-hero h1{font-size:34px}.notes-hero .eyebrow{font-size:9px}.notes-hero p{font-size:12px}.notes-hero .button{font-size:12px;white-space:nowrap;margin-top:24px}.collection-line{flex-wrap:wrap;font-size:11px;gap:10px}.note-grid{grid-template-columns:1fr;gap:14px}.note-card{min-height:236px}.editor-top{flex-wrap:wrap;margin-bottom:22px}.note-actions{gap:10px;margin-left:auto}.save-status{font-size:10px}.note-actions .button{font-size:12px;padding:10px}.note-title{font-size:27px}.editor-bottom{align-items:flex-start;flex-direction:column;gap:12px}.view-tools button{font-size:11px}.format-tools button{padding:7px}}
</style>
