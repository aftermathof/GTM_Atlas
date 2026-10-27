<script setup lang="ts">
import LoadingState from '../components/LoadingState.vue'
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowUpRight, ArrowLeft } from 'lucide-vue-next'
import { knowledgeDocument, peekKnowledge, state } from '../state'
import ArticleBody from '../components/ArticleBody.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ResourceGallery from '../components/ResourceGallery.vue'
const route = useRoute(), doc = ref<any>(null), error = ref(''), busy = ref(false)
const backLink = computed(() => doc.value?.meta.kind === 'jd' ? {path:'/interviews',query:{kind:'jd',page:route.query.page}} : {path:'/learn',query:{kind:'learning',collection:doc.value?.meta.author_collection_id || undefined,postPage:route.query.postPage,page:route.query.page}})
let generation=0
async function load() {
  const current=++generation, slug=String(route.params.slug || '')
  error.value=''; doc.value=null; busy.value=false
  if (!slug || slug==='ask') return
  const cached=peekKnowledge('/knowledge/documents/'+encodeURIComponent(slug))
  if (cached) {doc.value=cached;state.documentId=slug;state.scope='article';return}
  busy.value=true
  try {
    const row=await knowledgeDocument(slug)
    if(current===generation){doc.value=row;state.documentId=slug;state.scope='article'}
  } catch(e:any){if(current===generation)error.value=e.message}
  finally{if(current===generation)busy.value=false}
}
watch(()=>route.params.slug,load);onMounted(load)
</script>
<template>
  <div class="container">
    <template v-if="!route.params.slug || route.params.slug === 'ask'">
      <section class="page-hero"><div><p class="eyebrow">01 / THE KNOWLEDGE ATLAS</p><h1 class="h-xl">为业务理解，<br>建立一张<span class="blue">地图。</span></h1><p class="lead">从概念、框架到案例，沿着知识的脉络深入。<br>不只收藏答案，也理解答案从何而来。</p></div><div class="hero-aside"><span class="large-number">01</span><p>知识是起点。<br>把它用在具体问题里。</p><RouterLink :to="route.params.slug === 'ask' ? '/learn' : '/learn/ask'" class="text-link">{{ route.params.slug === 'ask' ? '返回知识目录' : '向知识库提问' }} <ArrowUpRight :size="17" /></RouterLink></div></section>
      <ChatPanel v-if="route.params.slug === 'ask'" scope="global" :conversation-id="String(route.query.conversation || '')" class="wide-chat" />
      <ResourceGallery v-else />
    </template>
    <LoadingState v-else-if="busy && !doc" label="正在加载资料…"/><template v-else-if="doc"><RouterLink :to="backLink" class="back-link"><ArrowLeft :size="15" /> {{doc.meta.kind==='jd'?'返回岗位 JD':doc.meta.author_collection_id?'返回博主合集':'返回知识地图'}}</RouterLink><section class="article-header"><p class="eyebrow">THE KNOWLEDGE ATLAS / READING</p><h1 class="h-xl">{{ doc.title }}</h1><p class="meta">{{ doc.meta.source_author }} · {{ doc.meta.collected_at }} · {{ doc.meta.quality_status === "unverified" ? "未独立核实" : doc.meta.quality_status === "user_provided" ? "用户提供" : "已整理" }} · {{ doc.private ? "我的私有 JD" : doc.kind === "jd" ? "岗位 JD" : doc.meta.resource_group === "overview" ? "GTM 概览" : doc.meta.resource_group === "glossary" ? "GTM 专有名词库" : doc.meta.source_type === "original_research_note" ? "原创研究整理" : "在职经验" }}</p></section><p v-if="doc.meta.content_notice" class="notice">{{ doc.meta.content_notice }}</p><a v-if="doc.meta.source_url" :href="doc.meta.source_url" target="_blank" rel="noopener noreferrer" class="text-link source-link">{{ doc.meta.source_type === "site_reference" ? "查看原始资料" : "查看原帖出处" }} ↗</a><RouterLink v-if="doc.private" :to="'/career?jd_id='+doc.id" class="primary">以此 JD 定制简历 ↗</RouterLink><ArticleBody :source="doc.body" :heading="String(route.query.heading || '')" @ask="state.assistant=true"/><div class="article-qa"><p class="eyebrow">ASK ABOUT THIS ARTICLE</p><h2>带着问题，再读一遍。</h2><ChatPanel scope="article" :document-id="doc.id" /></div></template>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
  </div>
</template>
