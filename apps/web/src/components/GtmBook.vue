<script setup lang="ts">
import { ref } from 'vue'
const loaded = ref(false)
</script>
<template>
  <section class="gtm-book" aria-labelledby="book-title">
    <div class="book-heading"><div><p class="eyebrow">GO TO MARKET / THE COMPLETE BOOK</p><h2 id="book-title">爆品操盘GTM</h2><p>朱秋虎著。从历史沿革、华为 IPMS 演进到战略盘与战术盘，完整阅读六章正文与 TR / GR 附录。</p></div><a href="/gtm-book/index.html" target="_blank" rel="noopener noreferrer" class="text-link">打开完整页面 ↗</a></div>
    <p v-if="!loaded" class="meta" role="status">正在加载全书…</p>
    <iframe src="/gtm-book/index.html" title="爆品操盘GTM：全书目录、六章正文与附录" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox" @load="loaded=true"></iframe>
  </section>
</template>
<style scoped>
.book-heading{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin:12px 0 28px}
.book-heading h2{font-size:32px;font-weight:300;margin:16px 0}
.book-heading p:not(.eyebrow){color:var(--muted);line-height:1.9;max-width:720px}
.book-heading a{white-space:nowrap;flex-shrink:0}
iframe{display:block;width:100%;height:1000px;border:1px solid var(--line);background:var(--bg)}
@media(max-width:760px){.book-heading{display:block}.book-heading h2{font-size:27px}.book-heading a{display:inline-block;margin-top:16px}iframe{height:800px}}
</style>
