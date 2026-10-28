<script setup lang="ts">
import { cleanResumeText, cleanDiagnosis } from '../features/career/resumeText'
import LoadingState from '../components/LoadingState.vue'
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, Upload, Lock, Check, FileText } from 'lucide-vue-next'
import { api, post, state, download, authorizedFetch, peekHistory } from '../state'
import ContextPicker from '../components/ContextPicker.vue'
import ChatPanel from '../components/ChatPanel.vue'
import BlockRewriteDialog from '../components/BlockRewriteDialog.vue'
import Markdown from '../components/Markdown.vue'
const route = useRoute(), router = useRouter(), session = ref<any>(null), facts = ref<any[]>([]), draftFacts = ref<any[]>([]), versions = ref<any[]>([]), selectedVersion = ref<any>(null), artifacts = ref<any>(null), approved = ref<string[]>([]), busy = ref(false), error = ref(''), file = ref<File|null>(null), jd = ref(''), template = ref('gtm-original'), manual = ref(''), tab = ref('diagnosis')
const parts = computed(() => (route.params.pathMatch as string[] || []).filter(Boolean))
const blockRows = ref<any[]>([]), blocksLoading = ref(false), blocksError = ref(''), activeBlockId = ref('')
const blockChats = ref<Record<string, any>>({})
let blockRequest = 0
const versionError = ref(''), versionNotice = ref('')
const pdfUrl = ref(''), sessionLoading = ref(false)
const targetJdId=ref(''), jdFilename=ref(''), uploadingJd=ref(false)
const generating = ref(false)
const editorBusy = computed(() => busy.value || generating.value || blocksLoading.value || !!activeBlockId.value)
const activeBlock = computed(() => blockRows.value.find(b => b.id === activeBlockId.value))
const editableFacts = computed(() => draftFacts.value.filter(f => !f.locked && !blockRows.value.some(b => b.locked && b.fact_ids.includes(f.id))))
const experienceFacts = computed(() => {
  const mapping = (selectedVersion.value?.structure || session.value?.structure)?.assignments || {}
  return editableFacts.value.filter(f => ['projects','experience'].includes(f.section || mapping[f.id]))
})
const allAuthorized = computed(() => editableFacts.value.length > 0 && editableFacts.value.every(f => approved.value.includes(f.id)))
const experienceAuthorized = computed(() => experienceFacts.value.length > 0 && experienceFacts.value.every(f => approved.value.includes(f.id)))
const hasChanges = computed(() => blockRows.value.some(b => blockAuthorized(b) && b.text !== b.original))
const sectionNames:Record<string,string>={personal:'个人信息',education:'教育背景',projects:'项目经历',experience:'实习/工作经历',skills:'技能特长',summary:'自我评价',other:'其他经历'}
const diagnosisText = computed(() => cleanDiagnosis(String(session.value?.diagnosis?.analysis || '')))
function cloneFacts(value:any[]) {return value.map(f=>({...f,text:cleanResumeText(f.text)}))}
function toggleAuthorization(ids: string[]) {
  if (editorBusy.value || !ids.length) return
  const selected = new Set(approved.value), remove = ids.every(id => selected.has(id))
  for (const id of ids) { if (remove) selected.delete(id); else selected.add(id) }
  approved.value = editableFacts.value.filter(f => selected.has(f.id)).map(f => f.id)
}
function selectExperience(){toggleAuthorization(experienceFacts.value.map(f=>f.id))}
function selectAll(){toggleAuthorization(editableFacts.value.map(f=>f.id))}
function resetBlocks() {
  blockRequest++; blockRows.value=[]; blockChats.value={}; activeBlockId.value=''; blocksLoading.value=false; blocksError.value=''
}
function blockAuthorized(block:any) { return !block.locked && block.fact_ids.every((id:string) => approved.value.includes(id)) }
async function loadBlocks() {
  if (sessionLoading.value || !session.value?.confirmed || tab.value!=='editor' || blockRows.value.length || blocksLoading.value) return
  const own=++blockRequest
  const endpoint=`/career/sessions/${sessionId.value}/editing-blocks`+(selectedVersion.value ? '?base_version_id='+selectedVersion.value.id : '')
  const cached=peekHistory(endpoint)
  blocksLoading.value=!cached; blocksError.value=''
  try {
    const result=cached || await api(endpoint)
    if (own!==blockRequest) return
    blockRows.value=result.blocks.map((block:any) => {
      const text=cleanResumeText(block.fact_ids.map((id:string) => draftFacts.value.find(f=>f.id===id)?.text || '').join('\n'))
      return {...block,text,original:text}
    })
  } catch(e:any) {if (own===blockRequest) blocksError.value=e.message}
  finally {if (own===blockRequest) blocksLoading.value=false}
}
function authorizeBlock(block:any) { toggleAuthorization(block.fact_ids) }
function openBlock(block:any) {
  if (editorBusy.value || !blockAuthorized(block)) return
  if (!blockChats.value[block.id] || blockChats.value[block.id].original!==block.text) {
    blockChats.value[block.id]={turns:[],draft:'',original:block.text}
  }
  activeBlockId.value=block.id
}
function acceptBlock(text:string, original:string) {
  const block=activeBlock.value
  if (!block || !blockAuthorized(block)) return
  if (block.text!==original) {error.value='原文已修改，请重新进入改写对话。'; activeBlockId.value=''; return}
  block.text=text; activeBlockId.value=''; error.value=''
}
function resizeEditor(element: HTMLTextAreaElement) {
  element.style.height = 'auto'
  element.style.height = element.scrollHeight + 2 + 'px'
}
const vAutosize = { mounted: resizeEditor, updated: resizeEditor }
async function uploadJd(event:Event){const selected=(event.target as HTMLInputElement).files?.[0];if(!selected)return;uploadingJd.value=true;error.value='';try{const form=new FormData();form.append('file',selected);const result=await api('/career/job-descriptions',{method:'POST',body:form});targetJdId.value=result.id;jd.value=result.body;jdFilename.value=result.filename}catch(e:any){error.value=e.message}finally{uploadingJd.value=false}}
onBeforeUnmount(() => { if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value) })
const sessionId = computed(() => ['review','editor'].includes(parts.value[0]) ? parts.value[1] : '')
async function load() {
  sessionLoading.value=false
  versionError.value=''; versionNotice.value=''
  resetBlocks()
  error.value = ''; session.value = null; selectedVersion.value=null; artifacts.value=null; versions.value=[]; approved.value=[]
  if (!sessionId.value) {if(route.query.jd_id && state.user){try{const r=await api('/knowledge/documents/'+route.query.jd_id);jd.value=r.body;targetJdId.value=r.id;jdFilename.value=r.title}catch(e:any){error.value=e.message}}return}
  const endpoint='/career/sessions/' + sessionId.value
  const cached=peekHistory(endpoint), cachedVersions=peekHistory(endpoint+'/versions')
  sessionLoading.value=!(cached && cachedVersions)
  try {
    session.value = cached || await api(endpoint)
    state.careerId = sessionId.value; state.scope = 'career'
    facts.value = cloneFacts(session.value.facts).map(f=>({...f,section:f.section||session.value.structure?.assignments[f.id]||'other'})); draftFacts.value = cloneFacts(facts.value)
    versions.value = cachedVersions || await api(endpoint+'/versions')
    const active = versions.value.find(v => v.id === session.value.active_version_id)
    tab.value = parts.value[0] === 'editor' ? 'editor' : 'diagnosis'
    sessionLoading.value=false
    if (active) await selectVersion(active)
  } catch(e: any) { error.value = e.message } finally {sessionLoading.value=false}
}
async function upload() {
  if (!file.value) return
  busy.value = true; error.value = ''
  try { const form = new FormData(); form.append('file',file.value); const resume = await api('/career/resumes', {method:'POST',body:form}); const result = await post('/career/sessions', {...state.context,resume_id:resume.id,jd:jd.value,jd_id:targetJdId.value||null}); await router.push('/career/review/' + result.id) } catch(e: any) { error.value = e.message } finally {busy.value = false}
}
async function confirm() {
  busy.value = true; error.value = ''
  try {
    if (!facts.value.length && manual.value.trim()) facts.value = manual.value.trim().split('\n').filter(Boolean).map((text,i) => ({id:'f'+i,text,locked:/教育|大学|本科/.test(text),confidence:1,page:1}))
    session.value = await post(`/career/sessions/${sessionId.value}/confirm-facts`, {facts:facts.value})
    draftFacts.value = cloneFacts(facts.value); selectedVersion.value=null; approved.value=[]
    resetBlocks()
  } catch(e:any) {error.value=e.message} finally {busy.value=false}
}
async function rewrite() {
  if (editorBusy.value) return
  generating.value = true; error.value = ''; versionError.value=''; versionNotice.value=''
  try {
    const blocks = blockRows.value.filter(b => blockAuthorized(b) && b.text !== b.original).map(b=>({fact_ids:b.fact_ids,text:b.text}))
    if (!blocks.length) throw new Error('请修改已勾选授权的段落，随后再生成版本。')
    const result = await post(`/career/sessions/${sessionId.value}/approve-rewrite`, {blocks,approved_fact_ids:approved.value,template:template.value,base_version_id:selectedVersion.value?.id || null})
    versions.value.unshift(result); approved.value=[]; versionNotice.value='已保存为新版本。可下载 TeX；PDF 编译状态见右侧。'
    try { await selectVersion(result) }
    catch(e:any) { versionError.value='新版已保存，但下载信息暂时无法加载：'+e.message+'。可在右侧刷新编译状态，无需重复生成。' }
  } catch(e:any) {versionError.value=e.message} finally {generating.value=false}
}
async function selectVersion(version:any) {
  resetBlocks()
  facts.value=cloneFacts(version.facts); draftFacts.value=cloneFacts(version.facts); selectedVersion.value=version
  void loadBlocks()
  artifacts.value=await api(`/career/versions/${version.id}/artifacts`)
  if (pdfUrl.value) { URL.revokeObjectURL(pdfUrl.value); pdfUrl.value='' }
  if (artifacts.value.pdf) { const r = await authorizedFetch(artifacts.value.pdf); if(r.ok) pdfUrl.value=URL.createObjectURL(await r.blob()) }
}
async function exportFile(kind:string) {try {await download(`/api/v1/career/versions/${selectedVersion.value.id}/download/${kind}`, 'resume.'+kind)} catch(e:any) {error.value=e.message} }
watch(() => [tab.value, session.value?.confirmed, selectedVersion.value?.id, sessionLoading.value], loadBlocks)
onBeforeUnmount(resetBlocks)
watch(() => route.fullPath,load); onMounted(load)
</script>
<template>
  <div class="container">
    <section v-if="!sessionId" class="page-hero"><div><p class="eyebrow">03 / TELL YOUR REAL STORY</p><h1 class="h-xl">让真实经历，<br>表达<span class="blue">你的价值。</span></h1><p class="lead">结合目标岗位与 JD，诊断表达、补充内容、打磨简历。<br>按你的反馈逐轮修改，每一处取舍都由你决定。</p></div><div class="hero-aside"><span class="large-number">03</span><p>从你的经历与需求出发。<br>让表达更贴近目标岗位。</p><RouterLink to="/history?kind=career" class="text-link">历史简历修改 <ArrowUpRight :size="17" /></RouterLink></div></section>
    <template v-if="!sessionId"><div v-if="!state.user" class="empty-state"><Lock :size="25" /><h2>为你的经历，留一个私有空间。</h2><p>登录后上传简历，原文件与修改版本仅对你可见。</p><RouterLink to="/login?next=/career" class="primary">登录 / 注册 <ArrowUpRight :size="16" /></RouterLink></div><form v-else class="setup-layout" @submit.prevent="upload"><div><p class="eyebrow">STEP 01 / YOUR TARGET</p><h2>先确定，想走向哪里。</h2><ContextPicker /><label>上传目标岗位 JD（选填）<input type="file" accept=".txt,.md,.pdf" :disabled="uploadingJd" @change="uploadJd"><span class="meta">{{ uploadingJd ? "正在读取 JD…" : jdFilename ? "已保存私有 JD："+jdFilename : "TXT / Markdown / 可读 PDF · 最大 2MB；也可直接粘贴" }}</span></label><label>目标岗位 JD（可校对）<textarea v-model="jd" rows="4" placeholder="粘贴真实岗位描述，明确要求优先于通用画像。"></textarea></label><p class="eyebrow space-top">STEP 02 / YOUR EXPERIENCE</p><label class="upload-area"><Upload :size="26" /><strong>{{ file?.name || '选择你的简历文件' }}</strong><span>PDF、PNG、JPG 或 TXT · 最大 10 MB / 10 页</span><input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" @change="file=($event.target as HTMLInputElement).files?.[0] || null"></label><p class="meta">可读 PDF/TXT 直接提取文字；扫描件和图片由支持图像输入的大模型识别。识别后请核对并确认事实。</p><p class="meta">上传后，简历文本将发送至配置的模型服务进行提取与诊断；图片或扫描页会发送至图像识别模型。</p><div class="career-submit"><button class="primary" :disabled="!file || busy || uploadingJd">{{ busy ? '解析与诊断中…' : '上传并开始诊断' }}<ArrowUpRight :size="16" /></button></div></div><aside class="info-aside"><p class="eyebrow">YOU STAY IN CONTROL</p><h3>从诊断开始。<br>是否改写，由你选择。</h3><ol><li>上传与识别</li><li>确认真实经历</li><li>查看诊断建议</li><li>授权段落并生成版本</li></ol><p class="meta">教育背景默认锁定。未经确认与授权，不会生成新版简历。</p></aside></form></template>
    <LoadingState v-else-if="sessionLoading" label="正在加载简历与修改记录…"/><template v-else-if="session"><RouterLink to="/career" class="back-link"><ArrowLeft :size="15" /> 简历工作台</RouterLink><div class="workspace-heading"><div><p class="eyebrow">YOUR CAREER WORKSPACE / PRIVATE</p><h1 class="h-xl">把经历，说清楚。</h1></div><span class="status-label">{{ session.confirmed ? '事实已确认' : '等待事实确认' }} · 私有</span></div><div class="tabs"><button :class="{active:tab==='facts'}" @click="tab='facts'">识别与事实</button><button :class="{active:tab==='diagnosis'}" @click="tab='diagnosis'">诊断建议</button><button :class="{active:tab==='editor'}" @click="tab='editor'">修改与版本</button></div>
      <section v-if="tab==='facts'" class="facts-section"><div v-if="session.structure" class="extracted-profile"><span v-for="(field,key) in session.structure.profile" :key="key" v-show="field.value"><small>{{ ({name:"姓名",email:"邮箱",phone:"电话",target_role:"求职意向"} as Record<string,string>)[key] }}</small>{{ field.value }}</span></div><p class="meta">核对关键字段与段落归属。确认后，后台按这些映射填入你的 TeX 模板。</p><p class="notice">{{ session.parse_warning }} 勾选锁定可保护段落；后续补充也可直接在改写对话中提出。</p><div v-for="f in facts" :key="f.id" class="fact-row"><div><span v-if="f.confidence<0.9" class="meta">需核对</span><textarea v-autosize v-model="f.text" rows="1" :disabled="busy" :aria-label="'核对段落 '+f.id"></textarea><select v-model="f.section" :aria-label="'段落归属 '+f.id" class="section-select"><option v-for="(name,key) in sectionNames" :key="key" :value="key">{{ name }}</option></select></div><label class="checkbox-label"><input v-model="f.locked" type="checkbox">锁定</label></div><textarea v-if="!facts.length" v-autosize v-model="manual" rows="1" class="manual-facts" placeholder="逐行录入姓名、教育、经历与技能；不清楚的字段请核对原件。"></textarea><div class="career-submit"><button class="primary" :disabled="busy" @click="confirm"><Check :size="16" />{{ busy ? '确认中…' : '我已核对，确认这些事实' }}</button></div></section>
      <section v-if="tab==='diagnosis'"><div v-if="session.diagnosis" class="diagnosis-layout"><div><p class="eyebrow">DIAGNOSIS / {{ session.diagnosis.provider === 'mock' ? '旧版诊断' : session.diagnosis.model }}</p><h2>先看见可以改进的地方。</h2><p class="notice">{{ session.diagnosis.notice }}</p><div v-for="d in session.diagnosis.dimensions" :key="d.name" class="dimension-row"><h3>{{ d.name }}<span>{{ d.score }} / {{ d.max }}</span></h3><p>{{ d.advice }}</p></div><Markdown ai class="diagnosis-analysis" :source="diagnosisText" /><div class="citations"><RouterLink v-for="c in session.diagnosis.citations" :key="c.chunk_id" :to="c.url+'?heading='+encodeURIComponent(c.heading_path)">{{ c.title }} · {{ c.kind==='interview'?'个人面经参考':'岗位/学习依据' }} ↗</RouterLink></div></div><aside class="score-block"><strong>{{ session.diagnosis.score }}</strong><span>内部完整性参考 / 100</span><button class="secondary" @click="tab='facts'">补充 / 纠正信息</button><button class="primary" @click="tab=session.confirmed?'editor':'facts'">{{ session.confirmed ? '选择需要修改的段落' : '先确认识别事实' }}</button><p class="meta">只查看建议即可结束，系统不会自动改写。</p></aside></div><div v-else class="empty-state">识别文本不足。请先进入「识别与事实」录入并确认简历内容。<button @click="tab='facts'">去确认事实</button></div><div class="article-qa"><h2>围绕当前简历，继续讨论。</h2><ChatPanel scope="career" :session-id="sessionId" /></div></section>
      <section v-if="tab==='editor'"><p v-if="!session.confirmed" class="notice">请先在「识别与事实」确认内容，再授权改写。</p><div v-else class="editor-layout"><div><p class="eyebrow">EDIT WITH EVIDENCE</p><p>按完整经历编辑，进入每块的 AI 对话逐轮修改；确认回填后选择模板生成新版。</p><div class="editor-bulk-actions"><button type="button" class="secondary" :disabled="editorBusy || !editableFacts.length" @click="selectAll">{{ allAuthorized ? '全部取消授权' : '全部授权' }}</button><button type="button" class="secondary" :disabled="editorBusy || !experienceFacts.length" @click="selectExperience">{{ experienceAuthorized ? '取消项目与经历授权' : '选择项目与经历段落' }}</button></div><LoadingState v-if="blocksLoading" label="正在整理完整经历…" compact/><div v-else-if="blocksError"><p class="error" role="alert">{{ blocksError }}</p><button class="secondary" @click="loadBlocks">重新加载分块</button></div><section v-for="block in blockRows" :key="block.id" class="edit-block"><div class="block-heading"><h3>{{ block.title }}</h3><label class="checkbox-label"><input type="checkbox" :checked="blockAuthorized(block)" :disabled="block.locked || editorBusy" @change="authorizeBlock(block)">{{ block.locked ? '已锁定' : '授权修改此块' }}</label></div><textarea v-autosize v-model="block.text" rows="4" maxlength="16000" :aria-label="'修改 '+block.title" :disabled="block.locked || !blockAuthorized(block) || editorBusy"></textarea><p v-if="blockAuthorized(block) && !block.text.trim()" class="meta">此块为空，可让 AI 结合目标岗位起草；保持空白时不出现在导出简历中。</p><div v-if="!block.locked" class="block-actions"><button class="text-link" :disabled="!blockAuthorized(block) || editorBusy" @click="openBlock(block)">{{ block.text.trim() ? '生成改写建议' : '和 AI 聊聊' }}<ArrowUpRight :size="16"/></button></div></section><p v-if="error" class="error" role="alert">{{ error }}</p><label>排版模板<select v-model="template" :disabled="editorBusy"><option value="gtm-original">你的 GTM 中文简历模板</option><option value="classic-cn">经典中文</option><option value="classic-en">经典英文（保留原文，不自动翻译）</option><option value="modern-onepage">现代单页</option></select></label><div class="career-submit"><button type="button" class="primary" @click="rewrite" :disabled="editorBusy || !hasChanges">{{ generating ? '生成新版中…' : '确认并生成新版' }}<ArrowUpRight :size="16" /></button></div><p v-if="versionNotice" class="notice version-feedback" role="status">{{ versionNotice }}</p><p v-if="versionError" class="error version-feedback" role="alert">{{ versionError }}</p></div><aside class="versions-panel"><p class="eyebrow">VERSION HISTORY</p><p v-if="!versions.length" class="meta">还没有生成版本，原始文件保持不变。</p><button v-for="(v,i) in versions" :key="v.id" :class="{selected:selectedVersion?.id===v.id}" class="version-row" :disabled="editorBusy" @click="selectVersion(v)"><FileText :size="17" /><span>版本 {{ versions.length-i }}<small>{{ new Date(v.created_at).toLocaleString() }}</small></span></button><template v-if="selectedVersion"><p class="notice">{{ artifacts?.job?.message || '编译任务：' + artifacts?.job?.status }}</p><button class="secondary" :disabled="editorBusy" @click="selectVersion(selectedVersion)">刷新编译状态</button><button class="secondary" @click="exportFile('tex')">下载 .tex</button><button class="primary" :disabled="!artifacts?.pdf" @click="exportFile('pdf')">下载 PDF</button></template></aside></div><section v-if="pdfUrl" class="pdf-preview"><h2>简历 PDF 预览</h2><iframe :src="pdfUrl" title="简历 PDF 预览"></iframe></section><div class="article-qa"><h2>先讨论，再决定如何修改。</h2><ChatPanel scope="career" :session-id="sessionId" /></div></section>
    </template><BlockRewriteDialog v-if="activeBlock" :key="activeBlock.id" :block="activeBlock" :session-id="sessionId" :base-version-id="selectedVersion?.id" :dialogue="blockChats[activeBlock.id]" @close="activeBlockId=''" @accept="acceptBlock"/><p v-if="error && (!session || tab!=='editor')" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.career-submit{display:flex;justify-content:flex-end;margin-top:24px}
.version-feedback{margin-top:14px}
.editor-bulk-actions{display:flex;gap:10px;flex-wrap:wrap}
.fact-row{grid-template-columns:minmax(0,1fr) 70px}
.fact-row textarea,.manual-facts{min-height:0;padding:6px 10px;font-size:14px;line-height:1.75;resize:none;overflow:hidden}
.edit-block{padding:24px 0;border-bottom:1px solid var(--line)}
.block-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.block-heading h3{font-size:18px;margin:0}
.block-heading label{margin:0}
.edit-block textarea{min-height:130px;padding:12px;font-size:14px;line-height:1.9;resize:vertical;overflow:hidden}
.block-actions{display:flex;justify-content:flex-end;margin-top:16px}
.block-actions button{white-space:nowrap}
.diagnosis-analysis{margin-top:24px;font-size:15px;line-height:1.95;white-space:normal}
.diagnosis-analysis :deep(h1),.diagnosis-analysis :deep(h2){font-size:22px}
</style>
