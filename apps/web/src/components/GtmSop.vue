<script setup lang="ts">
import { ref } from 'vue'
const loaded = ref(false)
</script>
<template>
  <section class="gtm-sop" aria-labelledby="sop-title">
    <div class="sop-heading"><div><p class="eyebrow">GO TO MARKET / STANDARD OPERATING PROCEDURE</p><h2 id="sop-title">SOP</h2><p>先读操盘手册建立全局，再按七阶段流程查阅 15 份导图与表格资料。</p></div><a href="/gtm-sop/index.html" target="_blank" rel="noopener noreferrer" class="text-link">打开完整页面 ↗</a></div>
    <p v-if="!loaded" class="meta" role="status">正在加载 SOP…</p>
    <iframe src="/gtm-sop/index.html" title="SOP：七阶段流程与十五份资料目录" sandbox="allow-scripts allow-same-origin allow-downloads allow-popups allow-popups-to-escape-sandbox" @load="loaded=true"></iframe>
  </section>
</template>
<style scoped>
.sop-heading{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin:12px 0 28px}
.sop-heading h2{font-size:32px;font-weight:300;margin:16px 0}
.sop-heading p:not(.eyebrow){color:var(--muted);line-height:1.9;max-width:720px}
.sop-heading a{white-space:nowrap;flex-shrink:0}
iframe{display:block;width:100%;height:1000px;border:1px solid var(--line);background:var(--bg)}
@media(max-width:760px){.sop-heading{display:block}.sop-heading h2{font-size:27px}.sop-heading a{display:inline-block;margin-top:16px}iframe{height:800px}}
</style>
