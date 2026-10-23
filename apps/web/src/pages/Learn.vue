<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowUpRight, ArrowLeft } from 'lucide-vue-next'
import { api, state } from '../state'
import Markdown from '../components/Markdown.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ResourceGallery from '../components/ResourceGallery.vue'
const route = useRoute(), doc = ref<any>(null), error = ref(''), busy = ref(false)
async function load() {
  busy.value = true; error.value = ''; doc.value = null
  try {
    const slug = route.params.slug
    if (slug && slug !== 'ask') { doc.value = await api('/knowledge/documents/' + slug); state.documentId = String(slug); state.scope = 'article'; await nextTick(); if (route.query.heading) document.querySelectorAll('.prose h1,.prose h2,.prose h3').forEach(el => { if (el.textContent === route.query.heading) el.scrollIntoView() }) }
  } catch(e: any) { error.value = e.message } finally { busy.value = false }
}
function scrollHeading(line: string) { document.querySelectorAll('.prose h2').forEach(el => { if (el.textContent === line.slice(3)) el.scrollIntoView({behavior:'smooth'}) }) }
watch(() => [route.params.slug, route.query.heading], load); onMounted(load)
</script>
<template>
  <div class="container">
    <template v-if="!route.params.slug || route.params.slug === 'ask'">
      <section class="page-hero"><div><p class="eyebrow">01 / THE KNOWLEDGE ATLAS</p><h1 class="h-xl">为业务理解，<br>建立一张<span class="blue">地图。</span></h1><p class="lead">从概念、框架到案例，沿着知识的脉络深入。<br>不只收藏答案，也理解答案从何而来。</p></div><div class="hero-aside"><span class="large-number">01</span><p>知识是起点。<br>把它用在具体问题里。</p><RouterLink :to="route.params.slug === 'ask' ? '/learn' : '/learn/ask'" class="text-link">{{ route.params.slug === 'ask' ? '返回知识目录' : '向知识库提问' }} <ArrowUpRight :size="17" /></RouterLink></div></section>
      <ChatPanel v-if="route.params.slug === 'ask'" scope="global" :conversation-id="String(route.query.conversation || '')" class="wide-chat" />
      <ResourceGallery v-else />
    </template>
    <template v-else-if="doc"><RouterLink to="/learn" class="back-link"><ArrowLeft :size="15" /> 返回知识地图</RouterLink><section class="article-header"><p class="eyebrow">THE KNOWLEDGE ATLAS / READING</p><h1 class="h-xl">{{ doc.title }}</h1><p class="meta">{{ doc.meta.source_author }} · {{ doc.meta.collected_at }} · {{ doc.meta.quality_status === "unverified" ? "未独立核实" : doc.meta.quality_status === "user_provided" ? "用户提供" : "已整理" }} · {{ doc.private ? "我的私有 JD" : doc.meta.source_type === "original_research_note" ? "原创研究整理" : "在职经验" }}</p></section><p v-if="doc.meta.content_notice" class="notice">{{ doc.meta.content_notice }}</p><a v-if="doc.meta.source_url" :href="doc.meta.source_url" target="_blank" rel="noopener noreferrer" class="text-link source-link">查看原帖出处 ↗</a><RouterLink v-if="doc.private" :to="'/career?jd_id='+doc.id" class="primary">以此 JD 定制简历 ↗</RouterLink><div class="article-grid"><aside class="sidebar"><p class="eyebrow">ON THIS PAGE</p><a v-for="line in doc.body.split('\n').filter((s: string) => s.startsWith('## '))" :key="line" href="#" @click.prevent="scrollHeading(line)">{{ line.slice(3) }}</a><button class="text-link" @click="state.assistant = true">询问当前文章 ↗</button></aside><Markdown :source="doc.body" /></div><div class="article-qa"><p class="eyebrow">ASK ABOUT THIS ARTICLE</p><h2>带着问题，再读一遍。</h2><ChatPanel scope="article" :document-id="doc.id" /></div></template>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
  </div>
</template>
