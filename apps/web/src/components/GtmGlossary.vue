<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search } from 'lucide-vue-next'
import { gtmGlossary } from '../content/gtm-glossary'
const query = ref('')
const filteredGlossary = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return gtmGlossary.filter(item => [item.term, item.fullName, item.explanation, item.example].some(value => value.toLowerCase().includes(keyword)))
})
</script>
<template>
  <section class="gtm-glossary" aria-labelledby="glossary-title">
    <p class="eyebrow">THE GTM GLOSSARY</p>
    <div class="glossary-heading"><div><h2 id="glossary-title">GTM 专有名词库</h2><p class="glossary-intro">先读懂术语，再理解业务。首批收录 {{gtmGlossary.length}} 个常用名词，后续持续补充；具体含义以行业、岗位和业务语境为准。</p></div><label class="glossary-search"><Search :size="18" aria-hidden="true"/><span>搜索</span><input v-model="query" type="search" aria-label="搜索专有名词" autocomplete="off"></label></div>
    <p v-if="query.trim()" class="glossary-results" role="status">找到 {{filteredGlossary.length}} 个名词</p>
    <table v-if="filteredGlossary.length">
      <colgroup><col class="term-column"><col></colgroup>
      <thead><tr><th scope="col">名词</th><th scope="col">解释</th></tr></thead>
      <tbody><tr v-for="item in filteredGlossary" :key="item.term">
        <th scope="row">{{item.term}}</th>
        <td><p class="term-full-name">{{item.fullName}}</p><p>{{item.explanation}}</p><p class="term-example">{{item.example}}</p></td>
      </tr></tbody>
    </table>
    <p v-else class="glossary-empty">未找到相关名词，请更换搜索词。</p>
  </section>
</template>
<style scoped>
.gtm-glossary{padding-top:12px}
.gtm-glossary h2{font-size:32px;font-weight:300;margin:16px 0}
.glossary-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:32px}
.glossary-heading>div{min-width:0;flex:1}
.glossary-search{display:flex;flex-direction:row;align-items:center;gap:10px;flex:0 1 300px;min-width:220px;margin:16px 0 32px;padding:0 12px;border:1px solid var(--line);color:var(--muted)}
.glossary-search svg{flex-shrink:0}
.glossary-search:focus-within{border-color:var(--blue)}
.glossary-search span{font-size:13px;white-space:nowrap}
.glossary-search input{min-width:0;width:100%;padding:12px 0;border:0;background:transparent;font:inherit;color:var(--ink);outline:none;box-shadow:none}
.glossary-results{font-size:13px;color:var(--muted);margin:0 0 16px}
.glossary-empty{padding:32px 0;border-top:1px solid var(--line);color:var(--muted)}
.glossary-intro{color:var(--muted);line-height:1.9;margin-bottom:32px;max-width:760px}
table{width:100%;border-collapse:collapse;table-layout:fixed;text-align:left}
.term-column{width:150px}
th,td{border-bottom:1px solid var(--line);padding:24px 20px;vertical-align:top;overflow-wrap:anywhere}
thead th{border-top:1px solid var(--ink);font-weight:500;font-size:14px}
tbody th{color:var(--blue);font-size:22px;font-weight:400}
td p{margin:0 0 10px;line-height:1.85}
td p:last-child{margin-bottom:0}
.term-full-name{font-weight:500}
.term-example{color:var(--muted);font-size:14px}
@media(max-width:760px){.glossary-heading{flex-direction:column;gap:0}.glossary-search{flex:none;min-width:0;width:100%;margin-top:0}.term-column{width:76px}th,td{padding:20px 10px}tbody th{font-size:18px}.gtm-glossary h2{font-size:27px}td{font-size:14px}}
</style>
