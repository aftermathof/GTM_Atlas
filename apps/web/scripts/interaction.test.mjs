import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import { webcrypto } from 'node:crypto'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

function compile(source) {
  return ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
}

function scrolling() {
  let config
  const context = vm.createContext({ exports: {}, require: name => {
    if (name === 'vue') return { createApp: () => ({ use() { return this }, mount() {} }) }
    if (name === 'vue-router') return { createWebHistory() {}, createRouter: value => { config = value; return {} } }
    return {}
  } })
  vm.runInContext(compile(readFileSync(new URL('../src/main.ts', import.meta.url), 'utf8')), context)
  return config.scrollBehavior
}

test('switching gallery tabs preserves page position', () => {
  const result = scrolling()({ path: '/learn', query: { kind: 'jd' } }, { path: '/learn', query: { kind: 'overview' } }, null)
  assert.equal(result, false)
})

test('browser back restores its saved scroll position', () => {
  const position = { left: 0, top: 850 }
  assert.equal(scrolling()({ path: '/learn' }, { path: '/career' }, position), position)
})

test('navigation to a different page still starts at the top', () => {
  assert.equal(scrolling()({ path: '/career' }, { path: '/learn' }, null).top, 0)
})

function composer(user = { id: 'test-user' }, configured = true) {
  let microphoneRequests = 0, recordingStarts = 0
  class Recorder {
    static isTypeSupported() { return true }
    start() { this.state = 'recording'; recordingStarts++ }
    stop() { this.state = 'inactive'; this.onstop?.() }
  }
  const { descriptor } = parse(readFileSync(new URL('../src/components/Composer.vue', import.meta.url), 'utf8'))
  const source = compileScript(descriptor, { id: 'composer-test' }).content
  const context = vm.createContext({
    exports: {}, MediaRecorder: Recorder, window: { MediaRecorder: Recorder },
    navigator: { mediaDevices: { async getUserMedia() {
      microphoneRequests++
      return { getTracks: () => [{ stop() {} }] }
    } } },
    setInterval: () => 1, clearInterval() {}, FormData, Blob, AbortController,
    require: name => {
      if (name === 'vue') return { ...vue, onBeforeUnmount() {} }
      if (name === '../state') return { state: { user, health: { stt_configured: configured } }, api() { throw new Error('Unexpected STT request') } }
      return {}
    }
  })
  vm.runInContext(compile(source), context)
  const component = context.exports.default.setup({ modelValue: '', busy: false }, { expose() {}, emit() {} })
  return { component, requests: () => microphoneRequests, starts: () => recordingStarts }
}

test('one click starts recording without a separate consent step', async () => {
  const app = composer()
  await app.component.start()
  assert.equal(app.requests(), 1)
  assert.equal(app.starts(), 1)
  assert.equal(app.component.mode.value, 'recording')
  app.component.cancel()
})

test('voice input still requires login and configured transcription service', async () => {
  for (const app of [composer(null), composer({ id: 'test-user' }, false)]) {
    await app.component.start()
    assert.equal(app.requests(), 0)
    assert.ok(app.component.error.value)
  }
})

function mockInterview(confirmExit = true, options = {}) {
  const navigations = [], confirmations = []
  const state = { user: { id: 'user' }, context: {}, assistantRequest: null, assistantBusy: false }
  const { descriptor } = parse(readFileSync(new URL('../src/pages/Interviews.vue', import.meta.url), 'utf8'))
  const context = vm.createContext({ exports: {}, crypto: webcrypto, window: { confirm: message => { confirmations.push(message); return confirmExit } }, require: name => {
    if (name === 'vue') return { ...vue, onMounted() {}, watch() {} }
    if (name === 'vue-router') return { useRoute: () => ({ path: '/interviews/mock/test', params: { pathMatch: options.pathMatch || ['mock', 'test'] } }), useRouter: () => ({ push: path => navigations.push(path) }) }
    if (name === '../state') return { state, api: options.api, post: options.post, historyRecords: options.historyRecords || (() => options.api('/history')) }
    return {}
  } })
  vm.runInContext(compile(compileScript(descriptor, { id: 'interview-test' }).content), context)
  return { state, navigations, confirmations, component: context.exports.default.setup({}, { expose() {} }) }
}

test('ask AI uses the saved answer and its original question, including followups', () => {
  const app = mockInterview()
  app.component.askAI({ question: '追问：你会如何验证？', answer: '我会先做小规模实验。' })
  assert.equal(app.state.assistantRequest.question, '题目：追问：你会如何验证？\n\n用户回答：我会先做小规模实验。\n\n请结合资料给出更标准的回答：')
})

test('custom Mock counts are submitted without a fixed random seed', async () => {
  let body
  const app = mockInterview(true, { post: async (path, value) => { body = value; return { id: 'custom-mock' } } })
  app.component.count.value = 'custom'
  app.component.customCount.value = 7
  await app.component.begin()
  assert.equal(body.count, 7)
  assert.equal(Object.hasOwn(body, 'seed'), false)
  assert.deepEqual(app.navigations, ['/interviews/mock/custom-mock'])
})

test('invalid custom Mock counts do not start a session', async () => {
  for (const count of [0, 21, 1.5]) {
    const app = mockInterview(true, { post: () => { throw new Error('must not submit') } })
    app.component.count.value = 'custom'
    app.component.customCount.value = count
    await app.component.begin()
    assert.match(app.component.error.value, /1–20/)
    assert.equal(app.navigations.length, 0)
  }
})

test('ask AI does not submit another request while the assistant is replying', () => {
  const app = mockInterview()
  app.state.assistantBusy = true
  app.component.askAI({ question: '题目', answer: '回答' })
  assert.equal(app.state.assistantRequest, null)
})

test('exit Mock returns to interviews and preserves submitted progress', async () => {
  const app = mockInterview()
  const progress = { id: 'session', current_question_index: 1, answers: [{ answer: '已提交' }] }
  app.component.session.value = progress
  await app.component.exitMock()
  assert.deepEqual(app.navigations, ['/interviews'])
  assert.equal(app.confirmations.length, 0)
  assert.equal(app.component.session.value.current_question_index, 1)
  assert.equal(app.component.session.value.answers.length, 1)
})

test('cancel exit keeps an unsubmitted draft on the Mock page', async () => {
  const app = mockInterview(false)
  app.component.draft.value = '尚未提交的回答'
  await app.component.exitMock()
  assert.equal(app.confirmations.length, 1)
  assert.deepEqual(app.navigations, [])
  assert.equal(app.component.draft.value, '尚未提交的回答')
})

test('confirmed exit leaves the page but cannot interrupt a pending answer submission', async () => {
  const app = mockInterview()
  app.component.draft.value = '未提交回答'
  app.component.busy.value = true
  await app.component.exitMock()
  assert.deepEqual(app.navigations, [])
  app.component.busy.value = false
  await app.component.exitMock()
  assert.deepEqual(app.navigations, ['/interviews'])
  assert.equal(app.component.draft.value, '')
})

test('an unfinished Mock review loads saved answers without opening the live question', async () => {
  const calls = []
  const saved = { id: 'test', status: 'active', answers: [{ question: '已答题', answer: '已提交回答', evaluation: { feedback: '改进建议' } }] }
  const app = mockInterview(true, { pathMatch: ['mock', 'test', 'report'], api: async path => { calls.push(path); return saved } })
  await app.component.load()
  assert.deepEqual(calls, ['/mock/sessions/test/report'])
  assert.equal(app.component.report.value.answers[0].question, '已答题')
  assert.equal(app.component.report.value.status, 'active')
})

function careerEditor(options = {}) {
  const { descriptor } = parse(readFileSync(new URL('../src/pages/Career.vue', import.meta.url), 'utf8'))
  const context = vm.createContext({ exports: {}, require: name => {
    if (name === 'vue') return { ...vue, onMounted() {}, onBeforeUnmount() {}, watch() {} }
    if (name === 'vue-router') return { useRoute: () => ({ params: { pathMatch: ['review', 'test'] }, query: {} }), useRouter: () => ({}) }
    if (name === '../state') return { state: { user: { id: 'test' }, context: {} }, post: options.post, api: options.api }
    return {}
  } })
  vm.runInContext(compile(compileScript(descriptor, { id: 'career-test' }).content), context)
  return context.exports.default.setup({}, { expose() {} })
}

test('authorize all includes every editable fact and excludes locked facts', () => {
  const editor = careerEditor()
  editor.draftFacts.value = [{ id: 'education', locked: true }, { id: 'experience', locked: false }, { id: 'skills', locked: false }]
  editor.selectAll()
  assert.deepEqual(Array.from(editor.approved.value), ['experience', 'skills'])
  assert.equal(editor.draftFacts.value[0].locked, true)
})

test('diagnosis fixes model bold markers with trailing spaces before rendering', () => {
  const editor = careerEditor()
  editor.session.value = { diagnosis: { analysis: '## 总体判断\n\n**优先建议 **\n\n**正常加粗**' } }
  assert.equal(editor.diagnosisText.value, '## 总体判断\n\n**优先建议**\n\n**正常加粗**')
})

test('bulk authorization toggles off and experience toggle preserves other selections', () => {
  const editor = careerEditor()
  editor.draftFacts.value = [{ id: 'locked', locked: true }, { id: 'work', section: 'experience' }, { id: 'skill', section: 'skills' }]
  editor.selectAll()
  assert.equal(editor.allAuthorized.value, true)
  editor.selectExperience()
  assert.deepEqual(Array.from(editor.approved.value), ['skill'])
  editor.selectExperience()
  assert.equal(editor.allAuthorized.value, true)
  editor.selectAll()
  assert.deepEqual(Array.from(editor.approved.value), [])
})

test('suggestions remain separate until confirmed and never generate a version', async () => {
  const calls = []
  let reply
  const editor = careerEditor({ post: (path, body) => { calls.push({ path, body }); return new Promise(resolve => { reply = resolve }) } })
  editor.facts.value = [{ id: 'f1', text: '原文' }]
  editor.draftFacts.value = [{ id: 'f1', text: '原文' }]
  editor.approved.value = ['f1']
  editor.rewriteInstruction.value = '突出个人行动'
  const task = editor.suggest()
  assert.equal(editor.suggesting.value, true)
  assert.equal(editor.generating.value, false)
  reply({ patches: [{ fact_id: 'f1', text: '建议改写', reason: '表达更清晰' }] })
  await task
  assert.equal(editor.draftFacts.value[0].text, '原文')
  assert.equal(editor.pendingSuggestions.value.f1.text, '建议改写')
  assert.equal(calls.length, 1)
  assert.ok(calls[0].path.endsWith('/suggest-rewrite'))
  assert.equal(calls[0].body.instruction, '突出个人行动')
  editor.acceptSuggestion('f1')
  assert.equal(editor.draftFacts.value[0].text, '建议改写')
  assert.equal(editor.facts.value[0].text, '原文')
  assert.equal(editor.pendingSuggestions.value.f1, undefined)
  assert.equal(editor.versions.value.length, 0)
})

test('suggestion cannot overwrite text edited after the suggestion was generated', async () => {
  const editor = careerEditor({ post: async () => ({ patches: [{ fact_id: 'f1', text: '建议', reason: '说明' }] }) })
  editor.draftFacts.value = [{ id: 'f1', text: '原文' }]
  editor.approved.value = ['f1']
  await editor.suggest()
  editor.draftFacts.value[0].text = '手动新内容'
  editor.acceptSuggestion('f1')
  assert.equal(editor.draftFacts.value[0].text, '手动新内容')
  assert.ok(editor.error.value)
})

test('requesting suggestions without authorization gives a useful message', async () => {
  const editor = careerEditor({ post: () => { throw new Error('must not call API') } })
  await editor.suggest()
  assert.match(editor.error.value, /授权/)
})

test('only a confirmed suggestion is sent to version generation with the selected template', async () => {
  const calls = []
  const editor = careerEditor({
    post: async (path, body) => {
      calls.push({ path, body })
      if (path.endsWith('/suggest-rewrite')) return { patches: [{ fact_id: 'f1', text: '确认后的新表达', reason: '更清晰' }] }
      return { id: 'v1', facts: [{ id: 'f1', text: '确认后的新表达' }] }
    },
    api: async () => ({ job: { status: 'queued' } })
  })
  editor.facts.value = [{ id: 'f1', text: '原文' }]
  editor.draftFacts.value = [{ id: 'f1', text: '原文' }]
  editor.approved.value = ['f1']
  editor.template.value = 'classic-cn'
  await editor.suggest()
  await editor.rewrite()
  assert.equal(calls.length, 1)
  assert.equal(editor.versions.value.length, 0)
  editor.acceptSuggestion('f1')
  await editor.rewrite()
  assert.equal(calls.length, 2)
  assert.ok(calls[1].path.endsWith('/approve-rewrite'))
  assert.equal(calls[1].body.patches[0].text, '确认后的新表达')
  assert.equal(calls[1].body.template, 'classic-cn')
  assert.equal(editor.versions.value.length, 1)
})

test('failed suggestion request restores controls and preserves the original text', async () => {
  const editor = careerEditor({ post: async () => { throw new Error('模型服务暂不可用') } })
  editor.draftFacts.value = [{ id: 'f1', text: '原文' }]
  editor.approved.value = ['f1']
  await editor.suggest()
  assert.equal(editor.suggesting.value, false)
  assert.equal(editor.generating.value, false)
  assert.equal(editor.draftFacts.value[0].text, '原文')
  assert.match(editor.error.value, /模型服务/)
})

test('a suggestion response from a previous resume view is discarded', async () => {
  let reply
  const editor = careerEditor({ post: () => new Promise(resolve => { reply = resolve }) })
  editor.draftFacts.value = [{ id: 'f1', text: '原文' }]
  editor.approved.value = ['f1']
  const task = editor.suggest()
  editor.resetSuggestions()
  reply({ patches: [{ fact_id: 'f1', text: '过期建议' }] })
  await task
  assert.equal(editor.pendingCount.value, 0)
  assert.equal(editor.draftFacts.value[0].text, '原文')
})

test('version generation errors belong to the confirmation action rather than suggestion feedback', async () => {
  const editor = careerEditor({post:async()=>{throw new Error('具体字段错误')}})
  editor.facts.value=[{id:'f1',text:'原文'}]
  editor.draftFacts.value=[{id:'f1',text:'修改'}]
  editor.approved.value=['f1']
  await editor.rewrite()
  assert.equal(editor.error.value,'')
  assert.equal(editor.versionError.value,'具体字段错误')
  assert.equal(editor.generating.value,false)
})

test('artifact loading failure does not turn a saved version into a generation failure', async () => {
  const editor = careerEditor({post:async()=>({id:'saved',facts:[{id:'f1',text:'修改'}]}),api:async()=>{throw new Error('下载信息暂不可用')}})
  editor.facts.value=[{id:'f1',text:'原文'}]
  editor.draftFacts.value=[{id:'f1',text:'修改'}]
  editor.approved.value=['f1']
  await editor.rewrite()
  assert.equal(editor.versions.value.length,1)
  assert.match(editor.versionNotice.value,/已保存/)
  assert.match(editor.versionError.value,/已保存/)
  assert.equal(editor.approved.value.length,0)
})
