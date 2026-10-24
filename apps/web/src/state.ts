import { reactive } from 'vue'

export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const listCache = new Map<string, { expires: number; pending: Promise<any> }>()

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
  listCache.clear()
  state.token = value.token
  localStorage.setItem('atlas-token', value.token)
  if (value.refresh_token) localStorage.setItem('atlas-refresh', value.refresh_token)
  else localStorage.removeItem('atlas-refresh')
}

export function clearSession() {
  listCache.clear()
  state.user = null; state.token = ''
  localStorage.removeItem('atlas-token'); localStorage.removeItem('atlas-refresh')
  sessionStorage.removeItem('atlas-token'); sessionStorage.removeItem('atlas-refresh')
}

window.addEventListener('storage', event => {
  if (event.storageArea !== localStorage || (event.key !== 'atlas-token' && event.key !== null)) return
  listCache.clear()
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
  const r = await authorizedFetch('/api/v1' + path, options)
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    if (r.status === 401 && !path.startsWith('/auth/login')) clearSession()
    throw new Error(typeof body.detail === 'string' ? body.detail : `请求失败 (${r.status})，请检查输入`)
  }
  if ((options.method || 'GET').toUpperCase() !== 'GET') listCache.clear()
  return r.json()
}

async function cachedList(path: string, ttl: number) {
  const key = state.token + '\n' + path
  const saved = listCache.get(key)
  if (saved && saved.expires > Date.now()) return saved.pending
  if (listCache.size >= 32) listCache.delete(listCache.keys().next().value!)
  const pending = api(path)
  listCache.set(key, { expires: Date.now() + ttl, pending })
  try { return await pending }
  catch (error) {
    if (listCache.get(key)?.pending === pending) listCache.delete(key)
    throw error
  }
}

export function knowledgeDocuments(query: string) { return cachedList('/knowledge/documents?' + query, 60_000) }
export function historyRecords() { return cachedList('/history', 30_000) }

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
