import { reactive } from 'vue'

export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')
type CachedResult = { expires: number; pending: Promise<any>; value?: any }
const listCache = new Map<string, CachedResult>()
const knowledgeCache = new Map<string, CachedResult>()
const privateHistoryCache = new Map<string, CachedResult>()
const deletedHistory = new Set<string>()
let sessionGeneration=0
export function isHistoryDeleted(id: string) { return deletedHistory.has(state.token+'\n'+id) }

if (!localStorage.getItem('atlas-token') && sessionStorage.getItem('atlas-token')) {
  for (const key of ['atlas-token', 'atlas-refresh']) {
    const value = sessionStorage.getItem(key)
    if (value) localStorage.setItem(key, value)
  }
}
sessionStorage.removeItem('atlas-token'); sessionStorage.removeItem('atlas-refresh')

export const state = reactive({
  user: null as any,
  token: localStorage.getItem('atlas-token') || '',
  context: { role: 'gtm', role_raw: '', industry: '', language: 'zh-CN', region: '', seniority: 'intern', business_model: 'unknown' },
  roles: [] as any[], industries: [] as any[], health: null as any,
  assistant: false, assistantBusy: false, assistantRequest: null as { question: string } | null,
  scope: 'global', documentId: '', careerId: '', notice: '', historyRevision: 0,
  notesRevision: 0, notesDeleteError: '', knowledgeRevision: 0
})

export function saveSession(value: any, renewal=false) {
  if(!renewal)sessionGeneration++
  deletedHistory.clear()
  listCache.clear(); knowledgeCache.clear(); privateHistoryCache.clear()
  state.token = value.token
  localStorage.setItem('atlas-token', value.token)
  if (value.refresh_token) localStorage.setItem('atlas-refresh', value.refresh_token)
  else localStorage.removeItem('atlas-refresh')
}

export function clearSession() {
  sessionGeneration++
  deletedHistory.clear()
  listCache.clear(); knowledgeCache.clear(); privateHistoryCache.clear()
  state.user = null; state.token = ''
  localStorage.removeItem('atlas-token'); localStorage.removeItem('atlas-refresh')
  sessionStorage.removeItem('atlas-token'); sessionStorage.removeItem('atlas-refresh')
}

window.addEventListener('storage', event => {
  if(event.storageArea===localStorage && event.key==='atlas-knowledge-revision'){knowledgeCache.clear();state.knowledgeRevision++;return}
  if (event.storageArea !== localStorage || (event.key !== 'atlas-token' && event.key !== null)) return
  sessionGeneration++
  deletedHistory.clear()
  listCache.clear(); knowledgeCache.clear(); privateHistoryCache.clear()
  state.token = event.key === null ? '' : event.newValue || ''
  if (!state.token) state.user = null
})

let refreshing: Promise<void> | null = null
async function refreshSession() {
  if (!refreshing) refreshing = (async () => {
    const token = localStorage.getItem('atlas-refresh')
    if (!token) throw new Error('请重新登录')
    const r = await fetch(API_ORIGIN + '/api/v1/auth/refresh', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({refresh_token:token}) })
    if(localStorage.getItem('atlas-refresh')!==token)throw new Error('登录状态已改变，请重新登录')
    if (!r.ok) {
      if (r.status === 400 || r.status === 401) clearSession()
      throw new Error(r.status >= 500 ? '登录服务暂时不可用，请稍后重试' : '登录已过期，请重新登录')
    }
    const session=await r.json()
    if(localStorage.getItem('atlas-refresh')!==token)throw new Error('登录状态已改变，请重新登录')
    saveSession(session,true)
  })().finally(() => { refreshing = null })
  return refreshing
}

export function logoutSession(): Promise<void> {
  const token=state.token
  clearSession()
  if(!token)return Promise.resolve()
  return fetch(API_ORIGIN+'/api/v1/auth/logout',{
    method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:'{}',keepalive:true,
  }).then(response=>{if(!response.ok && response.status!==401)throw new Error('服务端会话撤销暂未完成')})
}

export async function authorizedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const generation=sessionGeneration
  const headers = new Headers(options.headers)
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  let r = await fetch(API_ORIGIN + path, { ...options, headers })
  if (r.status === 401 && generation===sessionGeneration && localStorage.getItem('atlas-refresh') && !path.startsWith('/api/v1/auth/login') && !path.startsWith('/api/v1/auth/register')) {
    await refreshSession()
    if(generation!==sessionGeneration)return r
    headers.set('Authorization', `Bearer ${state.token}`)
    r = await fetch(API_ORIGIN + path, {...options, headers})
  }
  return r
}

function historyPath(path: string) {
  return path === '/history' || path === '/history?prefetch=true' || /^\/ai\/conversations(?:\/[^/?]+)?$/.test(path) ||
    /^\/mock\/sessions\/[^/?]+(?:\/report)?$/.test(path) ||
    /^\/career\/sessions\/[^/?]+(?:\/versions|\/editing-blocks(?:\?[^#]*)?)?$/.test(path)
}
export function peekHistory(path: string) { return privateHistoryCache.get(state.token + '\n' + path)?.value }
export function api(path: string, options: RequestInit = {}): Promise<any> {
  return (options.method || 'GET').toUpperCase() === 'GET' && historyPath(path)
    ? cachedList(path, Infinity, privateHistoryCache) : requestApi(path, options)
}
function invalidateHistory(path: string) {
  const chat = path.startsWith('/ai/chat') || path.startsWith('/ai/conversations')
  const mock = path.startsWith('/mock/'), career = path.startsWith('/career/') && !/\/(block-dialogue|suggest-rewrite)$/.test(path)
  const mockId = path.match(/^\/mock\/sessions\/([^/?]+)/)?.[1]
  const careerId = path.match(/^\/career\/sessions\/([^/?]+)/)?.[1]
  for (const key of privateHistoryCache.keys()) {
    const cachedPath = key.slice(key.indexOf('\n') + 1)
    if (((chat || mock || career) && cachedPath.startsWith('/history')) ||
        (chat && cachedPath.startsWith('/ai/conversations')) ||
        (mock && mockId && cachedPath.startsWith('/mock/sessions/'+mockId+'/')) ||
        (mock && cachedPath === '/mock/sessions/'+mockId) ||
        (career && careerId && (cachedPath === '/career/sessions/'+careerId || cachedPath.startsWith('/career/sessions/'+careerId+'/')))) privateHistoryCache.delete(key)
  }
}
async function requestApi(path: string, options: RequestInit = {}): Promise<any> {
  const ownerToken=state.token
  const ownerSession=sessionGeneration
  const rewriting = path.endsWith('/block-dialogue')
  let r: Response
  try { r = await authorizedFetch('/api/v1' + path, options) }
  catch (error: any) {
    if (rewriting && error?.name === 'TypeError') throw new Error('改写请求的网络连接中断，未收到生成结果；当前输入已保留，请重试。')
    throw error
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    if (r.status === 401 && ownerSession===sessionGeneration && !path.startsWith('/auth/login')) clearSession()
    if (typeof body.detail === 'string') throw new Error(body.detail)
    if (Array.isArray(body.detail) && body.detail.length) {
      const labels: Record<string,string> = {patches:'改写段落',text:'内容',approved_fact_ids:'授权段落',template:'排版模板',base_version_id:'基础版本',facts:'简历事实',count:'题目数量'}
      const details = body.detail.slice(0,3).map((issue: any) => {
        const field = (issue.loc || []).filter((key: any) => key !== 'body').map((key: any) => typeof key === 'number' ? String(key+1) : labels[key] || key).join(' / ')
        const reasons: Record<string,string> = {string_too_short:`至少需要 ${issue.ctx?.min_length || 1} 个字符`,string_too_long:`最多允许 ${issue.ctx?.max_length} 个字符`,missing:'缺少必填内容',literal_error:'选项无效，请重新选择',int_parsing:'请输入整数'}
        return field + '：' + (reasons[issue.type] || issue.msg || '输入格式不正确')
      })
      throw new Error(details.join('；'))
    }
    if (rewriting && r.status >= 500) throw new Error(`改写服务网关返回错误 (${r.status})，当前输入已保留，请稍后重试。`)
    throw new Error(`请求失败 (${r.status})，请检查输入`)
  }
  const mutation=(options.method || 'GET').toUpperCase() !== 'GET'
  const previousHistory=peekHistory('/history')
  if (mutation) {
    listCache.clear(); invalidateHistory(path)
    if (path.startsWith('/career/job-descriptions') || path.startsWith('/knowledge/')) knowledgeCache.clear()
  }
  try {
    let value=await r.json()
    if(mutation && ownerToken===state.token && path.startsWith('/career/sessions') && value.id && Array.isArray(value.facts) && !path.endsWith('/approve-rewrite')) {
      prime(privateHistoryCache,'/career/sessions/'+value.id,value)
      if(previousHistory) prime(privateHistoryCache,'/history',[
        {id:value.id,kind:'career',created_at:value.created_at,status:value.status,context:value.context},
        ...previousHistory.filter((row:any)=>row.id!==value.id),
      ])
    }
    if(!mutation && historyPath(path) && Array.isArray(value)) value=value.filter(row=>!isHistoryDeleted(row.id))
    if(mutation && ownerToken===state.token && path.startsWith('/mock/sessions')) {
      const id=value.id || path.match(/^\/mock\/sessions\/([^/?]+)/)?.[1]
      if(value.id && Array.isArray(value.answers)) {
        prime(privateHistoryCache,'/mock/sessions/'+id,value)
        prime(privateHistoryCache,'/mock/sessions/'+id+'/report',value)
      }
      if(previousHistory && id) {
        const rows=previousHistory.filter((row:any)=>row.id!==id)
        if(value.id && value.answers?.length) rows.unshift({id,kind:'mock',created_at:value.created_at,status:value.status,context:value.context})
        prime(privateHistoryCache,'/history',rows)
      }
      if(id)void preloadHistory().catch(()=>{})
    }
    if(mutation && ownerToken===state.token && (path.startsWith('/ai/') || path.startsWith('/career/')) && state.user) {
      void preloadHistory().catch(()=>{})
    }
    return value
  }
  catch (error) {
    if (rewriting) throw new Error('改写结果读取失败，连接可能中断；当前输入已保留，请重试。')
    throw error
  }
}

export async function deleteHistoryRecord(item: {id:string;kind:string}) {
  const token=state.token, marker=token+'\n'+item.id
  const snapshots=new Map([...privateHistoryCache].filter(([key])=>key.startsWith(token+'\n')))
  deletedHistory.add(marker)
  for(const [key,entry] of snapshots) {
    const path=key.slice(key.indexOf('\n')+1)
    if(Array.isArray(entry.value)) prime(privateHistoryCache,path,entry.value.filter(row=>row.id!==item.id))
    else if(path.split(/[/?]/).includes(item.id)) privateHistoryCache.delete(key)
  }
  state.historyRevision++
  const base=item.kind==='career'?'/career/sessions/':item.kind==='mock'?'/mock/sessions/':'/ai/conversations/'
  try { await api(base+encodeURIComponent(item.id),{method:'DELETE'}) }
  catch(error) {
    if(token===state.token) {
      deletedHistory.delete(marker)
      for(const [key,entry] of snapshots) {
        const path=key.slice(key.indexOf('\n')+1), current=privateHistoryCache.get(key)
        if(!current) privateHistoryCache.set(key,entry)
        else if(Array.isArray(current.value) && Array.isArray(entry.value)) {
          const removed=entry.value.find(row=>row.id===item.id)
          if(removed && !current.value.some(row=>row.id===item.id)) prime(privateHistoryCache,path,[...current.value,removed])
        }
      }
      state.historyRevision++
    }
    throw error
  }
  if(token===state.token){
    for(const [key,entry] of snapshots) if(!privateHistoryCache.has(key) && Array.isArray(entry.value)) {
      prime(privateHistoryCache,key.slice(key.indexOf('\n')+1),entry.value.filter(row=>!isHistoryDeleted(row.id)))
    }
    state.historyRevision++
  }
}

function prime(cache: Map<string,CachedResult>, path: string, value: any) {
  cache.set(state.token+'\n'+path,{expires:Infinity,value,pending:Promise.resolve(value)})
}
export async function preloadDocuments() {
  const path='/knowledge/preload', key=state.token+'\n'+path
  const pending=cachedList(path,Infinity,knowledgeCache), entry=knowledgeCache.get(key)
  const result=await pending
  if(knowledgeCache.get(key)!==entry)return
  for(const document of result.items) prime(knowledgeCache,'/knowledge/documents/'+encodeURIComponent(document.id),document)
}
export async function preloadHistory() {
  const path='/history?prefetch=true', key=state.token+'\n'+path
  const pending=api(path), entry=privateHistoryCache.get(key)
  const rows=await pending
  if(privateHistoryCache.get(key)!==entry)return []
  prime(privateHistoryCache,'/history',rows.map(({snapshot,versions,...row}:any)=>row))
  for(const row of rows) if(row.kind==='mock' && row.snapshot) {
    prime(privateHistoryCache,'/mock/sessions/'+row.id,row.snapshot)
    prime(privateHistoryCache,'/mock/sessions/'+row.id+'/report',row.snapshot)
  }
  for(const row of rows) if(row.kind==='career' && row.snapshot) {
    const path='/career/sessions/'+row.id
    prime(privateHistoryCache,path,row.snapshot)
    prime(privateHistoryCache,path+'/versions',row.versions || [])
    if(row.snapshot.confirmed && row.snapshot.editing_blocks) prime(privateHistoryCache,path+'/editing-blocks',{blocks:row.snapshot.editing_blocks})
    for(const version of row.versions || []) if(version.editing_blocks) {
      prime(privateHistoryCache,path+'/editing-blocks?base_version_id='+version.id,{blocks:version.editing_blocks})
    }
  }
  return rows
}

async function cachedList(path: string, ttl: number, cache = listCache) {
  const key = state.token + '\n' + path
  const saved = cache.get(key)
  if (saved && saved.expires > Date.now()) return saved.pending
  if (cache === listCache && cache.size >= 32) cache.delete(cache.keys().next().value!)
  const pending = requestApi(path)
  const entry: CachedResult = { expires: Date.now() + ttl, pending }
  cache.set(key, entry)
  try {
    const value = await pending
    if (cache.get(key) === entry) entry.value = value
    return value
  } catch (error) {
    if (cache.get(key) === entry) cache.delete(key)
    throw error
  }
}

export function knowledgeDocuments(query: string) { return cachedList('/knowledge/documents?' + query, Infinity, knowledgeCache) }
export function knowledgeDocument(id: string) { return cachedList('/knowledge/documents/' + encodeURIComponent(id), Infinity, knowledgeCache) }
export function peekKnowledge(path: string) { const cached=knowledgeCache.get(state.token + '\n' + path);return cached && cached.expires>Date.now()?cached.value:undefined }
export function knowledgeCapabilities(){return cachedList('/knowledge/capabilities',Infinity,knowledgeCache)}
export function peekKnowledgeDocuments(query:string):any[]|undefined{
  const first=peekKnowledge('/knowledge/documents?'+query)
  if(!first)return undefined
  const rows=[...first.items]
  if(!rows.length && first.total)return undefined
  while(rows.length<first.total){
    const page=peekKnowledge('/knowledge/documents?'+query+'&offset='+rows.length)
    if(!page?.items.length)return undefined
    rows.push(...page.items)
  }
  return rows
}
export function refreshKnowledge() { knowledgeCache.clear() }
function knowledgeChanged(){
  refreshKnowledge();state.knowledgeRevision++
  localStorage.setItem('atlas-knowledge-revision',crypto.randomUUID())
}
export async function editKnowledgeDocument(id:string, data:{title:string;excerpt:string;body:string;expected_sha256:string}){
  try{const result=await api('/knowledge/documents/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify(data)});knowledgeChanged();return result}
  catch(error){refreshKnowledge();throw error}
}
export async function deleteKnowledgeDocument(id:string, expected:string){
  try{await api('/knowledge/documents/'+encodeURIComponent(id)+'?expected_sha256='+encodeURIComponent(expected),{method:'DELETE'});knowledgeChanged()}
  catch(error){refreshKnowledge();throw error}
}
export async function historyRecords() { return decorateHistory((await api('/history')).filter((row:any)=>!isHistoryDeleted(row.id))) }
export function peekHistoryRecords() {
  const rows = peekHistory('/history')
  return rows ? decorateHistory(rows.filter((row:any)=>!isHistoryDeleted(row.id))) : undefined
}
function decorateHistory(rows: any[]) {
  const counters = new Map<string, number>(), names = new Map<string, string>()
  const dateFormat = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' })
  const resumes = rows.filter((r: any) => r.kind === 'career').sort((a: any, b: any) => Date.parse(a.created_at) - Date.parse(b.created_at) || a.id.localeCompare(b.id))
  for (const row of resumes) {
    const date = new Date(row.created_at)
    if (!Number.isFinite(date.getTime())) continue
    const day = dateFormat.format(date).replace(/\D/g, ''), index = counters.get(day) || 0
    names.set(row.id, day + (index ? 'n' + index : ''))
    counters.set(day, index + 1)
  }
  return rows.map((row: any) => names.has(row.id) ? { ...row, display_name: names.get(row.id) } : row)
}

export function post(path: string, body: any) { return api(path, { method: 'POST', body: JSON.stringify(body) }) }
let restoringProfile: Promise<void> | null = null
export async function restoreSession() {
  if (state.user || !state.token) return
  if (!restoringProfile) restoringProfile = (async () => {
    const generation=sessionGeneration
    try {
      const user = await api('/auth/me')
      if (state.token && sessionGeneration===generation) {
        state.user = user
        Object.assign(state.context, user.preferences)
      }
    } catch (e: any) { if(sessionGeneration===generation)state.notice = e.message }
  })().finally(() => { restoringProfile = null })
  await restoringProfile
}
export async function initialize() {
  try {
    if (state.token) void historyRecords().catch(() => {})
    const [health, roles, industries] = await Promise.all([api('/health'), api('/catalog/roles'), api('/catalog/industries'), restoreSession()])
    Object.assign(state, { health, roles, industries })
  } catch (e: any) { state.notice = e.message }
}

export async function download(path: string, name: string) {
  const r = await authorizedFetch(path)
  if (!r.ok) throw new Error('文件不可用或权限已过期')
  const url = URL.createObjectURL(await r.blob())
  const link = document.createElement('a'); link.href = url; link.download = name; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
