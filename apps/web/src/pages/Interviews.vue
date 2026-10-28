<script setup lang="ts">
import { cleanAIText } from "../features/ai/aiText"
import LoadingState from '../components/LoadingState.vue'
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, Sparkles, LogOut } from 'lucide-vue-next'
import { api, post, state, historyRecords, knowledgeDocument, peekKnowledge, peekHistory } from '../state'
import ContextPicker from '../components/ContextPicker.vue'
import ChatPanel from '../components/ChatPanel.vue'
import Composer from '../components/Composer.vue'
import ArticleBody from '../components/ArticleBody.vue'
import ResourceGallery from '../components/ResourceGallery.vue'
const route = useRoute(), router = useRouter(), doc = ref<any>(null), session = ref<any>(null), report = ref<any>(null), error = ref(''), busy = ref(false), draft = ref(''), count = ref<number | 'custom'>(5), customCount = ref(7), difficulty = ref('基础'), jd = ref(''), company = ref(''), language = ref('zh-CN'), resumeId = ref(''), consent = ref(false), resumes = ref<any[]>([])
const path = computed(() => String(route.params.pathMatch ? (route.params.pathMatch as string[]).join('/') : ''))
const isSetup = computed(() => path.value === 'mock/setup')
const isMock = computed(() => path.value.startsWith('mock/') && !isSetup.value)
const loading = ref(false)
let answerKey = crypto.randomUUID()
let loadGeneration=0
async function load() {
  const current=++loadGeneration
  error.value = ''; doc.value = null; session.value = null; report.value = null
  loading.value = true
  try {
    if (isMock.value) {
      const id = path.value.split('/')[1]
      const review=path.value.endsWith('/report')
      const endpoint='/mock/sessions/'+id+(review?'/report':'')
      const cached=peekHistory(endpoint)
      if(cached)loading.value=false
      const row=cached || await api(endpoint)
      if(current!==loadGeneration)return
      session.value=row;if(review)report.value=row
    }
    else if (isSetup.value) { if (state.user) resumes.value = (await historyRecords()).filter((r: any) => r.kind === 'career' && ['diagnosed','editing','confirmed'].includes(r.status)) }
    else if (path.value) {
      const id=path.value, cached=peekKnowledge('/knowledge/documents/'+encodeURIComponent(id))
      const row=cached || await knowledgeDocument(id)
      if(current!==loadGeneration)return
      doc.value=row;state.documentId=row.id;state.scope='article'
    }
  } catch (e: any) { if(current===loadGeneration)error.value = e.message } finally { if(current===loadGeneration)loading.value = false }
}
async function begin() {
  if (busy.value) return
  const requestedCount = count.value === 'custom' ? customCount.value : count.value
  if (!Number.isInteger(requestedCount) || requestedCount < 1 || requestedCount > 20) { error.value = '请输入 1–20 之间的整数题数'; return }
  busy.value = true; error.value = ''
  try { const r = await post('/mock/sessions', { ...state.context, count: requestedCount, difficulty: difficulty.value, jd: jd.value, company: company.value, language: language.value, resume_session_id: resumeId.value || null, resume_consent: consent.value }); await router.push('/interviews/mock/' + r.id) } catch(e: any) { error.value = e.message } finally { busy.value = false }
}
async function answer(mode: string) {
  busy.value = true; error.value = ''
  try {
    session.value = await post(`/mock/sessions/${session.value.id}/answers`, { answer: draft.value, question_index: session.value.current_question_index, idempotency_key: answerKey, input_mode: mode })
    draft.value = ''; answerKey = crypto.randomUUID()
    if (session.value.status === 'completed') await router.push(`/interviews/mock/${session.value.id}/report`)
  } catch(e: any) { error.value = e.message } finally { busy.value = false }
}
async function exitMock() {
  if (busy.value) return
  const unanswered = session.value?.id && !session.value.answers?.length
  if (!unanswered && draft.value.trim() && !window.confirm('当前回答尚未提交，退出后将丢失这段草稿。已提交的记录会保留，之后可从「我的空间」回看。确定退出？')) return
  if (unanswered) {
    busy.value = true; error.value = ''
    try { await api(`/mock/sessions/${session.value.id}?only_if_unanswered=true`, {method:'DELETE'}) }
    catch(e:any) { error.value = '丢弃空练习失败，请重试：'+e.message; return }
    finally { busy.value = false }
  }
  draft.value = ''
  await router.push('/interviews')
}
function askAI(answer: { question: string; answer: string }) {
  if (state.assistantBusy || state.assistantRequest) return
  state.assistantRequest = { question: `题目：${answer.question}\n\n用户回答：${answer.answer}\n\n请结合资料给出更标准的回答：` }
}
watch(() => [route.path, state.context.role, state.context.industry], load); onMounted(load)
</script>
<template>
  <div class="container">
    <section v-if="!isMock && !doc" class="page-hero"><div><p class="eyebrow">02 / PRACTICE YOUR PERSPECTIVE</p><h1 class="h-xl">把理解，变成<br><span class="blue">说得清的判断。</span></h1><p class="lead">从业务问题出发，在练习、追问与复盘中，<br>形成属于你的回答。</p></div><div class="hero-aside"><span class="large-number">02</span><p>问题是入口。<br>思考过程比标准答案更重要。</p><div class="mock-entry-links"><RouterLink to="/interviews/mock/setup" class="text-link">开始 Mock 面试 <ArrowUpRight :size="17" /></RouterLink><RouterLink to="/history?kind=mock" class="text-link">Mock 历史 <ArrowUpRight :size="17" /></RouterLink></div></div></section>
    <template v-if="isSetup"><RouterLink to="/interviews" class="back-link"><ArrowLeft :size="15"/>返回面经与 Mock</RouterLink><div class="section-heading"><h2>设置一次有目标的练习</h2><span class="eyebrow">MOCK INTERVIEW / SETUP</span></div><div v-if="!state.user" class="empty-state">登录后即可保存练习与复盘。<RouterLink to="/login?next=/interviews/mock/setup" class="text-link">登录 / 注册 ↗</RouterLink></div><form v-else class="setup-layout" @submit.prevent="begin"><div><ContextPicker /><div class="form-grid"><label>题目数量<select v-model="count"><option :value="3">3 题 · 快速练习</option><option :value="5">5 题 · 标准练习</option><option :value="10">10 题 · 完整练习</option><option value="custom">自定义数量</option></select></label><label v-if="count==='custom'">自定义题数<input v-model.number="customCount" type="number" min="1" max="20" step="1" required placeholder="1–20 题"></label><label>难度<select v-model="difficulty"><option>基础</option><option>进阶</option><option>挑战</option></select></label><label>语言<select v-model="language"><option value="zh-CN">中文</option><option value="en">English</option></select></label></div><label>目标企业（选填）<input v-model="company" placeholder="例如：目标品牌 / 企业"></label><label>目标岗位 JD（选填）<textarea v-model="jd" rows="5" placeholder="粘贴岗位职责与要求，优先用于练习背景"></textarea></label><label>引用我的已确认简历（选填）<select v-model="resumeId"><option value="">不引用简历</option><option v-for="r in resumes" :key="r.id" :value="r.id">{{ r.display_name }}</option></select></label><label v-if="resumeId" class="checkbox-label"><input v-model="consent" type="checkbox">我授权本次面试使用这份简历的已确认事实。</label><div class="mock-start-actions"><button class="primary" :disabled="busy || (!!resumeId && !consent)">{{ busy ? '准备题目中…' : '开始练习' }}<ArrowUpRight :size="16" /></button></div></div><aside class="info-aside"><p class="eyebrow">WHAT TO EXPECT</p><h3>一次练习，<br>一份可回看的进步。</h3><p>题目覆盖岗位认知、业务场景与行为经历等能力。每题支持文字或语音转写，AI 会根据回答继续追问，或进入下一题。</p><p>已提交的回答与反馈会自动保存，你可以随时从「我的空间」回看。</p></aside></form></template>
    <template v-else-if="isMock && session"><div class="mock-record-navigation"><RouterLink :to="path.endsWith('/report') ? '/history?kind=mock' : '/interviews'" class="back-link"><ArrowLeft :size="15" />{{ path.endsWith('/report') ? 'Mock 历史' : '面试练习' }}</RouterLink><RouterLink v-if="path.endsWith('/report')" to="/interviews" class="back-link">返回面经与 Mock<ArrowUpRight :size="15"/></RouterLink></div><template v-if="path.endsWith('/report')"><section class="report-heading"><div><p class="eyebrow">MOCK / ANSWER REVIEW</p><h1 class="h-xl">Mock 作答记录</h1><p class="meta">回看已作答的题目、你的回答与 AI 改进建议。</p></div></section><p v-if="!report.answers.length" class="empty-state">这轮练习还没有已提交的回答。</p><div v-for="(a,i) in report.answers" :key="i" class="review-row"><p class="eyebrow">题目 {{ Number(i)+1 }}</p><h3>{{ cleanAIText(a.question) }}</h3><p class="eyebrow review-label">我的回答</p><blockquote class="mock-review-answer">{{ a.answer }}</blockquote><p class="eyebrow review-label">AI 改进建议</p><p class="mock-review-feedback">{{ cleanAIText(a.evaluation.feedback) }}</p><div class="review-answer-actions"><button type="button" class="text-link" :disabled="state.assistantBusy || !!state.assistantRequest" @click="askAI(a)"><Sparkles :size="16" />问问 AI<ArrowUpRight :size="16" /></button></div></div><div class="mock-start-actions"><RouterLink to="/interviews/mock/setup" class="primary">开始新一轮练习 ↗</RouterLink></div></template><template v-else><div class="mock-top"><p class="eyebrow">MOCK INTERVIEW / {{ session.context.language === 'en' ? 'ENGLISH' : '中文' }}</p><span class="meta">{{ session.current_question_index+1 }} / {{ session.questions.length }} · 已自动保存</span></div><div class="progress-track"><div :style="{width: session.current_question_index / session.questions.length * 100 + '%'}"></div></div><div class="mock-layout"><section><p class="eyebrow">{{ session.questions[session.current_question_index]?.dimension }} {{ session.pending_followup ? ' / 深入追问' : '' }}</p><h1 class="mock-question"><span class="mock-question-number">{{ String(session.current_question_index + 1).padStart(2, '0') }}</span><span>{{ cleanAIText(session.pending_followup || session.questions[session.current_question_index]?.text) }}</span></h1><Composer v-model="draft" :busy="busy" label="确认并提交回答" placeholder="组织你的回答。语音转写后，请校对再提交。" @submit="answer" /><p class="meta">回答以确认后的文字为准。按 Ctrl + Enter 提交。</p><div v-if="session.answers.length" class="last-feedback"><p class="eyebrow">PREVIOUS FEEDBACK</p><p>{{ cleanAIText(session.answers.at(-1).evaluation.feedback) }}</p><button class="text-link" :disabled="state.assistantBusy || !!state.assistantRequest" @click="askAI(session.answers.at(-1))"><Sparkles :size="16" />问问 AI<ArrowUpRight :size="16" /></button></div></section><aside class="info-aside"><p class="eyebrow">INTERVIEW NOTES</p><p>先给出判断，再解释依据。<br>用真实经历，说明你的行动。<br>不确定的部分，可以明确说明。</p><p class="meta">{{ session.provider === 'mock' ? '旧版记录：固定题池 + 启发式评价，不能替代人工反馈。' : '模型评分仅供学习参考。' }}</p></aside></div><div class="mock-exit"><button type="button" class="secondary" :disabled="busy" @click="exitMock"><LogOut :size="16" />退出 Mock</button></div></template></template>
    <template v-else-if="doc"><RouterLink :to="{path:'/interviews',query:{page:route.query.page}}" class="back-link"><ArrowLeft :size="15" /> 返回题目库</RouterLink><section class="article-header"><p class="eyebrow">INTERVIEW NOTES / READING</p><h1 class="h-xl">{{ doc.title }}</h1><p class="meta">{{ doc.meta.source_type === "original_research_note" ? "原创研究笔记 · 个人面试自述" : "合成练习示例" }} · {{ doc.meta.source_author }}</p></section><a v-if="doc.meta.source_url" :href="doc.meta.source_url" target="_blank" rel="noopener noreferrer" class="text-link source-link">查看原帖出处 ↗</a><ArticleBody :source="doc.body" :heading="String(route.query.heading || '')" @ask="state.assistant=true"/><div class="article-qa"><h2>围绕这个案例，继续思考。</h2><ChatPanel scope="article" :document-id="doc.id" /></div></template>
    <ResourceGallery v-else-if="!path" fixed-kind="interview" />
    <LoadingState v-if="loading && path && !isSetup" :label="isMock ? (path.endsWith('/report') ? '正在加载 Mock 记录…' : '正在加载 Mock 练习…') : '正在加载资料…'"/>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.mock-question{display:flex;align-items:baseline;gap:16px;padding:22px 24px;background:rgba(0,47,167,.045);font-size:22px;font-weight:400;line-height:1.8;overflow-wrap:anywhere}
.mock-question-number{flex-shrink:0;font-family:var(--mono);font-size:18px;font-weight:500;line-height:1.8;color:var(--blue);font-variant-numeric:tabular-nums}
@media(max-width:700px){.mock-question{gap:12px;padding:18px 16px;font-size:18px}.mock-question-number{font-size:16px}}

.mock-record-navigation{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.review-answer-actions{display:flex;justify-content:flex-end;margin-top:16px}
.review-answer-actions .text-link{white-space:nowrap}
.mock-start-actions{display:flex;justify-content:flex-end}
.mock-entry-links{display:flex;flex-direction:column;align-items:flex-start;gap:14px}
.review-label{margin:24px 0 12px}
.mock-review-answer,.mock-review-feedback{white-space:pre-wrap;overflow-wrap:anywhere}
.mock-exit{display:flex;justify-content:flex-end;border-top:1px solid var(--line);padding:24px 0 40px}
</style>
