<script setup lang="ts">
import LoadingState from '../components/LoadingState.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Search, LogOut, Trash2 } from 'lucide-vue-next'
import { api, post, state, saveSession, clearSession, historyRecords } from '../state'
import ContextPicker from '../components/ContextPicker.vue'
const route=useRoute(),router=useRouter(), email=ref(''), password=ref(''),register=ref(false), error=ref(''),success=ref(''),busy=ref(false),history=ref<any[]>([]),query=ref(String(route.query.q || '')), results=ref<any[]>([])
const page=computed(()=>String(route.params.page || 'history'))
const resumeHistory=computed(()=>route.query.kind==='career')
const mockHistory=computed(()=>route.query.kind==='mock')
const visibleHistory=computed(()=>(resumeHistory.value||mockHistory.value)?history.value.filter(item=>item.kind===route.query.kind):history.value)
const historyLoading=ref(false)
let historyRequest=0
async function load() {
  const request=++historyRequest, userId=state.user?.id
  error.value=''; historyLoading.value=false
  if (!state.user) { history.value=[]; return }
  if (page.value!=='history') return
  historyLoading.value=true
  try {
    const rows=await historyRecords()
    if(request===historyRequest && userId===state.user?.id) history.value=rows
  } catch(e:any) { if(request===historyRequest) error.value=e.message }
  finally { if(request===historyRequest) historyLoading.value=false }
}
function toggleAuth(){register.value=!register.value;error.value='';success.value='';password.value=''}
async function auth(){
  if(busy.value)return
  const registering=register.value
  busy.value=true;error.value='';success.value=''
  try{
    const r=await post('/auth/'+(registering?'register':'login'),{email:email.value,password:password.value})
    password.value=''
    if(registering){
      success.value=r.confirmation_required?r.message:'注册成功，请使用刚才的邮箱和密码登录。'
      register.value=false
      return
    }
    saveSession(r);state.user=r.user || await api('/auth/me');Object.assign(state.context,state.user.preferences)
    void historyRecords().catch(()=>{})
    const next=String(route.query.next||'/')
    await router.push(next.startsWith('/')&&!next.startsWith('//')?next:'/')
  }catch(e:any){error.value=e.message}finally{busy.value=false}
}
async function logout(){try{await post('/auth/logout',{});success.value='已退出登录'}catch(e:any){error.value='已退出此浏览器，服务端会话撤销失败：'+e.message}finally{clearSession();history.value=[]}}
async function save(){try{await api('/preferences',{method:'PUT',body:JSON.stringify(state.context)});success.value='偏好已保存，可随时修改'}catch(e:any){error.value=e.message}}
async function search(){busy.value=true;error.value='';try{results.value=(await post('/knowledge/search',{query:query.value})).items}catch(e:any){error.value=e.message}finally{busy.value=false}}
async function remove(item:any){const message=item.kind==='career'?'删除此简历会话、私有原件（若无其他会话引用）及其版本？':item.kind==='mock'?'删除此 Mock 的题目、回答与复盘？':'删除此聊天的所有问答与引用？';if(!window.confirm(message))return;const path=item.kind==='career'?'/career/sessions/':item.kind==='mock'?'/mock/sessions/':'/ai/conversations/';try{await api(path+item.id,{method:'DELETE'});await load()}catch(e:any){error.value=e.message}}
watch(()=>[route.path,state.user],load);onMounted(load)
</script>
<template><div class="container utility-page">
  <template v-if="page==='login'"><div class="auth-layout"><div><p class="eyebrow">YOUR PRIVATE WORKSPACE</p><h1 class="h-xl">让每一步，<br>都有<span class="blue">积累。</span></h1><p class="lead">保存练习、回看反馈，继续打磨你的下一步。</p></div><Transition name="auth-switch" mode="out-in"><form :key="register ? 'register' : 'login'" class="auth-form" :aria-busy="busy" @submit.prevent="auth"><p class="eyebrow">{{register?'CREATE YOUR ACCOUNT':'WELCOME BACK'}}</p><h2>{{register?'创建你的空间':'登录 GTM Atlas'}}</h2><label>邮箱<input v-model="email" required type="email" autocomplete="email" placeholder="you@example.com"></label><label>密码<input v-model="password" required type="password" :autocomplete="register?'new-password':'current-password'" placeholder="请输入密码"></label><button class="primary" :disabled="busy">{{busy?(register?'正在注册…':'正在登录…'):register?'注册':'登录'}}<ArrowUpRight :size="16"/></button><button type="button" class="text-link"  :disabled="busy" @click="toggleAuth">{{register?'已有账号？返回登录':'没有账号？创建账号'}}</button><p v-if="success" class="notice auth-feedback" role="status">{{success}}</p><p v-if="error" class="error auth-feedback" role="alert">{{error}}</p></form></Transition></div></template>
  <template v-else-if="page==='history'"><p class="eyebrow">YOUR WORK / CONTINUE WHERE YOU LEFT OFF</p><h1 class="h-xl">{{ resumeHistory ? '简历修改记录。' : mockHistory ? 'Mock 历史记录。' : '每一步，都在这里。' }}</h1><p class="lead">{{ resumeHistory ? '继续修改已有简历，或回看历史版本。' : mockHistory ? '回看已作答的题目、你的回答与 AI 改进建议。' : '继续上次的练习，或回看一次修改。' }}</p><LoadingState v-if="state.token && !state.user" label="正在验证登录状态…"/><div v-else-if="!state.user" class="empty-state">登录后查看私有历史。<RouterLink to="/login" class="text-link">登录 ↗</RouterLink></div><div v-else><LoadingState v-if="historyLoading && !visibleHistory.length" label="正在加载历史记录…"/><p v-else-if="!visibleHistory.length && !error" class="empty-state">{{ mockHistory ? '还没有 Mock 记录。去开始一次面试练习。' : '还没有历史。去开始一次面试练习，或上传你的简历。' }}</p><div v-for="item in visibleHistory" :key="item.id" class="history-row"><span class="eyebrow">{{item.kind==='mock'?'MOCK':item.kind==='career'?'RESUME':'Q&A'}}</span><RouterLink :to="item.kind==='mock'?'/interviews/mock/'+item.id+'/report':item.kind==='career'?'/career/review/'+item.id:'/learn/ask?conversation='+item.id"><h3>{{item.display_name||item.message||state.roles.find(r=>r.id===item.context?.role)?.name||'我的练习'}}<ArrowUpRight :size="17"/></h3><p class="meta">{{new Date(item.created_at).toLocaleString()}} · {{item.status||'问答记录'}}</p></RouterLink><button class="icon-button" @click="remove(item)" aria-label="删除历史记录"><Trash2 :size="17"/></button></div></div></template>
  <template v-else-if="page==='settings'"><p class="eyebrow">PREFERENCES / PRIVACY / TRANSPARENCY</p><h1 class="h-xl">了解你的工作空间。</h1><div class="settings-grid"><section><h2>我的岗位偏好</h2><ContextPicker/><label>默认语言<select v-model="state.context.language"><option value="zh-CN">中文</option><option value="en">English</option></select></label><div class="settings-actions"><button class="primary" :disabled="!state.user" @click="save">保存偏好</button></div><p class="meta">偏好仅在主动保存后持久化，不从对话中擅自提取私人信息。</p><p v-if="success && state.user" class="notice" role="status">{{success}}</p></section><section><h2>模型与服务状态</h2><dl class="service-status"><dt>文本模型</dt><dd>{{state.health?.llm_configured ? state.health.model : '未配置 · AI 暂不可用'}}</dd><dt>知识检索</dt><dd>{{state.health?.retrieval==='hybrid-rrf'?'混合检索 · RRF':'本地词法检索 · 未配置 Embedding'}}</dd><dt>语音转写</dt><dd>{{state.health?.stt_configured?'已配置独立 STT 服务':'未配置 · 键盘输入可用'}}</dd><dt>数据库</dt><dd>{{state.health?.database==='sqlite'?'SQLite · 本地开发模式':'PostgreSQL'}}</dd></dl><p class="meta">API Key 仅由服务端环境变量配置，网页不会保存或显示 Key。</p></section></div><section class="privacy-notes"><h2>你的数据，由你决定。</h2><p>简历原件、确认事实和版本属于私有数据，不进入公共知识库。可在历史页删除简历会话与文件。点击麦克风后开始录音，停止后发送至配置的 STT 服务转写，回填草稿供你校对后发送；应用默认不保存原音频。</p><p>AI 服务会将你明确选择的当前任务文本发送至配置的模型服务。提供方的数据政策需由部署者确认；未授权知识不进入索引或模型请求。</p><p>Mock 评分与简历分数仅供学习参考，不代表真实招聘结果、录用概率或官方 ATS 评分。</p><div v-if="state.user" class="settings-actions"><button class="primary logout-button" @click="logout"><LogOut :size="15"/>退出登录</button></div></section></template>
  <template v-else><p class="eyebrow">SEARCH THE ATLAS</p><h1 class="h-xl">从一个问题，<br>找到下一条线索。</h1><form class="search-field global-search" @submit.prevent="search"><Search :size="21"/><input v-model="query" placeholder="搜索知识、面经与岗位资料" aria-label="全站搜索"><button :disabled="busy">{{busy?'搜索中…':'搜索'}}</button></form><p class="meta">先展示确定性检索结果；需要解释时可打开 AI Assistant。</p><RouterLink v-for="r in results" :key="r.chunk_id" :to="r.url+'?heading='+encodeURIComponent(r.heading_path)" class="search-result"><p class="eyebrow">{{r.kind}} / {{r.heading_path}}</p><h2>{{r.title}} ↗</h2><p>{{r.text.slice(0,220)}}</p></RouterLink><p v-if="!results.length" class="empty-state">输入关键词，探索可用资料。</p></template>
  <p v-if="error && page!=='login'" class="error" role="alert">{{error}}</p><p v-if="success && page!=='login' && (page!=='settings' || !state.user)" class="notice" role="status">{{success}}</p>
</div></template>

<style scoped>
.settings-actions{display:flex;justify-content:flex-end}
.auth-switch-enter-active,.auth-switch-leave-active{transition:opacity .18s ease,transform .18s ease}
.auth-switch-enter-from{opacity:0;transform:translateY(12px)}
.auth-switch-leave-to{opacity:0;transform:translateY(-8px)}
.auth-feedback{margin:8px 0 0}
@media(prefers-reduced-motion:reduce){.auth-switch-enter-active,.auth-switch-leave-active{transition:none}.auth-switch-enter-from,.auth-switch-leave-to{transform:none}}
.logout-button{margin-top:20px;min-width:152px;min-height:48px}
</style>
