import { watch } from 'vue'
import type { Router } from 'vue-router'
import { state, restoreSession } from '../../state'

export function installAuthGuard(router: Router) {
  router.beforeEach(async to => {
    if (to.path === '/auth/confirmed') return true
    const recovery = new URLSearchParams(to.hash?.slice(1) || '')
    if (recovery.get('type') === 'recovery') return to.path === '/login' ? true : { path: '/login', hash: to.hash, query: {} }
    if (recovery.get('type') === 'signup' || (recovery.has('error') && !to.query?.reset)) return { path: '/auth/confirmed', hash: to.hash, query: {} }
    if (to.path === '/login') return true
    if (!state.user) await restoreSession()
    return state.user ? true : { path: '/login', query: { next: to.fullPath } }
  })
  watch(() => state.user, user => {
    if (!user && !['/login', '/auth/confirmed'].includes(router.currentRoute.value.path)) {
      void router.replace({ path: '/login', query: { next: router.currentRoute.value.fullPath } })
    }
  })
}
