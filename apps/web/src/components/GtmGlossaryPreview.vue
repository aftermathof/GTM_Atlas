<script setup lang="ts">
import GtmGlossary from './GtmGlossary.vue'
</script>
<template>
  <section class="glossary-preview" aria-labelledby="glossary-preview-title">
    <div class="preview-heading"><div><p class="eyebrow">THE GTM GLOSSARY</p><h2 id="glossary-preview-title">GTM 专有名词库</h2><p>从常用术语到业务场景，在解释与例子中理解 GTM。</p></div><a href="/glossary" target="_blank" rel="noopener noreferrer" class="text-link">打开完整页面 ↗</a></div>
    <div class="glossary-frame" tabindex="0" role="region" aria-label="GTM 专有名词库预览"><GtmGlossary/></div>
  </section>
</template>
<style scoped>
.preview-heading{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin:12px 0 28px}
.preview-heading h2{font-size:32px;font-weight:300;margin:16px 0}
.preview-heading p:not(.eyebrow){color:var(--muted);line-height:1.9;max-width:720px}
.preview-heading a{white-space:nowrap;flex-shrink:0}
.glossary-frame{height:1000px;overflow-y:auto;border:1px solid var(--line);padding:32px;background:var(--bg);overscroll-behavior:contain}
@media(max-width:760px){.preview-heading{display:block}.preview-heading h2{font-size:27px}.preview-heading a{display:inline-block;margin-top:16px}.glossary-frame{height:800px;padding:16px}}
</style>
