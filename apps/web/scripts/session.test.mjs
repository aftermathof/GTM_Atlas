import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('../src/state.ts', import.meta.url), 'utf8')
function compileState(apiOrigin = '') {
  return ts.transpileModule(source.replace('import.meta.env.VITE_API_BASE_URL', JSON.stringify(apiOrigin)), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
}
const compiled = compileState()

test('preloading a large catalog keeps its first article available for instant opening',async()=>{
  let requests=0
  const app=load(storage({'atlas-token':'alice'}),storage(),async url=>{
    requests++;return new Response(JSON.stringify({id:url.split('/').pop(),body:'完整正文'}))
  })
  await Promise.all(Array.from({length:150},(_,i)=>app.knowledgeDocument('d'+i)))
  assert.equal(app.peekKnowledge('/knowledge/documents/d0').body,'完整正文')
  await app.knowledgeDocument('d0')
  assert.equal(requests,150)
  app.clearSession()
  assert.equal(app.peekKnowledge('/knowledge/documents/d0'),undefined)
})

function storage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key)
  }
}

function load(localStorage = storage(), sessionStorage = storage(), fetch = async () => {
  throw new Error('Unexpected network request')
}, clock = Date, apiOrigin = '') {
  const listeners = new Map()
  const context = vm.createContext({
    exports: {}, localStorage, sessionStorage, fetch, Headers, FormData, Date: clock,
    window: { addEventListener: (name, handler) => listeners.set(name, handler) },
    require: name => {
      assert.equal(name, 'vue')
      return { reactive: value => value }
    }
  })
  vm.runInContext(apiOrigin ? compileState(apiOrigin) : compiled, context)
  return { ...context.exports, localStorage, sessionStorage, listeners }
}

test('API origin strips pasted whitespace before building request URLs', async()=>{
  for(const value of ['  https://example.test   ', '\nhttps://example.test/ \r\n']) {
    const urls=[]
    const app=load(storage(),storage(),async url=>{urls.push(url);return new Response(JSON.stringify({status:'ok'}))},Date,value)
    await app.api('/health')
    assert.equal(app.API_ORIGIN,'https://example.test')
    assert.deepEqual(urls,['https://example.test/api/v1/health'])
  }
})

test('rewrite network interruption is explained without retrying the POST or clearing login', async()=>{
  let calls=0
  const app=load(storage({'atlas-token':'access'}),storage(),async()=>{calls++;throw new TypeError('Failed to fetch')})
  await assert.rejects(app.post('/career/sessions/test/block-dialogue',{}),/改写.*连接.*中断/)
  assert.equal(calls,1)
  assert.equal(app.state.token,'access')
})

test('gateway errors and model errors are distinguished for rewrite requests', async()=>{
  const gateway=load(storage(),storage(),async()=>new Response('<html>Bad Gateway</html>',{status:502}))
  await assert.rejects(gateway.post('/career/sessions/test/block-dialogue',{}),/网关.*502/)
  const model=load(storage(),storage(),async()=>new Response(JSON.stringify({detail:'模型服务暂不可用，请保留草稿后重试'}),{status:502}))
  await assert.rejects(model.post('/career/sessions/test/block-dialogue',{}),/模型服务暂不可用/)
})

test('interruption while reading a rewrite response retains a useful error', async()=>{
  const app=load(storage(),storage(),async()=>({ok:true,json:async()=>{throw new TypeError('Failed to fetch')}}))
  await assert.rejects(app.post('/career/sessions/test/block-dialogue',{}),/改写结果读取失败/)
})

test('login survives closing a tab and recreating application state', () => {
  const disk = storage()
  load(disk).saveSession({ token: 'access', refresh_token: 'refresh' })
  const reopened = load(disk)
  assert.equal(reopened.state.token, 'access')
  assert.equal(disk.getItem('atlas-refresh'), 'refresh')
  assert.equal(reopened.sessionStorage.getItem('atlas-token'), null)
})

test('application startup restores the signed-in user from persistent credentials', async () => {
  const app = load(storage({ 'atlas-token': 'access', 'atlas-refresh': 'refresh' }), storage(), async (url, options) => {
    if (url.endsWith('/auth/me')) {
      assert.equal(options.headers.get('Authorization'), 'Bearer access')
      return new Response(JSON.stringify({ id: 'user', preferences: { role: 'gtm' } }))
    }
    return new Response(JSON.stringify(url.endsWith('/health') ? { status: 'ok' } : []))
  })
  await app.initialize()
  assert.equal(app.state.user.id, 'user')
  assert.equal(app.state.context.role, 'gtm')
})

test('existing tab session migrates once to persistent storage', () => {
  const old = storage({ 'atlas-token': 'old-access', 'atlas-refresh': 'old-refresh' })
  const app = load(storage(), old)
  assert.equal(app.localStorage.getItem('atlas-token'), 'old-access')
  assert.equal(app.localStorage.getItem('atlas-refresh'), 'old-refresh')
  assert.equal(old.getItem('atlas-token'), null)
  assert.equal(old.getItem('atlas-refresh'), null)
})

test('newer persistent session wins over an older tab session', () => {
  const disk = storage({ 'atlas-token': 'new', 'atlas-refresh': 'new-refresh' })
  const old = storage({ 'atlas-token': 'old', 'atlas-refresh': 'old-refresh' })
  const app = load(disk, old)
  assert.equal(app.state.token, 'new')
  assert.equal(disk.getItem('atlas-refresh'), 'new-refresh')
  assert.equal(old.getItem('atlas-token'), null)
})

test('expired access refreshes, persists rotated credentials and retries request', async () => {
  const disk = storage({ 'atlas-token': 'expired', 'atlas-refresh': 'refresh' })
  const calls = []
  const app = load(disk, storage(), async (url, options) => {
    calls.push(url)
    if (url.endsWith('/auth/refresh')) {
      assert.equal(JSON.parse(options.body).refresh_token, 'refresh')
      return new Response(JSON.stringify({ token: 'renewed', refresh_token: 'rotated' }))
    }
    return options.headers.get('Authorization') === 'Bearer renewed'
      ? new Response(JSON.stringify({ id: 'user', preferences: {} }))
      : new Response('{}', { status: 401 })
  })
  assert.equal((await app.api('/auth/me')).id, 'user')
  assert.equal(calls.length, 3)
  assert.equal(load(disk).state.token, 'renewed')
  assert.equal(disk.getItem('atlas-refresh'), 'rotated')
})

test('temporary refresh network failure preserves the saved session', async () => {
  const disk = storage({ 'atlas-token': 'expired', 'atlas-refresh': 'refresh' })
  const app = load(disk, storage(), async url => {
    if (url.endsWith('/auth/refresh')) throw new Error('offline')
    return new Response('{}', { status: 401 })
  })
  await assert.rejects(app.api('/auth/me'), /offline/)
  assert.equal(disk.getItem('atlas-refresh'), 'refresh')
})

test('revoked refresh session is removed rather than retried forever', async () => {
  const disk = storage({ 'atlas-token': 'expired', 'atlas-refresh': 'revoked' })
  const app = load(disk, storage(), async () => new Response('{}', { status: 401 }))
  await assert.rejects(app.api('/auth/me'), /请重新登录/)
  assert.equal(disk.getItem('atlas-token'), null)
  assert.equal(disk.getItem('atlas-refresh'), null)
})

test('explicit logout removes saved credentials and cannot restore on reopen', () => {
  const disk = storage({ 'atlas-token': 'access', 'atlas-refresh': 'refresh' })
  const app = load(disk)
  app.state.user = { id: 'user' }
  app.clearSession()
  assert.equal(app.state.user, null)
  assert.equal(load(disk).state.token, '')
  assert.equal(disk.getItem('atlas-refresh'), null)
})

test('logout in another tab clears the active user and access token', () => {
  const app = load(storage({ 'atlas-token': 'access', 'atlas-refresh': 'refresh' }))
  app.state.user = { id: 'user' }
  app.listeners.get('storage')?.({ storageArea: app.localStorage, key: 'atlas-token', newValue: null })
  assert.equal(app.state.user, null)
  assert.equal(app.state.token, '')
})

test('revisiting or concurrently loading the same catalog reuses one request', async () => {
  let calls = 0
  const app = load(storage(), storage(), async () => { calls++; return new Response(JSON.stringify({ items: [{ id: 'public' }] })) })
  await Promise.all([app.knowledgeDocuments('limit=100'), app.knowledgeDocuments('limit=100')])
  await app.knowledgeDocuments('limit=100')
  assert.equal(calls, 1)
})

test('catalog cache separates filters and authenticated users and clears on logout', async () => {
  let calls = 0
  const app = load(storage(), storage(), async () => { calls++; return new Response(JSON.stringify({ items: [] })) })
  await app.knowledgeDocuments('role=pmm')
  await app.knowledgeDocuments('role=sales')
  app.saveSession({ token: 'user-access', refresh_token: 'refresh' })
  await app.knowledgeDocuments('role=pmm')
  app.clearSession()
  await app.knowledgeDocuments('role=pmm')
  assert.equal(calls, 4)
})

test('a successful upload invalidates cached knowledge lists', async () => {
  let calls = 0
  const app = load(storage(), storage(), async () => { calls++; return new Response(JSON.stringify({ items: [] })) })
  await app.knowledgeDocuments('limit=100')
  await app.api('/career/job-descriptions', { method: 'POST', body: '{}' })
  await app.knowledgeDocuments('limit=100')
  assert.equal(calls, 3)
})

test('a failed catalog request is retried instead of cached', async () => {
  let calls = 0
  const app = load(storage(), storage(), async () => {
    calls++
    return new Response(JSON.stringify({ items: [] }), { status: calls === 1 ? 503 : 200 })
  })
  await assert.rejects(app.knowledgeDocuments('limit=100'))
  await app.knowledgeDocuments('limit=100')
  assert.equal(calls, 2)
})

test('catalog cache lasts across navigation until explicitly refreshed', async () => {
  let calls = 0, now = 0
  const app = load(storage(), storage(), async () => { calls++; return new Response('{"items":[]}') }, { now: () => now })
  await app.knowledgeDocuments('limit=100')
  now = 600_001
  await app.knowledgeDocuments('limit=100')
  assert.equal(calls, 1)
  app.refreshKnowledge()
  await app.knowledgeDocuments('limit=100')
  assert.equal(calls, 2)
})

test('history visits share a request and reuse results until a relevant mutation', async () => {
  let calls = 0, now = 0
  const app = load(storage({ 'atlas-token': 'user' }), storage(), async () => {
    calls++; return new Response('[{"id":"saved"}]')
  }, { now: () => now })
  await Promise.all([app.historyRecords(), app.historyRecords()])
  await app.historyRecords()
  assert.equal(calls, 1)
  now = 30_001
  await app.historyRecords()
  assert.equal(calls, 1)
})

test('conversation records share preloads and invalidate after context resets',async()=>{
  let calls=0
  const app=load(storage({'atlas-token':'alice'}),storage(),async()=>{
    calls++;return new Response('{"id":"thread","messages":[]}')
  })
  await Promise.all([app.api('/ai/conversations/thread'),app.api('/ai/conversations/thread')])
  assert.equal(calls,1)
  assert.equal(app.peekHistory('/ai/conversations/thread').id,'thread')
  await app.post('/ai/conversations/thread/reset',{})
  assert.equal(app.peekHistory('/ai/conversations/thread'),undefined)
  await app.api('/ai/conversations/thread')
  assert.equal(calls,3)
  app.clearSession()
  assert.equal(app.peekHistory('/ai/conversations/thread'),undefined)
})
test('unrelated note writes keep chat history warm and live artifact polling stays fresh',async()=>{
  let calls=0
  const app=load(storage({'atlas-token':'alice'}),storage(),async()=>{
    calls++;return new Response('{}')
  })
  await app.api('/ai/conversations/thread')
  await app.post('/notes',{})
  await app.api('/ai/conversations/thread')
  assert.equal(calls,2)
  await app.api('/career/versions/version/artifacts')
  await app.api('/career/versions/version/artifacts')
  assert.equal(calls,4)
})

test('history is refreshed after mutations and cannot survive account changes', async () => {
  let calls = 0
  const app = load(storage({ 'atlas-token': 'first' }), storage(), async () => {
    calls++; return new Response('[]')
  })
  await app.historyRecords()
  await app.api('/mock/sessions', { method: 'POST', body: '{}' })
  await app.historyRecords()
  app.saveSession({ token: 'second' })
  await app.historyRecords()
  app.clearSession()
  await app.historyRecords()
  assert.equal(calls, 5)
})

test('history failures are not cached', async () => {
  let calls = 0
  const app = load(storage(), storage(), async () => new Response('[]', { status: ++calls === 1 ? 503 : 200 }))
  await assert.rejects(app.historyRecords())
  await app.historyRecords()
  assert.equal(calls, 2)
})

test('startup fetches history while profile validation is still pending', async () => {
  const calls = []
  let finishProfile
  const app = load(storage({ 'atlas-token': 'user' }), storage(), async url => {
    calls.push(url)
    if (url.endsWith('/auth/me')) return new Promise(resolve => { finishProfile = () => resolve(new Response('{"id":"user","preferences":{}}')) })
    return new Response('[]')
  })
  const pending = app.initialize()
  await new Promise(resolve => setImmediate(resolve))
  assert.ok(calls.includes('/api/v1/history'))
  finishProfile()
  await pending
  await app.historyRecords()
  assert.equal(calls.filter(url => url.endsWith('/history')).length, 1)
})

test('resume display names use Shanghai dates and chronological same-day suffixes', async () => {
  const rows = [
    {id:'third',kind:'career',created_at:'2026-10-24T08:00:00Z'},
    {id:'chat',kind:'chat_thread',created_at:'2026-10-24T01:00:00Z'},
    {id:'second',kind:'career',created_at:'2026-10-24T00:00:00Z'},
    {id:'first',kind:'career',created_at:'2026-10-23T16:01:00Z'},
    {id:'yesterday',kind:'career',created_at:'2026-10-23T15:59:00Z'}
  ]
  const app = load(storage(), storage(), async () => new Response(JSON.stringify(rows)))
  const result = await app.historyRecords()
  assert.deepEqual(Array.from(result, row => row.display_name), ['20261024n2',undefined,'20261024n1','20261024','20261023'])
  assert.deepEqual(Array.from(result, row => row.id), rows.map(row => row.id))
})

test('validation errors identify the affected field without exposing rejected private text', async () => {
  const app = load(storage(), storage(), async () => new Response(JSON.stringify({detail:[
    {loc:['body','patches',1,'text'],type:'string_too_long',msg:'String should have at most 4000 characters',ctx:{max_length:4000},input:'private resume text'}
  ]}),{status:422}))
  await assert.rejects(app.api('/career/sessions/test/approve-rewrite',{method:'POST',body:'{}'}), error => {
    assert.match(error.message, /改写段落.*2.*内容/)
    assert.match(error.message, /4000/)
    assert.ok(!error.message.includes('private resume text'))
    return true
  })
})


test('article bodies share requests and remain cached after AI requests', async()=>{
  const calls=[]
  const app=load(storage(),storage(),async url=>{calls.push(url);return new Response(JSON.stringify({id:'read',body:'## 正文',meta:{}}))})
  await Promise.all([app.knowledgeDocument('read'),app.knowledgeDocument('read')])
  await app.api('/ai/chat',{method:'POST',body:'{}'})
  await app.knowledgeDocument('read')
  assert.equal(calls.filter(url=>url.endsWith('/knowledge/documents/read')).length,1)
  assert.equal(app.peekKnowledge('/knowledge/documents/read').body,'## 正文')
  app.refreshKnowledge()
  assert.equal(app.peekKnowledge('/knowledge/documents/read'),undefined)
  await app.knowledgeDocument('read')
  assert.equal(calls.filter(url=>url.endsWith('/knowledge/documents/read')).length,2)
})

test('private article caches cannot survive logout and switching accounts',async()=>{
  let calls=0
  const app=load(storage({'atlas-token':'first'}),storage(),async()=>{calls++;return new Response('{"body":"private"}')})
  await app.knowledgeDocument('private')
  app.clearSession()
  assert.equal(app.peekKnowledge('/knowledge/documents/private'),undefined)
  app.saveSession({token:'second'})
  await app.knowledgeDocument('private')
  assert.equal(calls,2)
})


test('profile restoration is shared and does not wait for catalog availability',async()=>{
  let finish, calls=0
  const app=load(storage({'atlas-token':'saved'}),storage(),async url=>{
    assert.equal(url,'/api/v1/auth/me')
    calls++
    return new Promise(resolve=>{finish=()=>resolve(new Response('{"id":"user","preferences":{}}'))})
  })
  const first=app.restoreSession(), second=app.restoreSession()
  assert.equal(calls,1)
  finish();await Promise.all([first,second])
  assert.equal(app.state.user.id,'user')
  await app.restoreSession()
  assert.equal(calls,1)
})

test('an expired profile cannot grant access and anonymous restoration needs no request',async()=>{
  const anonymous=load()
  await anonymous.restoreSession()
  assert.equal(anonymous.state.user,null)
  const expired=load(storage({'atlas-token':'expired'}),storage(),async()=>new Response('{"detail":"请重新登录"}',{status:401}))
  await expired.restoreSession()
  assert.equal(expired.state.user,null)
  assert.equal(expired.state.token,'')
})
