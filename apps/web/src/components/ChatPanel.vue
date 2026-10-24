<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, post, state } from '../state'
import Composer from './Composer.vue'
import Markdown from './Markdown.vue'
const props = defineProps<{ scope?: string; documentId?: string; sessionId?: string; conversationId?: string; docked?: boolean }>()
const route = useRoute(), router = useRouter()
const draft = ref(''), busy = ref(false), error = ref(''), messages = ref<any[]>([])
const conversation = ref(''), threads = ref<any[]>([]), contextAfter = ref(0), legacy = ref(false)
const scope = ref(props.scope || 'global'), documentId = ref(props.documentId || ''), sessionId = ref(props.sessionId || '')
const messageList = ref<HTMLElement>()
let generation=0
async function list() {
  const current=generation
  const rows=state.user ? await api('/ai/conversations') : []
  if(current===generation) threads.value=rows.filter((t:any) => t.scope === scope.value && (t.document_id || '') === documentId.value && (t.session_id || '') === sessionId.value)
}
function resetView() {
  generation++; busy.value=false
  conversation.value=''; messages.value=[]; draft.value=''; contextAfter.value=0; legacy.value=false
  scope.value=props.scope || 'global'; documentId.value=props.documentId || ''; sessionId.value=props.sessionId || ''
}
async function newChat() {
  resetView(); error.value=''
  if (props.conversationId) await router.replace({query:{...route.query, conversation:undefined}})
}
async function restore(id:string) {
  if (!id) return newChat()
  busy.value=true; error.value=''
  const current=generation
  try {
    const row=await api('/ai/conversations/'+id)
    if(current!==generation) return
    conversation.value=row.id; scope.value=row.scope; documentId.value=row.document_id || ''; sessionId.value=row.session_id || ''
    contextAfter.value=row.context_after || 0; legacy.value=!!row.legacy
    messages.value=row.messages.map((m:any)=>({question:m.message, turn:m.turn, ...m.response}))
    void list().catch(() => {})
  } catch(e:any) { if(current===generation) {resetView(); error.value=e.message} } finally { if(current===generation) busy.value=false }
}
async function clearContext() {
  if (!conversation.value || busy.value) return
  busy.value=true; error.value=''
  try { const row=await post('/ai/conversations/'+conversation.value+'/reset',{}); contextAfter.value=row.context_after }
  catch(e:any) {error.value=e.message} finally {busy.value=false}
}
async function remove() {
  if (!conversation.value || !window.confirm('删除此会话的所有问答和引用？此操作无法恢复。')) return
  busy.value=true; error.value=''
  try {await api('/ai/conversations/'+conversation.value,{method:'DELETE'}); threads.value=threads.value.filter(t=>t.id!==conversation.value); await newChat()}
  catch(e:any) {error.value=e.message} finally {busy.value=false}
}
async function ask() {
  if (!draft.value.trim() || busy.value || legacy.value) return
  busy.value = true; error.value = ''
  const question = draft.value
  const current=generation
  const pendingIndex=messages.value.length
  messages.value.push({question, turn:pendingIndex+1, pending:true, answer:'', citations:[]})
  draft.value=''
  try {
    const result = await post('/ai/chat', { ...state.context, message: question, scope: scope.value, document_id: documentId.value || null, session_id: sessionId.value || null, conversation_id: conversation.value || null })
    if(current!==generation) return
    conversation.value=result.conversation_id || ''; messages.value[pendingIndex]={question, turn:pendingIndex+1, ...result}
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
      <select v-if="state.user && threads.length" :value="conversation" :disabled="busy" aria-label="恢复历史会话" @change="restore(($event.target as HTMLSelectElement).value)">
        <option value="">选择历史会话</option><option v-for="thread in threads" :key="thread.id" :value="thread.id">{{thread.title}}</option>
      </select>
      <button v-if="conversation && !legacy" class="text-link" :disabled="busy" @click="clearContext">清空上下文</button>
      <button v-if="conversation" class="text-link" :disabled="busy" @click="remove">删除会话</button>
    </div>
    <div ref="messageList" class="chat-messages" role="region" aria-label="对话记录" tabindex="0">
    <p v-if="!state.user" class="meta">登录后可保存并恢复问答。访客问答仅在当前页面可见。</p>
    <p v-if="legacy" class="notice">这是旧版单条问答记录。可查看或删除；继续提问请新建会话。</p>
    <p v-if="scope !== (props.scope || 'global')" class="meta">已恢复原会话范围：{{scope}}。新建会话可回到当前页面范围。</p>
    <p v-if="contextAfter" class="notice">已清空前 {{contextAfter}} 轮的上下文。记录仍可查看，后续提问不会发送这些旧消息。</p>
    <div v-for="(message, index) in messages" :key="index" class="message-pair">
      <p class="question">{{ message.question }}</p><p v-if="message.pending" class="thinking meta" role="status">正在思考…</p><template v-else><p class="provider-label">{{ message.provider === 'mock' ? '旧版记录' : message.model }}{{message.turn <= contextAfter ? ' · 已移出上下文' : ''}}</p><Markdown class="answer chat-answer" :source="message.answer || ''" /></template>
      <div class="citations"><RouterLink v-for="c in message.citations" :key="c.chunk_id" :to="c.url + '?heading=' + encodeURIComponent(c.heading_path)">{{ c.title }} · {{ c.heading_path }} ↗</RouterLink></div>
      <p class="meta">{{ message.limitations }}</p>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
    <Composer v-if="!legacy" :key="state.user?.id || 'guest'" v-model="draft" :busy="busy" @submit="ask" />
  </div>
</template>
<style scoped>
.chat-toolbar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:24px}
.chat-toolbar select{max-width:280px;min-width:0}
.chat-messages{overflow-y:auto;overscroll-behavior:contain;overflow-wrap:anywhere;scrollbar-gutter:stable}
.chat-panel:not(.docked) .chat-messages{max-height:min(60dvh,640px)}
.docked{display:flex;flex-direction:column;flex:1;min-height:0}
.docked .chat-toolbar{flex-shrink:0}
.docked .chat-messages{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain}
.docked :deep(.composer){flex-shrink:0;margin-top:16px;max-height:55%;overflow-y:auto}
.docked :deep(.composer textarea){max-height:30dvh}
.chat-answer{white-space:normal}
.chat-answer :deep(h1),.chat-answer :deep(h2){font-size:21px;margin:20px 0 12px}
.chat-answer :deep(h3){font-size:18px;margin:16px 0 10px}
.chat-answer :deep(pre){overflow-x:auto;max-width:100%}
.thinking{padding:12px 0;color:var(--blue)}
</style>
