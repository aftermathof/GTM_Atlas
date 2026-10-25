<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Search, ArrowUpRight, X, Menu, Sparkles, Maximize2, Minimize2 } from 'lucide-vue-next'
import { state, initialize } from './state'
import ChatPanel from './components/ChatPanel.vue'
import LoadingState from './components/LoadingState.vue'
const route = useRoute(), menu = ref(false), assistantMounted = ref(false), assistantExpanded = ref(false), drawer = ref<HTMLElement>()
const assistantChat = ref<InstanceType<typeof ChatPanel>>()
onMounted(initialize)
watch(() => state.user, user => { if (!user) { menu.value = false; state.assistant = false; state.assistantRequest = null } })
watch(() => route.path, () => { menu.value = false; state.documentId = ''; state.careerId = ''; state.scope = 'global' })
watch(() => state.assistant, async value => { if (value) { assistantMounted.value = true; await nextTick(); drawer.value?.focus() } else assistantExpanded.value = false })
watch(() => state.assistantRequest, async request => {
  if (!request) return
  state.assistant = true; assistantMounted.value = true
  await nextTick()
  try { await assistantChat.value?.submitQuestion(request.question) }
  finally { if (state.assistantRequest === request) state.assistantRequest = null }
})
function trap(e: KeyboardEvent) {
  if (e.key === 'Escape') state.assistant = false
  if (e.key !== 'Tab') return
  const nodes = drawer.value?.querySelectorAll<HTMLElement>('button,select,textarea,a,input')
  if (!nodes?.length) return
  const first = nodes[0], last = nodes[nodes.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}
</script>
<template>
  <a class="skip-link" href="#main">跳转到主要内容</a>
  <header v-if="state.user" class="site-header"><div class="container header-inner">
    <RouterLink to="/" class="brand"><svg class="brand-mark" viewBox="0 0 36 36" aria-hidden="true" focusable="false"><path fill="currentColor" d="M0 0h36v36H0z" /><g fill="none" stroke="#fff" stroke-linejoin="round"><path d="M7 26V12l7-3 8 3 7-3v15l-7 3-8-3-7 2Z" stroke-opacity=".55" /><path d="M14 9v15m8-12v15" stroke-opacity=".35" /><path d="m10 23 15-13m-7 0h7v7" stroke-width="2" /></g></svg><span class="brand-wordmark">GTM Atlas</span></RouterLink>
    <nav class="desktop-nav" aria-label="主导航"><RouterLink to="/learn" :class="{active: route.path.startsWith('/learn')}">知识学习</RouterLink><RouterLink to="/interviews" :class="{active: route.path.startsWith('/interviews')}">面经与 Mock</RouterLink><RouterLink to="/career" :class="{active: route.path.startsWith('/career')}">简历工作台</RouterLink></nav>
    <div class="header-actions"><RouterLink to="/search" class="icon-button" aria-label="全站搜索"><Search :size="19" /></RouterLink><button class="assistant-toggle" @click="state.assistant = true"><Sparkles :size="16" /><span>AI Assistant</span></button><RouterLink :to="state.user ? '/history' : '/login'" class="account-link">{{ state.user ? '我的空间' : '登录' }}<ArrowUpRight :size="14" /></RouterLink><RouterLink to="/settings" class="header-settings">设置</RouterLink><button class="mobile-menu icon-button" @click="menu = !menu" aria-label="菜单" :aria-expanded="menu"><Menu :size="21" /></button></div>
  </div><nav v-if="menu" class="mobile-nav"><RouterLink to="/learn">知识学习</RouterLink><RouterLink to="/interviews">面经与 Mock</RouterLink><RouterLink to="/career">简历工作台</RouterLink><RouterLink to="/history">我的历史</RouterLink></nav></header>
  <main id="main"><div v-if="state.notice" class="container error" role="alert">{{ state.notice }} · 请检查 API 服务是否启动。</div><RouterView v-if="route.path==='/login' || state.user"/><LoadingState v-else label="正在验证登录状态…"/></main>
  <footer v-if="state.user" class="site-footer container"><RouterLink to="/" class="footer-brand">GTM Atlas <span>理解市场，走向市场。</span></RouterLink></footer>
  <button v-if="state.user && !state.assistant" class="floating-assistant" @click="state.assistant = true" aria-label="打开全局 AI Assistant"><Sparkles :size="19" /><span>问问 Atlas</span><ArrowUpRight :size="15" /></button>
  <div v-if="state.user && assistantMounted" v-show="state.assistant" class="drawer-backdrop" @click.self="state.assistant = false"><aside ref="drawer" class="assistant-drawer" :class="{expanded:assistantExpanded}" role="dialog" aria-modal="true" aria-label="全局 AI Assistant" tabindex="-1" @keydown="trap"><div class="drawer-header"><span class="eyebrow">ATLAS ASSISTANT</span><div class="drawer-actions"><button class="icon-button" @click="assistantExpanded = !assistantExpanded" :aria-pressed="assistantExpanded" :aria-label="assistantExpanded ? '收起为侧边助手' : '放大全屏'" :title="assistantExpanded ? '收起为侧边助手' : '放大全屏'"><Minimize2 v-if="assistantExpanded" :size="20"/><Maximize2 v-else :size="20"/></button><button class="icon-button" @click="state.assistant = false" aria-label="关闭助手"><X :size="22" /></button></div></div><ChatPanel ref="assistantChat" scope="global" docked /></aside></div>
</template>
<style scoped>
.brand{display:inline-flex;align-items:center;gap:10px;letter-spacing:normal}
.brand-mark{width:30px;height:30px;flex-shrink:0;color:var(--blue)}
.brand .brand-wordmark{font-weight:600}
.header-settings{font-size:13px;white-space:nowrap}
.header-settings:hover,.header-settings.router-link-active{color:var(--blue)}
.assistant-drawer{display:flex;flex-direction:column;overflow:hidden}
.assistant-drawer.expanded{width:100%;max-width:none;padding-inline:max(24px,calc((100vw - 1120px)/2));border-left:0}
.expanded :deep(.chat-panel){width:100%;margin-inline:auto}
@media(max-width:760px){.assistant-drawer.expanded{padding-inline:20px}}
.drawer-actions{display:flex;align-items:center;gap:16px}
.drawer-header{flex-shrink:0}
@media(max-width:760px){.brand{gap:8px}.brand-mark{width:26px;height:26px}.header-settings{font-size:12px}}
</style>
