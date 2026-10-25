import { reactive } from 'vue'

export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')
type CachedResult = { expires: number; pending: Promise<any>; value?: any }
const listCache = new Map<string, CachedResult>()
const knowledgeCache = new Map<string, CachedResult>()

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
  context: { role: '', role_raw: '', industry: '', language: 'zh-CN', region: '', seniority: 'intern', business_model: 'unknown' },
  roles: [] as any[], industries: [] as any[], health: null as any,
  assistant: false, assistantBusy: false, assistantRequest: null as { question: string } | null,
  scope: 'global', documentId: '', careerId: '', notice: ''
})

export function saveSession(value: any) {
  listCache.clear(); knowledgeCache.clear()
  state.token = value.token
  localStorage.setItem('atlas-token', value.token)
  if (value.refresh_token) localStorage.setItem('atlas-refresh', value.refresh_token)
  else localStorage.removeItem('atlas-refresh')
}

export function clearSession() {
  listCache.clear(); knowledgeCache.clear()
  state.user = null; state.token = ''
  localStorage.removeItem('atlas-token'); localStorage.removeItem('atlas-refresh')
  sessionStorage.removeItem('atlas-token'); sessionStorage.removeItem('atlas-refresh')
}

window.addEventListener('storage', event => {
  if (event.storageArea !== localStorage || (event.key !== 'atlas-token' && event.key !== null)) return
  listCache.clear(); knowledgeCache.clear()
  state.token = event.key === null ? '' : event.newValue || ''
  if (!state.token) state.user = null
})

let refreshing: Promise<void> | null = null
async function refreshSession() {
  if (!refreshing) refreshing = (async () => {
    const token = localStorage.getItem('atlas-refresh')
    if (!token) throw new Error('请重新登录')
    const r = await fetch(API_ORIGIN + '/api/v1/auth/refresh', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({refresh_token:token}) })
    if (!r.ok) {
      if (r.status === 400 || r.status === 401) clearSession()
      throw new Error(r.status >= 500 ? '登录服务暂时不可用，请稍后重试' : '登录已过期，请重新登录')
    }
    saveSession(await r.json())
  })().finally(() => { refreshing = null })
  return refreshing
}

export async function authorizedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers)
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  let r = await fetch(API_ORIGIN + path, { ...options, headers })
  if (r.status === 401 && localStorage.getItem('atlas-refresh') && !path.startsWith('/api/v1/auth/login') && !path.startsWith('/api/v1/auth/register')) {
    await refreshSession()
    headers.set('Authorization', `Bearer ${state.token}`)
    r = await fetch(API_ORIGIN + path, {...options, headers})
  }
  return r
}

export async function api(path: string, options: RequestInit = {}): Promise<any> {
  const rewriting = path.endsWith('/block-dialogue')
  let r: Response
  try { r = await authorizedFetch('/api/v1' + path, options) }
  catch (error: any) {
    if (rewriting && error?.name === 'TypeError') throw new Error('改写请求的网络连接中断，未收到生成结果；当前输入已保留，请重试。')
    throw error
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    if (r.status === 401 && !path.startsWith('/auth/login')) clearSession()
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
  if ((options.method || 'GET').toUpperCase() !== 'GET') {
    listCache.clear()
    if (path.startsWith('/career/job-descriptions') || path.startsWith('/knowledge/')) knowledgeCache.clear()
  }
  try { return await r.json() }
  catch (error) {
    if (rewriting) throw new Error('改写结果读取失败，连接可能中断；当前输入已保留，请重试。')
    throw error
  }
}

async function cachedList(path: string, ttl: number, cache = listCache) {
  const key = state.token + '\n' + path
  const saved = cache.get(key)
  if (saved && saved.expires > Date.now()) return saved.pending
  if (cache.size >= (cache === knowledgeCache ? 128 : 32)) cache.delete(cache.keys().next().value!)
  const pending = api(path)
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
export function peekKnowledge(path: string) { return knowledgeCache.get(state.token + '\n' + path)?.value }
export function refreshKnowledge() { knowledgeCache.clear() }
export async function historyRecords() {
  const rows = await cachedList('/history', 30_000)
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
export async function initialize() {
  try {
    if (state.token) void historyRecords().catch(() => {})
    const profile = state.token ? api('/auth/me').catch((e: any) => { state.notice = e.message; return null }) : Promise.resolve(null)
    const [health, roles, industries, user] = await Promise.all([api('/health'), api('/catalog/roles'), api('/catalog/industries'), profile])
    Object.assign(state, { health, roles, industries })
    if (user) {
      state.user = user
      Object.assign(state.context, state.user.preferences)
    }
  } catch (e: any) { state.notice = e.message }
}

export async function download(path: string, name: string) {
  const r = await authorizedFetch(path)
  if (!r.ok) throw new Error('文件不可用或权限已过期')
  const url = URL.createObjectURL(await r.blob())
  const link = document.createElement('a'); link.href = url; link.download = name; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
