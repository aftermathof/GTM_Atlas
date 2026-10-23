<script setup lang="ts">
import { gtmGlossary } from '../content/gtm-glossary'
</script>
<template>
  <section class="gtm-glossary" aria-labelledby="glossary-title">
    <p class="eyebrow">THE GTM GLOSSARY</p>
    <h2 id="glossary-title">GTM 专有名词库</h2>
    <p class="glossary-intro">先读懂术语，再理解业务。首批收录 {{gtmGlossary.length}} 个常用名词，后续持续补充；具体含义以行业、岗位和业务语境为准。</p>
    <table>
      <colgroup><col class="term-column"><col></colgroup>
      <thead><tr><th scope="col">名词</th><th scope="col">解释</th></tr></thead>
      <tbody><tr v-for="item in gtmGlossary" :key="item.term">
        <th scope="row">{{item.term}}</th>
        <td><p class="term-full-name">{{item.fullName}}</p><p>{{item.explanation}}</p><p class="term-example">{{item.example}}</p></td>
      </tr></tbody>
    </table>
  </section>
</template>
<style scoped>
.gtm-glossary{padding-top:12px}
.gtm-glossary h2{font-size:32px;font-weight:300;margin:16px 0}
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
@media(max-width:760px){.term-column{width:76px}th,td{padding:20px 10px}tbody th{font-size:18px}.gtm-glossary h2{font-size:27px}td{font-size:14px}}
</style>
