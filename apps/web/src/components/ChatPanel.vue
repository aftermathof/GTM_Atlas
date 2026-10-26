<script setup lang="ts">
import LoadingState from './LoadingState.vue'
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, post, state, peekHistory, deleteHistoryRecord, isHistoryDeleted } from '../state'
import ConfirmDelete from './ConfirmDelete.vue'
import Composer from './Composer.vue'
import Markdown from './Markdown.vue'
import { citationSources } from '../aiCitations'
const props = defineProps<{ scope?: string; documentId?: string; sessionId?: string; conversationId?: string; docked?: boolean }>()
const route = useRoute(), router = useRouter()
const draft = ref(''), busy = ref(false), error = ref(''), messages = ref<any[]>([])
const conversation = ref(''), threads = ref<any[]>([]), contextAfter = ref(0), legacy = ref(false)
const scope = ref(props.scope || 'global'), documentId = ref(props.documentId || ''), sessionId = ref(props.sessionId || '')
const messageList = ref<HTMLElement>()
const restoring = ref(false), showPrevious = ref(false)
const pendingDelete=ref(false)
const visibleMessages = computed(() => showPrevious.value ? messages.value : messages.value.filter(m => !m.turn || m.turn > contextAfter.value))
function shortTitle(title: string) {
  const characters = Array.from(title.replace(/\s+/g, ' ').trim())
  return characters.length > 14 ? characters.slice(0, 13).join('') + '…' : characters.join('')
}
let generation=0
async function list() {
  const current=generation
  const rows=state.user ? (peekHistory('/ai/conversations') || await api('/ai/conversations')) : []
  if(current===generation) threads.value=rows.filter((t:any) => !isHistoryDeleted(t.id) && t.scope === scope.value && (t.document_id || '') === documentId.value && (t.session_id || '') === sessionId.value)
}
function resetView() {
  pendingDelete.value=false
  generation++; busy.value=false; restoring.value=false
  conversation.value=''; messages.value=[]; draft.value=''; contextAfter.value=0; legacy.value=false; showPrevious.value=false
  scope.value=props.scope || 'global'; documentId.value=props.documentId || ''; sessionId.value=props.sessionId || ''
}
async function newChat() {
  resetView(); error.value=''
  if (props.conversationId) await router.replace({query:{...route.query, conversation:undefined}})
}
async function restore(id:string) {
  if (!id) return newChat()
  const cached=peekHistory('/ai/conversations/'+id)
  busy.value=!cached; restoring.value=!cached; error.value=''
  const current=generation
  try {
    const row=cached || await api('/ai/conversations/'+id)
    if(current!==generation) return
    conversation.value=row.id; scope.value=row.scope; documentId.value=row.document_id || ''; sessionId.value=row.session_id || ''
    showPrevious.value=false; contextAfter.value=row.context_after || 0; legacy.value=!!row.legacy
    messages.value=row.messages.map((m:any)=>({question:m.message, turn:m.turn, ...m.response}))
    void list().catch(() => {})
  } catch(e:any) { if(current===generation) {resetView(); error.value=e.message} } finally { if(current===generation) {busy.value=false; restoring.value=false} }
}
async function clearContext() {
  if (!conversation.value || busy.value) return
  const current=generation
  busy.value=true; error.value=''
  try {
    const row=await post('/ai/conversations/'+conversation.value+'/reset',{})
    if(current===generation) {contextAfter.value=row.context_after; showPrevious.value=false}
  } catch(e:any) {if(current===generation) error.value=e.message} finally {if(current===generation) busy.value=false}
}
async function remove() {
  if(!conversation.value)return
  const id=conversation.value,account=state.user?.id
  pendingDelete.value=false;error.value=''
  try {await deleteHistoryRecord({id,kind:'chat_thread'})}
  catch(e:any) {if(account===state.user?.id)error.value='删除未完成，记录已恢复：'+e.message}
}
watch(()=>state.historyRevision,()=>{
  threads.value=threads.value.filter(thread=>!isHistoryDeleted(thread.id))
  if(conversation.value && isHistoryDeleted(conversation.value))void newChat()
  else void list().catch(()=>{})
})
async function ask() {
  if (!draft.value.trim() || busy.value || legacy.value) return
  busy.value = true; error.value = ''
  const question = draft.value
  const current=generation
  const pendingIndex=messages.value.length
  const turn=Math.max(contextAfter.value, ...messages.value.map(m=>m.turn || 0)) + 1
  messages.value.push({question, turn, pending:true, answer:'', citations:[]})
  draft.value=''
  try {
    const result = await post('/ai/chat', { ...state.context, message: question, scope: scope.value, document_id: documentId.value || null, session_id: sessionId.value || null, conversation_id: conversation.value || null })
    if(current!==generation) return
    conversation.value=result.conversation_id || ''; messages.value[pendingIndex]={question, turn, ...result}
    if(conversation.value && !threads.value.some(t=>t.id===conversation.value)) threads.value.unshift({id:conversation.value,title:question.slice(0,80)})
  } catch (e: any) { if(current===generation) {messages.value.splice(pendingIndex,1); draft.value=question; error.value = e.message} } finally { if(current===generation) busy.value = false }
}
watch(()=>[props.scope,props.documentId,props.sessionId,props.conversationId,state.user?.id], async()=>{
  resetView(); error.value=''; threads.value=[]
  if(props.conversationId && state.user) await restore(props.conversationId)
  else {try {await list()} catch(e:any){error.value=e.message}}
}, {immediate:true})
async function submitQuestion(question: string) {
  if (busy.value) return
  await newChat()
  draft.value = question
  await ask()
}
defineExpose({ setQuestion: (q: string) => { draft.value = q }, submitQuestion })
watch(busy, value => { if (props.docked) state.assistantBusy = value }, {flush:'sync', immediate:true})
watch(()=>[messages.value.length,error.value,busy.value], async()=>{
  await nextTick()
  if(messageList.value) messageList.value.scrollTop=messageList.value.scrollHeight
})
</script>
<template>
  <div class="chat-panel" :class="{docked:props.docked}">
    <div class="chat-toolbar">
      <button class="secondary" :disabled="busy" @click="newChat">New chat · 新建会话</button>
      <select v-if="state.user && threads.length" :value="conversation" :title="threads.find(t=>t.id===conversation)?.title || '选择历史会话'" :disabled="busy" aria-label="恢复历史会话" @change="restore(($event.target as HTMLSelectElement).value)">
        <option value="">选择历史会话</option><option v-for="thread in threads" :key="thread.id" :value="thread.id" :title="thread.title">{{shortTitle(thread.title)}}</option>
      </select>
      <button v-if="conversation && !legacy" class="text-link" :disabled="busy" @click="clearContext">清空上下文</button>
      <button v-if="conversation" class="text-link" :disabled="busy" @click="pendingDelete=true">删除会话</button>
    </div>
    <div ref="messageList" class="chat-messages" role="region" aria-label="对话记录" tabindex="0">
    <p v-if="!state.user" class="meta">登录后可保存并恢复问答。访客问答仅在当前页面可见。</p>
    <p v-if="legacy" class="notice">这是旧版单条问答记录。可查看或删除；继续提问请新建会话。</p>
    <p v-if="scope !== (props.scope || 'global')" class="meta">已恢复原会话范围：{{scope}}。新建会话可回到当前页面范围。</p>
    <p v-if="contextAfter" class="notice">已清空前 {{contextAfter}} 轮的上下文。旧消息已从当前窗口隐藏，历史记录保留。<button class="text-link" @click="showPrevious = !showPrevious">{{ showPrevious ? '隐藏旧消息' : '查看旧消息' }}</button></p>
    <LoadingState v-if="restoring" label="正在加载历史对话…" compact />
    <div v-for="(message, index) in visibleMessages" :key="index" class="message-pair">
      <p class="question">{{ message.question }}</p><p v-if="message.pending" class="thinking meta" role="status">正在思考…</p><template v-else><p class="provider-label">{{ message.provider === 'mock' ? '旧版记录' : message.model }}{{message.turn <= contextAfter ? ' · 已移出上下文' : ''}}</p><Markdown ai class="answer chat-answer" :source="message.answer || ''" :citations="message.citations" /></template>
      <div class="citations"><RouterLink v-for="c in citationSources(message.citations)" :key="c.key" :to="c.href">{{ c.number }}. {{ c.title }} ↗</RouterLink></div>
      <p class="meta">{{ message.limitations }}</p>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
    <Composer v-if="!legacy" :key="state.user?.id || 'guest'" v-model="draft" :busy="busy" @submit="ask" />
    <ConfirmDelete v-if="pendingDelete" title="删除这个聊天记录？" :name="threads.find(t=>t.id===conversation)?.title" description="删除后无法恢复。会一并删除此会话的问答与引用。" @cancel="pendingDelete=false" @confirm="remove"/>
  </div>
</template>
<style scoped>
.chat-toolbar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:24px}
.chat-panel{min-width:0;max-width:100%}
.question{white-space:pre-wrap;overflow-wrap:anywhere}
.chat-toolbar select{width:280px;max-width:100%;min-width:0;flex:0 1 280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chat-messages{overflow-y:auto;overscroll-behavior:contain;overflow-wrap:anywhere;scrollbar-gutter:stable}
.chat-panel:not(.docked) .chat-messages{max-height:min(60dvh,640px)}
.docked{display:flex;flex-direction:column;flex:1;min-height:0}
.docked .chat-toolbar{flex-shrink:0}
.docked .chat-messages{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain}
.docked :deep(.composer){flex-shrink:0;margin-top:16px;max-height:55%;overflow-y:auto}
.docked :deep(.composer textarea){max-height:30dvh}
.chat-answer{white-space:normal;max-width:none}
.chat-answer :deep(h1),.chat-answer :deep(h2){font-size:21px;margin:20px 0 12px}
.chat-answer :deep(h3){font-size:18px;margin:16px 0 10px}
.chat-answer :deep(pre){overflow-x:auto;max-width:100%}
.thinking{padding:12px 0;color:var(--blue)}
</style>
