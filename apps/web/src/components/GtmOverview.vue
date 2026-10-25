<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { peekOverview, warmOverview } from '../publicLearning'
const page = ref('index.html'), html = ref(peekOverview()), error = ref(''), frame = ref<HTMLIFrameElement>()
const source = computed(() => html.value?.replace('<head>', '<head><base href="' + window.location.origin + '/gtm-overview/' + page.value + '">'))
async function load() {
  error.value = ''
  try { await warmOverview(); html.value = peekOverview(page.value) }
  catch { error.value = '概览暂时无法加载，请重试。' }
}
function bindLinks() {
  const doc = frame.value?.contentDocument
  doc?.addEventListener('click', event => {
    const link = (event.target as Element).closest('a')
    if (!link) return
    const href = link.getAttribute('href') || ''
    if (href.startsWith('#')) {
      event.preventDefault(); doc.getElementById(href.slice(1))?.scrollIntoView(); return
    }
    const url = new URL(href, window.location.origin + '/gtm-overview/' + page.value)
    const next = url.pathname.split('/').pop() || 'index.html'
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/gtm-overview/') || !peekOverview(next)) return
    event.preventDefault(); page.value = next; html.value = peekOverview(next)
  })
}
onMounted(() => { if (!html.value) void load() })
</script>
<template>
  <section class="gtm-overview" aria-labelledby="overview-title">
    <div class="overview-heading"><div><p class="eyebrow">GO TO MARKET / LEARNING GUIDE</p><h2 id="overview-title">GTM 概览</h2><p>从基本认知、关键工作到经营痛点与落地实施，沿着四章内容建立完整认识。</p></div><a href="/gtm-overview/index.html" target="_blank" rel="noopener noreferrer" class="text-link">打开完整页面 ↗</a></div>
    <p v-if="error" class="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <iframe v-if="source" ref="frame" :srcdoc="source" title="GTM 概览：体系学习资料与四章正文" sandbox="allow-same-origin" @load="bindLinks"></iframe>
    <p v-else-if="!error" class="meta" role="status">正在加载概览…</p>
  </section>
</template>
<style scoped>
.overview-heading{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin:12px 0 28px}
.overview-heading h2{font-size:32px;font-weight:300;margin:16px 0}
.overview-heading p:not(.eyebrow){color:var(--muted);line-height:1.9;max-width:720px}
.overview-heading a{white-space:nowrap;flex-shrink:0}
iframe{display:block;width:100%;height:1000px;border:1px solid var(--line);background:var(--bg)}
@media(max-width:760px){.overview-heading{display:block}.overview-heading h2{font-size:27px}.overview-heading a{display:inline-block;margin-top:16px}iframe{height:800px}}
</style>
