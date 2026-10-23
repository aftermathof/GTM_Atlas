import { reactive } from 'vue'

export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export const state = reactive({
  user: null as any,
  token: sessionStorage.getItem('atlas-token') || '',
  context: { role: '', role_raw: '', industry: '', language: 'zh-CN', region: '', seniority: 'intern', business_model: 'unknown' },
  roles: [] as any[], industries: [] as any[], health: null as any,
  assistant: false, scope: 'global', documentId: '', careerId: '', notice: ''
})

export function saveSession(value: any) {
  state.token = value.token
  sessionStorage.setItem('atlas-token', value.token)
  if (value.refresh_token) sessionStorage.setItem('atlas-refresh', value.refresh_token)
  else sessionStorage.removeItem('atlas-refresh')
}

export function clearSession() {
  state.user = null; state.token = ''
  sessionStorage.removeItem('atlas-token'); sessionStorage.removeItem('atlas-refresh')
}

let refreshing: Promise<void> | null = null
async function refreshSession() {
  if (!refreshing) refreshing = (async () => {
    const token = sessionStorage.getItem('atlas-refresh')
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
  if (r.status === 401 && sessionStorage.getItem('atlas-refresh') && !path.startsWith('/api/v1/auth/login') && !path.startsWith('/api/v1/auth/register')) {
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
  return r.json()
}

export function post(path: string, body: any) { return api(path, { method: 'POST', body: JSON.stringify(body) }) }
export async function initialize() {
  try {
    const [health, roles, industries] = await Promise.all([api('/health'), api('/catalog/roles'), api('/catalog/industries')])
    Object.assign(state, { health, roles, industries })
    if (state.token) {
      state.user = await api('/auth/me')
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
