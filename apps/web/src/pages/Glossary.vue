<script setup lang="ts">
import GtmGlossary from '../components/GtmGlossary.vue'
</script>
<template>
  <div class="container glossary-page"><RouterLink to="/learn?kind=glossary" class="back-link">← 返回资料目录</RouterLink><GtmGlossary/></div>
</template>
<style scoped>
.glossary-page{padding-top:40px;padding-bottom:40px}
</style>
