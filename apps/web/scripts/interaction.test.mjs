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

function glossarySearch() {
  const {descriptor}=parse(readFileSync(new URL('../src/components/GtmGlossary.vue',import.meta.url),'utf8'))
  const entries=JSON.parse(readFileSync(new URL('../../../knowledge/glossary/gtm-glossary.json',import.meta.url),'utf8'))
  const context=vm.createContext({exports:{},require:name=>{
    if(name==='vue') return vue
    if(name==='../content/gtm-glossary') return {gtmGlossary:entries}
    return {}
  }})
  vm.runInContext(compile(compileScript(descriptor,{id:'glossary-search-test'}).content),context)
  return {component:context.exports.default.setup({},{expose(){}}),entries}
}

test('glossary search matches terms full names explanations and examples without case sensitivity',()=>{
  const {component}=glossarySearch()
  for(const [query,expected] of [['  cac  ',['CAC','LTV']],['customer acquisition',['CAC']],['关键意见领袖',['KOL']],['东南亚',['GTM']]]) {
    component.query.value=query
    assert.deepEqual(Array.from(component.filteredGlossary.value,item=>item.term),expected)
  }
})

test('clearing glossary search restores all entries and unmatched text gives no results',()=>{
  const {component,entries}=glossarySearch()
  component.query.value='no-such-term-xyz'
  assert.equal(component.filteredGlossary.value.length,0)
  component.query.value='   '
  assert.equal(component.filteredGlossary.value.length,entries.length)
})

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

test('exiting an unanswered Mock discards it without keeping a history entry', async () => {
  const calls=[]
  const app=mockInterview(false,{api:async(path,options)=>{calls.push({path,options});return {deleted:true}}})
  app.component.session.value={id:'empty-mock',answers:[]}
  app.component.draft.value='尚未提交的草稿'
  await app.component.exitMock()
  assert.equal(calls[0].path,'/mock/sessions/empty-mock?only_if_unanswered=true')
  assert.equal(calls[0].options.method,'DELETE')
  assert.equal(app.confirmations.length,0)
  assert.deepEqual(app.navigations,['/interviews'])
})

test('loading a historical Mock has its own pending state', async () => {
  let finish
  const app=mockInterview(true,{pathMatch:['mock','test','report'],api:()=>new Promise(resolve=>{finish=resolve})})
  const pending=app.component.load()
  assert.equal(app.component.loading.value,true)
  finish({id:'test',answers:[{question:'已答题',answer:'已保存回答',evaluation:{feedback:'建议'}}]})
  await pending
  assert.equal(app.component.loading.value,false)
  assert.equal(app.component.report.value.answers.length,1)
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
    if (name === '../resumeText') {
      const helper = { exports: {} }
      vm.runInNewContext(compile(readFileSync(new URL('../src/resumeText.ts', import.meta.url), 'utf8')), helper)
      return helper.exports
    }
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

function readyBlock(editor, text = '原文') {
  editor.facts.value = [{ id:'f1', text:'原文', section:'experience' }, { id:'f2', text:'第二行', section:'experience' }]
  editor.draftFacts.value = editor.facts.value.map(f=>({...f}))
  editor.blockRows.value = [{ id:'f1', title:'实习经历 1', fact_ids:['f1','f2'], text, original:'原文' }]
  editor.approved.value = ['f1','f2']
  return editor.blockRows.value[0]
}

test('block dialogue opens with the whole current experience and only confirmation replaces it', () => {
  const editor = careerEditor()
  const block = readyBlock(editor)
  editor.openBlock(block)
  assert.equal(editor.activeBlockId.value, 'f1')
  assert.equal(editor.blockChats.value.f1.original, '原文')
  assert.equal(block.text, '原文')
  editor.acceptBlock('整块新内容', '原文')
  assert.equal(block.text, '整块新内容')
  assert.equal(editor.facts.value[0].text, '原文')
  assert.equal(editor.activeBlockId.value, '')
  assert.equal(editor.versions.value.length, 0)
})

test('partially authorized blocks cannot open AI rewrite or generate a version', () => {
  const editor = careerEditor()
  const block = readyBlock(editor, '改写')
  editor.approved.value = ['f1']
  editor.openBlock(block)
  assert.equal(editor.activeBlockId.value, '')
  assert.equal(editor.hasChanges.value, false)
})

test('a stale block suggestion cannot overwrite a manual edit', () => {
  const editor = careerEditor()
  const block = readyBlock(editor)
  editor.openBlock(block)
  block.text = '手动新内容'
  editor.acceptBlock('过期建议', '原文')
  assert.equal(block.text, '手动新内容')
  assert.match(editor.error.value, /原文已修改/)
})

test('version generation sends an authorized whole block and selected template', async () => {
  const calls = []
  const editor = careerEditor({ post:async(path,body)=>{ calls.push({path,body}); return {id:'v1',facts:[{id:'f1',text:'完整新经历'}]} }, api:async()=>({job:{status:'queued'}}) })
  readyBlock(editor, '完整新经历')
  editor.template.value = 'classic-cn'
  await editor.rewrite()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].body.blocks[0].text, '完整新经历')
  assert.deepEqual(Array.from(calls[0].body.blocks[0].fact_ids), ['f1','f2'])
  assert.equal(calls[0].body.template, 'classic-cn')
  assert.equal(editor.versions.value.length, 1)
})

test('closing and reopening the same unmodified block preserves its dialogue', () => {
  const editor = careerEditor()
  const block = readyBlock(editor)
  editor.openBlock(block)
  editor.blockChats.value.f1.turns.push({message:'突出调研',text:'建议内容'})
  editor.activeBlockId.value = ''
  editor.openBlock(block)
  assert.equal(editor.blockChats.value.f1.turns.length, 1)
})

test('version generation errors belong to the confirmation action rather than suggestion feedback', async () => {
  const editor = careerEditor({post:async()=>{throw new Error('具体字段错误')}})
  readyBlock(editor, '修改')
  await editor.rewrite()
  assert.equal(editor.error.value,'')
  assert.equal(editor.versionError.value,'具体字段错误')
  assert.equal(editor.generating.value,false)
})

test('artifact loading failure does not turn a saved version into a generation failure', async () => {
  const editor = careerEditor({post:async()=>({id:'saved',facts:[{id:'f1',text:'修改'}]}),api:async()=>{throw new Error('下载信息暂不可用')}})
  readyBlock(editor, '修改')
  await editor.rewrite()
  assert.equal(editor.versions.value.length,1)
  assert.match(editor.versionNotice.value,/已保存/)
  assert.match(editor.versionError.value,/已保存/)
  assert.equal(editor.approved.value.length,0)
})

function chatPanel(api = async () => [], post = async () => ({ context_after: 2 })) {
  const { descriptor } = parse(readFileSync(new URL('../src/components/ChatPanel.vue', import.meta.url), 'utf8'))
  const context = vm.createContext({ exports: {}, require: name => {
    if (name === 'vue') return { ...vue, watch() {} }
    if (name === 'vue-router') return { useRoute: () => ({ query: {} }), useRouter: () => ({}) }
    if (name === '../state') return { state: { user: { id: 'test' } }, api, post }
    return {}
  } })
  vm.runInContext(compile(compileScript(descriptor, { id: 'chat-test' }).content), context)
  return context.exports.default.setup({}, { expose() {} })
}

test('chat history labels collapse newlines and truncate without splitting Unicode characters', () => {
  const chat = chatPanel()
  assert.equal(chat.shortTitle('题目：  GTM\n用户回答'), '题目： GTM 用户回答')
  assert.equal(chat.shortTitle('😀'.repeat(20)), '😀'.repeat(13) + '…')
  assert.equal(Array.from(chat.shortTitle('长标题'.repeat(20))).length, 14)
})

test('restoring chat history shows pending state and preserves question paragraphs', async () => {
  let finish
  const chat = chatPanel(path => path.endsWith('/saved') ? new Promise(resolve => { finish = resolve }) : Promise.resolve([]))
  const pending = chat.restore('saved')
  assert.equal(chat.restoring.value, true)
  const message = '题目：如何上市？\n\n用户回答：先调研。\n\n请结合资料给出更标准的回答：'
  finish({ id: 'saved', scope: 'global', messages: [{ message, turn: 1, response: { answer: '建议' } }] })
  await pending
  assert.equal(chat.restoring.value, false)
  assert.equal(chat.busy.value, false)
  assert.equal(chat.messages.value[0].question, message)
})

test('failed history restore clears its loading indicator and reports the error', async () => {
  const chat = chatPanel(async () => { throw new Error('记录暂不可用') })
  await chat.restore('missing')
  assert.equal(chat.restoring.value, false)
  assert.equal(chat.busy.value, false)
  assert.equal(chat.error.value, '记录暂不可用')
})

test('resume history stays loading until its version list is ready', async () => {
  let finish
  const editor = careerEditor({ api: path => path.endsWith('/versions') ? new Promise(resolve => { finish = resolve }) : Promise.resolve({ facts: [] }) })
  const pending = editor.load()
  assert.equal(editor.sessionLoading.value, true)
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(editor.sessionLoading.value, true)
  finish([])
  await pending
  assert.equal(editor.sessionLoading.value, false)
})

test('clearing context hides previous turns without deleting saved messages', async () => {
  const chat = chatPanel()
  chat.conversation.value = 'saved'
  chat.messages.value = [{ turn: 1 }, { turn: 2 }]
  await chat.clearContext()
  assert.equal(chat.visibleMessages.value.length, 0)
  assert.equal(chat.messages.value.length, 2)
  chat.messages.value.push({ turn: 3 })
  assert.equal(chat.visibleMessages.value.length, 1)
  await chat.restore('')
  assert.equal(chat.contextAfter.value, 0)
})

function blockDialog(post) {
  const events=[]
  const { descriptor } = parse(readFileSync(new URL('../src/components/BlockRewriteDialog.vue', import.meta.url), 'utf8'))
  const context = vm.createContext({ exports:{}, document:{body:{style:{overflow:''}}}, require:name=>{
    if(name==='vue') return {...vue,onMounted(){},onBeforeUnmount(){}}
    if(name==='../state') return {post}
    return {}
  } })
  vm.runInContext(compile(compileScript(descriptor,{id:'block-dialog-test'}).content),context)
  const dialogue={turns:[],draft:'突出调研',original:'当前整段原文'}
  const component=context.exports.default.setup({block:{fact_ids:['f1','f2']},sessionId:'resume',baseVersionId:'v1',dialogue},{expose(){},emit:(...args)=>events.push(args)})
  return {component,dialogue,events}
}

test('block rewrite sends current text and multi-turn context while leaving the original unchanged', async()=>{
  const requests=[]
  const app=blockDialog(async(path,body)=>{requests.push(body);return {text:'完整新建议',analysis:'与岗位要求关联',questions:'',citations:[]}})
  await app.component.ask()
  assert.equal(requests[0].draft_text,'当前整段原文')
  assert.equal(requests[0].base_version_id,'v1')
  assert.equal(app.dialogue.original,'当前整段原文')
  assert.equal(app.events.length,0)
  app.dialogue.draft='再简洁一点'
  await app.component.ask()
  assert.equal(requests[1].draft_text,'完整新建议')
  assert.equal(requests[1].history[0].message,'突出调研')
  assert.equal(app.dialogue.turns.length,2)
})

test('failed block rewrite retains requirements and existing conversation for retry', async()=>{
  const app=blockDialog(async()=>{throw new Error('模型服务暂不可用')})
  await app.component.ask()
  assert.equal(app.component.busy.value,false)
  assert.equal(app.dialogue.draft,'突出调研')
  assert.equal(app.dialogue.turns.length,0)
  assert.match(app.component.error.value,/模型服务/)
})

function resumeText() {
  const helper={exports:{}}
  vm.runInNewContext(compile(readFileSync(new URL('../src/resumeText.ts',import.meta.url),'utf8')),helper)
  return helper.exports
}

test('resume display strips decorative glyphs and bullets but keeps dates contacts and percentages',()=>{
  const {cleanResumeText}=resumeText()
  assert.equal(cleanResumeText('\ue001📞 13800000000\n• 提升 20%\n▪ 2024–2025 实习\n邮箱：a@example.com'),'13800000000\n提升 20%\n2024–2025 实习\n邮箱：a@example.com')
})

test('diagnosis removes internal citation and fact identifiers while preserving Markdown and figures',()=>{
  const {cleanDiagnosis}=resumeText()
  const text=cleanDiagnosis('## 建议\n见 [[boss-d27686e6c7f6b6300nx50t27GFJV:3]]，参考（f16–f17）。结果 20% **有效** [资料](https://example.com)')
  assert.ok(!text.includes('boss-'))
  assert.ok(!text.includes('f16'))
  assert.ok(!text.includes('f17'))
  assert.match(text,/20%/)
  assert.match(text,/\*\*有效\*\*/)
  assert.match(text,/\[资料\]/)
})


test('resume cleaning removes misdecoded heading icons without stripping accented names',()=>{
  const {cleanResumeText}=resumeText()
  assert.equal(cleanResumeText('ŵ教育背景\nǼ 实习经历\nǼ\nǼvar Andersen\n2026.09–2028.06'), '教育背景\n实习经历\n\nǼvar Andersen\n2026.09–2028.06')
})

test('resume cleaning handles mixed bullets and heading glyphs without erasing meaningful letters',()=>{
  const {cleanResumeText}=resumeText()
  assert.equal(cleanResumeText('• ϻ教育背景\nϻ • 实习经历\nϻ\nϻvar Andersen\nμ = 20\nϻ = 3'), '教育背景\n实习经历\n\nϻvar Andersen\nμ = 20\nϻ = 3')
})

test('both resume screens clean arbitrary decorative heading prefixes and flag unreadable body text',()=>{
  const {cleanResumeText}=resumeText()
  for (const prefix of ['ˌ ', 'ë ', 'Ӝ ', '¤ ', '• ë ', 'ˌ\të ', '\uFFFD ']) {
    for (const heading of ['项目经历','实习经历','教育背景','工作经历','技能特长']) {
      assert.equal(cleanResumeText(prefix+heading),heading)
    }
  }
  assert.equal(cleanResumeText('Zoë Müller\në 是荷兰语变音字母\nμ = 20\nGTM 项目经历\nC++ / C#\n姓名：张\uFFFD'), 'Zoë Müller\në 是荷兰语变音字母\nμ = 20\nGTM 项目经历\nC++ / C#\n姓名：张[待确认]')
})

test('loading saved facts and a historical version applies the same heading cleanup',async()=>{
  const facts=[{id:'f0',text:'ˌ 项目经历',section:'projects'},{id:'f1',text:'ë 实习经历',section:'experience'}]
  const editor=careerEditor({api:async path=>{
    if(path==='/career/sessions/test') return {facts,confirmed:true}
    if(path.endsWith('/versions')) return []
    if(path.includes('/editing-blocks')) return {blocks:[{id:'f0',fact_ids:['f0']},{id:'f1',fact_ids:['f1']}]}
    if(path.endsWith('/artifacts')) return {pdf:null}
    throw new Error('Unexpected route: '+path)
  }})
  await editor.load()
  assert.deepEqual(Array.from(editor.facts.value,f=>f.text),['项目经历','实习经历'])
  await editor.selectVersion({id:'v1',facts})
  editor.tab.value='editor'
  await editor.loadBlocks()
  assert.deepEqual(Array.from(editor.blockRows.value,b=>b.text),['项目经历','实习经历'])
  assert.equal(facts[0].text,'ˌ 项目经历')
})


test('authorize all excludes unlocked lines inside a locked merged education block',()=>{
  const editor=careerEditor()
  editor.draftFacts.value=[{id:'f0',locked:true},{id:'f1',locked:false},{id:'f2',locked:false}]
  editor.blockRows.value=[{id:'f0',section:'education',fact_ids:['f0','f1'],locked:true},{id:'f2',section:'experience',fact_ids:['f2'],locked:false}]
  editor.selectAll()
  assert.deepEqual(Array.from(editor.approved.value),['f2'])
  assert.equal(editor.allAuthorized.value,true)
})


test('article table of contents uses rendered headings and scrolls duplicate titles independently',async()=>{
  const {descriptor}=parse(readFileSync(new URL('../src/components/ArticleBody.vue',import.meta.url),'utf8'))
  const context=vm.createContext({exports:{},require:name=>name==='vue'?{...vue,onMounted(){},watch(){}}:{}})
  vm.runInContext(compile(compileScript(descriptor,{id:'article-body-test'}).content),context)
  const app=context.exports.default.setup({source:'## 相同标题\n### 相同标题'},{expose(){},emit(){}})
  const scrolled=[]
  app.article.value={querySelectorAll:()=>[
    {textContent:'相同标题',tagName:'H2',scrollIntoView:()=>scrolled.push(0)},
    {textContent:'相同标题',tagName:'H3',scrollIntoView:()=>scrolled.push(1)}
  ]}
  await app.syncHeadings()
  assert.equal(app.headings.value.length,2)
  assert.equal(app.headings.value[1].depth,3)
  app.scrollToHeading(1)
  assert.deepEqual(scrolled,[1])
})
