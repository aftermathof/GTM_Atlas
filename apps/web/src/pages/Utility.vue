<script setup lang="ts">
import LoadingState from '../components/LoadingState.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, Search, LogOut, Trash2 } from 'lucide-vue-next'
import { api, post, state, saveSession, clearSession, logoutSession, historyRecords, peekHistoryRecords, deleteHistoryRecord, isHistoryDeleted } from '../state'
import ConfirmDelete from '../components/ConfirmDelete.vue'
import ContextPicker from '../components/ContextPicker.vue'
import CardPagination from '../components/CardPagination.vue'
import { cardPage } from '../features/knowledge/resourceGallery'
const route=useRoute(),router=useRouter(), email=ref(''), password=ref(''),register=ref(false), error=ref(''),success=ref(''),busy=ref(false),history=ref<any[]>([]),query=ref(String(route.query.q || '')), results=ref<any[]>([])
const recovering=ref(false), resetting=ref(false), recoveryToken=ref(''), confirmPassword=ref('')
const showPassword=ref(false)
const authStep=computed(()=>resetting.value?'reset':recovering.value?'recover':register.value?'register':'login')
const page=computed(()=>String(route.params.page || 'history'))
const resumeHistory=computed(()=>route.query.kind==='career')
const mockHistory=computed(()=>route.query.kind==='mock')
const visibleHistory=computed(()=>(resumeHistory.value||mockHistory.value)?history.value.filter(item=>item.kind===route.query.kind):history.value)
const historyPagination=computed(()=>cardPage(visibleHistory.value,route.query.page))
function changeHistoryPage(value:number){void router.replace({query:{...route.query,page:String(value)}});document.querySelector('.utility-page')?.scrollIntoView({block:'start'})}
const historyLoading=ref(false)
const pendingDelete=ref<any>(null)
let historyRequest=0
async function load() {
  const request=++historyRequest, userId=state.user?.id
  error.value=''; historyLoading.value=false
  if (!state.user) { history.value=[]; return }
  if (page.value!=='history') return
  const cached=peekHistoryRecords()
  if(cached){history.value=cached;return}
  historyLoading.value=true
  try {
    const rows=await historyRecords()
    if(request===historyRequest && userId===state.user?.id) history.value=rows
  } catch(e:any) { if(request===historyRequest) error.value=e.message }
  finally { if(request===historyRequest) historyLoading.value=false }
}
function returnToLogin(){recovering.value=false;resetting.value=false;recoveryToken.value='';register.value=false;password.value='';confirmPassword.value='';showPassword.value=false;error.value='';success.value=''}
function forgotPassword(){returnToLogin();recovering.value=true}
async function requestRecovery(){
  if(busy.value)return
  busy.value=true;error.value='';success.value=''
  try{const result=await post('/auth/request-password-reset',{email:email.value});success.value=result.message}catch(e:any){error.value=e.message}finally{busy.value=false}
}
async function resetPassword(){
  if(busy.value)return
  error.value='';success.value=''
  if(password.value!==confirmPassword.value){error.value='两次输入的密码不一致';return}
  if(!recoveryToken.value){error.value='重置链接已失效，请重新申请找回密码。';return}
  busy.value=true
  try{const result=await post('/auth/reset-password',{recovery_token:recoveryToken.value,password:password.value});clearSession();returnToLogin();success.value=result.message}catch(e:any){error.value=e.message}finally{busy.value=false}
}
async function readRecoveryLink(){
  if(page.value!=='login')return
  const params=new URLSearchParams(route.hash?.slice(1)||'')
  if(params.get('type')==='recovery' && params.get('access_token')){
    returnToLogin();recoveryToken.value=params.get('access_token')||'';resetting.value=true
    await router.replace({path:'/login'})
  }else if(params.get('error') || route.query.reset){
    forgotPassword();error.value='重置链接无效或已过期，请重新发送。'
    await router.replace({path:'/login'})
  }
}
function toggleAuth(){register.value=!register.value;error.value='';success.value='';password.value='';showPassword.value=false}
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
    await router.push('/')
  }catch(e:any){error.value=e.message}finally{busy.value=false}
}
function logout(){
  const pending=logoutSession()
  history.value=[]
  void router.replace('/login')
  void pending.catch(()=>{if(!state.token)state.notice='已退出此浏览器。服务端会话撤销暂未完成，请检查网络。'})
}
async function save(){try{await api('/preferences',{method:'PUT',body:JSON.stringify(state.context)});success.value='偏好已保存，可随时修改'}catch(e:any){error.value=e.message}}
async function search(){busy.value=true;error.value='';try{results.value=(await post('/knowledge/search',{query:query.value})).items}catch(e:any){error.value=e.message}finally{busy.value=false}}
function remove(item:any){pendingDelete.value=item}
async function confirmRemove(){
  const item=pendingDelete.value
  if(!item)return
  const account=state.user?.id, index=history.value.findIndex(row=>row.id===item.id)
  pendingDelete.value=null;error.value='';historyRequest++;historyLoading.value=false
  history.value=history.value.filter(row=>row.id!==item.id)
  try{await deleteHistoryRecord(item)}catch(e:any){
    if(account!==state.user?.id)return
    if(!history.value.some(row=>row.id===item.id))history.value.splice(Math.max(0,index),0,item)
    error.value='删除未完成，记录已恢复：'+e.message
  }
}
watch(()=>[route.path,state.user],load);onMounted(load)
watch(()=>state.historyRevision,()=>{if(page.value==='history')history.value=peekHistoryRecords() || history.value.filter(row=>!isHistoryDeleted(row.id))})
watch(()=>state.user?.id,()=>{pendingDelete.value=null})
watch(()=>route.hash,readRecoveryLink);onMounted(readRecoveryLink)
</script>
<template><div class="container utility-page" :class="{'auth-page':page==='login'}">
  <ConfirmDelete v-if="pendingDelete" :title="pendingDelete.kind==='career'?'删除这份简历记录？':pendingDelete.kind==='mock'?'删除这次 Mock 记录？':'删除这个聊天记录？'" :name="pendingDelete.display_name || pendingDelete.message || '我的练习'" :description="pendingDelete.kind==='career'?'删除后无法恢复。会一并删除会话、版本及不再被其他会话引用的私有原件。':pendingDelete.kind==='mock'?'删除后无法恢复。会一并删除本次题目、回答与复盘。':'删除后无法恢复。会一并删除此会话的问答与引用。'" @cancel="pendingDelete=null" @confirm="confirmRemove"/>
  <template v-if="page==='login'">
    <header class="auth-brand"><svg class="auth-brand-mark" viewBox="0 0 36 36" aria-hidden="true" focusable="false"><path fill="currentColor" d="M0 0h36v36H0z"/><g fill="none" stroke="#fff" stroke-linejoin="round"><path d="M7 26V12l7-3 8 3 7-3v15l-7 3-8-3-7 2Z" stroke-opacity=".55"/><path d="M14 9v15m8-12v15" stroke-opacity=".35"/><path d="m10 23 15-13m-7 0h7v7" stroke-width="2"/></g></svg><span>GTM Atlas</span><span class="auth-brand-caption">GTM 学习与求职工作台</span></header>
    <div class="auth-layout">
      <section class="auth-intro" aria-labelledby="auth-intro-title"><p class="eyebrow">YOUR PRIVATE WORKSPACE</p><h1 id="auth-intro-title" class="h-xl">让每一步，<br>都有<span class="blue">积累。</span></h1><p class="lead">保存练习、回看反馈，<br class="auth-desktop-break">继续打磨你的下一步。</p><dl class="auth-benefits"><div><dt>01 / 学习</dt><dd>梳理 GTM 知识，留下自己的笔记。</dd></div><div><dt>02 / 练习</dt><dd>从岗位 JD 出发，练习面试与表达。</dd></div><div><dt>03 / 积累</dt><dd>回看简历版本，接着上次的进度。</dd></div></dl></section>
      <Transition name="auth-switch" mode="out-in"><form :key="authStep" class="auth-form" :aria-busy="busy" aria-labelledby="auth-form-title" @submit.prevent="resetting ? resetPassword() : recovering ? requestRecovery() : auth()">
        <p class="eyebrow">{{resetting?'SET A NEW PASSWORD':recovering?'RESET YOUR PASSWORD':register?'CREATE YOUR ACCOUNT':'WELCOME BACK'}}</p>
        <h2 id="auth-form-title">{{resetting?'设置新密码':recovering?'找回密码':register?'创建你的空间':'登录 GTM Atlas'}}</h2>
        <p id="auth-description" class="auth-description">{{resetting?'设置完成后，请使用新密码重新登录。':recovering?'填写注册邮箱，我们会向你发送密码重置链接。':register?'使用邮箱注册，保存你的学习与求职记录。':'欢迎回来，继续你的学习与求职计划。'}}</p>
        <fieldset :disabled="busy" aria-describedby="auth-description">
          <legend class="sr-only">{{resetting?'新密码':recovering?'注册邮箱':'账号信息'}}</legend>
          <div v-if="!resetting" class="auth-field"><label for="auth-email">邮箱</label><input id="auth-email" v-model="email" name="email" required type="email" autocomplete="email" inputmode="email" autocapitalize="none" :spellcheck="false" placeholder="you@example.com"></div>
          <div v-if="!recovering" class="auth-field"><div class="auth-field-heading"><label for="auth-password">{{resetting?'新密码':'密码'}}</label><button v-if="!register && !resetting" type="button" class="auth-inline-link" @click="forgotPassword">忘记密码？</button></div><div class="auth-password"><input id="auth-password" v-model="password" name="password" required :type="showPassword?'text':'password'" :autocomplete="register || resetting?'new-password':'current-password'" :placeholder="resetting?'请输入新密码':'请输入密码'"><button type="button" class="auth-password-toggle" :aria-label="showPassword?'隐藏密码':'显示密码'" :aria-pressed="showPassword" aria-controls="auth-password" @click="showPassword=!showPassword">{{showPassword?'隐藏':'显示'}}</button></div></div>
          <div v-if="resetting" class="auth-field"><label for="auth-confirm-password">确认新密码</label><input id="auth-confirm-password" v-model="confirmPassword" name="confirm-password" required type="password" autocomplete="new-password" placeholder="再次输入新密码"></div>
          <p v-if="success" class="notice auth-feedback" role="status">{{success}}</p><p v-if="error" class="error auth-feedback" role="alert">{{error}}</p>
          <button type="submit" class="primary auth-submit" :disabled="busy">{{busy?(resetting?'正在更新…':recovering?'正在发送…':register?'正在注册…':'正在登录…'):resetting?'确认新密码':recovering?'发送重置链接':register?'创建账号':'登录'}}<ArrowUpRight v-if="!busy" :size="16" aria-hidden="true"/><span v-else class="auth-loading" aria-hidden="true"></span></button>
        </fieldset>
        <div class="auth-links"><button v-if="recovering || resetting" type="button" class="auth-inline-link" :disabled="busy" @click="returnToLogin">返回登录</button><template v-else><span>{{register?'已有账号？':'还没有账号？'}}</span><button type="button" class="auth-inline-link" :disabled="busy" @click="toggleAuth">{{register?'返回登录':'创建账号'}}</button></template></div>
        <p class="auth-footnote">学习笔记、练习与简历记录按账号保存。</p>
      </form></Transition>
    </div>
  </template>
  <template v-else-if="page==='history'"><RouterLink v-if="mockHistory || resumeHistory" :to="mockHistory ? '/interviews' : '/career'" class="back-link history-back"><ArrowLeft :size="15"/>{{ mockHistory ? '返回面经与 Mock' : '返回简历工作台' }}</RouterLink><p class="eyebrow">YOUR WORK / CONTINUE WHERE YOU LEFT OFF</p><h1 class="h-xl">{{ resumeHistory ? '简历修改记录。' : mockHistory ? 'Mock 历史记录。' : '每一步，都在这里。' }}</h1><p class="lead">{{ resumeHistory ? '继续修改已有简历，或回看历史版本。' : mockHistory ? '回看已作答的题目、你的回答与 AI 改进建议。' : '继续上次的练习，或回看一次修改。' }}</p><LoadingState v-if="state.token && !state.user" label="正在验证登录状态…"/><div v-else-if="!state.user" class="empty-state">登录后查看私有历史。<RouterLink to="/login" class="text-link">登录 ↗</RouterLink></div><div v-else><LoadingState v-if="historyLoading && !visibleHistory.length" label="正在加载历史记录…"/><p v-else-if="!visibleHistory.length && !error" class="empty-state">{{ mockHistory ? '还没有 Mock 记录。去开始一次面试练习。' : '还没有历史。去开始一次面试练习，或上传你的简历。' }}</p><div v-for="item in historyPagination.items" :key="item.id" class="history-row"><span class="eyebrow">{{item.kind==='mock'?'MOCK':item.kind==='career'?'RESUME':'Q&A'}}</span><RouterLink :to="item.kind==='mock'?'/interviews/mock/'+item.id+'/report':item.kind==='career'?'/career/review/'+item.id:'/learn/ask?conversation='+item.id"><h3>{{item.display_name||item.message||state.roles.find(r=>r.id===item.context?.role)?.name||'我的练习'}}<ArrowUpRight :size="17"/></h3><p class="meta">{{new Date(item.created_at).toLocaleString()}} · {{item.status||'问答记录'}}</p></RouterLink><button class="icon-button" @click="remove(item)" aria-label="删除历史记录"><Trash2 :size="17"/></button></div><CardPagination v-if="!historyLoading" :page="historyPagination.page" :pages="historyPagination.pages" :total="historyPagination.total" @change="changeHistoryPage"/></div></template>
  <template v-else-if="page==='settings'"><p class="eyebrow">PREFERENCES / PRIVACY / TRANSPARENCY</p><h1 class="h-xl">了解你的工作空间。</h1><div class="settings-grid"><section><h2>我的岗位偏好</h2><ContextPicker/><label>默认语言<select v-model="state.context.language"><option value="zh-CN">中文</option><option value="en">English</option></select></label><div class="settings-actions"><button class="primary" :disabled="!state.user" @click="save">保存偏好</button></div><p class="meta">偏好仅在主动保存后持久化，不从对话中擅自提取私人信息。</p><p v-if="success && state.user" class="notice" role="status">{{success}}</p></section><section><h2>模型与服务状态</h2><dl class="service-status"><dt>文本模型</dt><dd>{{state.health?.llm_configured ? state.health.model : '未配置 · AI 暂不可用'}}</dd><dt>知识检索</dt><dd>{{state.health?.retrieval==='hybrid-rrf'?'混合检索 · RRF':'本地词法检索 · 未配置 Embedding'}}</dd><dt>语音转写</dt><dd>{{state.health?.stt_configured?'已配置独立 STT 服务':'未配置 · 键盘输入可用'}}</dd><dt>数据库</dt><dd>{{state.health?.database==='sqlite'?'SQLite · 本地开发模式':'PostgreSQL'}}</dd></dl><p class="meta">API Key 仅由服务端环境变量配置，网页不会保存或显示 Key。</p></section></div><section class="privacy-notes"><h2>你的数据，由你决定。</h2><p>简历原件、确认事实和版本属于私有数据，不进入公共知识库。可在历史页删除简历会话与文件。点击麦克风后开始录音，停止后发送至配置的 STT 服务转写，回填草稿供你校对后发送；应用默认不保存原音频。</p><p>AI 服务会将你明确选择的当前任务文本发送至配置的模型服务。提供方的数据政策需由部署者确认；未授权知识不进入索引或模型请求。</p><p>Mock 评分与简历分数仅供学习参考，不代表真实招聘结果、录用概率或官方 ATS 评分。</p><div v-if="state.user" class="settings-actions"><button class="primary logout-button" @click="logout"><LogOut :size="15"/>退出登录</button></div></section></template>
  <template v-else><p class="eyebrow">SEARCH THE ATLAS</p><h1 class="h-xl">从一个问题，<br>找到下一条线索。</h1><form class="search-field global-search" @submit.prevent="search"><Search :size="21"/><input v-model="query" placeholder="搜索知识、面经与岗位资料" aria-label="全站搜索"><button :disabled="busy">{{busy?'搜索中…':'搜索'}}</button></form><p class="meta">先展示确定性检索结果；需要解释时可打开 AI Assistant。</p><RouterLink v-for="r in results" :key="r.chunk_id" :to="r.url+'?heading='+encodeURIComponent(r.heading_path)" class="search-result"><p class="eyebrow">{{r.kind}} / {{r.heading_path}}</p><h2>{{r.title}} ↗</h2><p>{{r.text.slice(0,220)}}</p></RouterLink><p v-if="!results.length" class="empty-state">输入关键词，探索可用资料。</p></template>
  <p v-if="error && page!=='login'" class="error" role="alert">{{error}}</p><p v-if="success && page!=='login' && (page!=='settings' || !state.user)" class="notice" role="status">{{success}}</p>
</div></template>

<style scoped>
.auth-page{padding-top:32px;padding-bottom:48px;min-height:100svh}
.auth-brand{display:flex;align-items:center;gap:12px;font-family:var(--sans);font-size:20px;font-weight:600;line-height:28px}
.auth-brand-mark{width:32px;height:32px;flex-shrink:0;color:var(--blue)}
.auth-brand-caption{margin-left:auto;color:var(--muted);font-family:var(--sans-zh);font-size:12px;font-weight:400;line-height:16px}
.auth-layout{grid-template-columns:minmax(0,1fr) minmax(0,432px);align-items:center;gap:80px;padding:80px 0 32px;max-width:1120px;margin-inline:auto}
.auth-intro{min-width:0}
.auth-intro .eyebrow,.auth-form>.eyebrow{margin:0 0 16px}
.auth-intro .h-xl{max-width:680px;margin:0 0 24px;text-wrap:balance}
.auth-intro .lead{max-width:680px;margin:0;text-wrap:pretty}
.auth-benefits{display:grid;gap:16px;margin:40px 0 0}
.auth-benefits>div{display:grid;grid-template-columns:80px minmax(0,1fr);gap:16px;align-items:baseline}
.auth-benefits dt{color:var(--blue);font-size:12px;line-height:16px}
.auth-benefits dd{margin:0;color:var(--muted);font-size:14px;line-height:20px;text-wrap:pretty}
.auth-form{width:100%;min-width:0;border:1px solid var(--line);padding:32px;margin:0;background:var(--bg)}
.auth-form h2{margin:0 0 12px;font-weight:400;text-wrap:balance}
.auth-description{margin:0 0 32px;color:var(--muted);font-size:14px;line-height:20px;text-wrap:pretty}
.auth-form fieldset{border:0;padding:0;margin:0;min-width:0}
.auth-field{margin-bottom:24px}
.auth-field label{margin:0 0 8px;font-size:14px;line-height:20px}
.auth-field input{min-height:48px;padding:12px;font-size:16px;line-height:24px}
.auth-field-heading{display:flex;justify-content:space-between;align-items:baseline;gap:16px;margin-bottom:8px}
.auth-field-heading label{margin:0}
.auth-inline-link{border:0;padding:0;color:var(--blue);font-size:14px;line-height:24px;text-underline-offset:4px}
.auth-inline-link:hover:not(:disabled){text-decoration:underline}
.auth-inline-link:active:not(:disabled){transform:translateY(1px)}
.auth-password{position:relative}
.auth-password input{padding-right:64px}
.auth-password-toggle{position:absolute;inset:0 0 0 auto;border:0;min-width:64px;padding:8px 12px;color:var(--muted);font-size:12px;line-height:16px}
.auth-password-toggle:hover:not(:disabled){color:var(--blue)}
.auth-password-toggle:focus-visible{outline-offset:-4px}
.auth-form .auth-submit{width:100%;min-height:48px;margin:8px 0 0;padding:8px 12px;font-size:16px;font-weight:600;line-height:24px;transition:transform .3s cubic-bezier(.22,1,.36,1),opacity .3s cubic-bezier(.22,1,.36,1)}
.auth-submit:hover:not(:disabled){opacity:.88}
.auth-submit:active:not(:disabled){transform:scale(.98)}
.auth-links{display:flex;justify-content:center;align-items:center;gap:8px;flex-wrap:wrap;margin-top:24px;color:var(--muted);font-size:14px;line-height:24px}
.auth-footnote{margin:24px 0 0;color:var(--muted);font-size:12px;line-height:16px;text-align:center;text-wrap:pretty}
.auth-loading{width:16px;height:4px;background:currentColor;animation:auth-pulse 1s cubic-bezier(.22,1,.36,1) infinite alternate}
@keyframes auth-pulse{from{opacity:.3}to{opacity:1}}
.history-back{margin-top:0;margin-bottom:24px}
.settings-actions{display:flex;justify-content:flex-end}
.auth-switch-enter-active,.auth-switch-leave-active{transition:opacity .3s cubic-bezier(.22,1,.36,1),transform .5s cubic-bezier(.22,1,.36,1)}
.auth-switch-enter-from{opacity:0;transform:translateY(12px)}
.auth-switch-leave-to{opacity:0;transform:translateY(-8px)}
.auth-form .auth-feedback{margin:0 0 16px;border:1px solid var(--line);padding:12px 16px;font-size:14px;line-height:20px}
@media(max-width:1050px){.auth-layout{gap:48px;grid-template-columns:minmax(0,1fr) minmax(0,384px)}}
@media(max-width:760px){.auth-page{width:calc(100% - 32px);padding-top:24px;padding-bottom:32px}.auth-brand-caption{display:none}.auth-layout{display:flex;flex-direction:column;align-items:stretch;gap:32px;max-width:480px;padding:48px 0 0}.auth-intro .eyebrow{margin-bottom:12px}.auth-intro .h-xl{margin-bottom:16px}.auth-desktop-break{display:none}.auth-benefits{display:none}.auth-form{padding:24px;margin:0}.auth-description{margin-bottom:24px}}
@media(prefers-reduced-motion:reduce){.auth-switch-enter-active,.auth-switch-leave-active{transition:opacity .3s cubic-bezier(.22,1,.36,1)}.auth-switch-enter-from,.auth-switch-leave-to{transform:none}.auth-form button{transition:none}.auth-form button:active{transform:none}.auth-loading{animation:none}}
.logout-button{margin-top:20px;min-width:152px;min-height:48px}
</style>
