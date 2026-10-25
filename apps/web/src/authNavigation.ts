import { watch } from 'vue'
import type { Router } from 'vue-router'
import { state, restoreSession } from './state'

export function installAuthGuard(router: Router) {
  router.beforeEach(async to => {
    if (to.path === '/login') return true
    const recovery = new URLSearchParams(to.hash?.slice(1) || '')
    if (recovery.get('type') === 'recovery') return { path: '/login', hash: to.hash, query: {} }
    if (!state.user) await restoreSession()
    return state.user ? true : { path: '/login', query: { next: to.fullPath } }
  })
  watch(() => state.user, user => {
    if (!user && router.currentRoute.value.path !== '/login') {
      void router.replace({ path: '/login', query: { next: router.currentRoute.value.fullPath } })
    }
  })
}
