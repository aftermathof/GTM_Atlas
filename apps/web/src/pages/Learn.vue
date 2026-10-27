<script setup lang="ts">
import LoadingState from '../components/LoadingState.vue'
import { computed, defineAsyncComponent, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, Pencil, Trash2 } from 'lucide-vue-next'
import { api, knowledgeDocument, deleteKnowledgeDocument, peekKnowledge, state } from '../state'
import ArticleBody from '../components/ArticleBody.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ResourceGallery from '../components/ResourceGallery.vue'
const KnowledgeEditor=defineAsyncComponent(()=>import('../components/KnowledgeEditor.vue'))
import ConfirmDelete from '../components/ConfirmDelete.vue'
const route = useRoute(), router=useRouter(), doc = ref<any>(null), error = ref(''), busy = ref(false)
const canManage=ref(false), editing=ref(false), pendingDelete=ref(false), deleting=ref(false)
const editable=computed(()=>canManage.value && doc.value?.meta.kind==='learning' && doc.value?.meta.source_type==='original_research_note' && !doc.value?.private)
const backLink = computed(() => doc.value?.meta.kind === 'jd' ? {path:'/interviews',query:{kind:'jd',page:route.query.page}} : {path:'/learn',query:{kind:'learning',collection:doc.value?.meta.author_collection_id || undefined,postPage:route.query.postPage,page:route.query.page,q:route.query.q}})
let generation=0
async function load() {
  const current=++generation, slug=String(route.params.slug || '')
  error.value=''; doc.value=null; busy.value=false;editing.value=false;pendingDelete.value=false
  if (!slug || slug==='ask') return
  const cached=peekKnowledge('/knowledge/documents/'+encodeURIComponent(slug))
  if (cached) {doc.value=cached;state.documentId=slug;state.scope='article';editing.value=route.query.edit==='1';return}
  busy.value=true
  try {
    const row=await knowledgeDocument(slug)
    if(current===generation){doc.value=row;state.documentId=slug;state.scope='article';editing.value=route.query.edit==='1'}
  } catch(e:any){if(current===generation)error.value=e.message}
  finally{if(current===generation)busy.value=false}
}
async function permissions(){
  canManage.value=false
  if(!state.user)return
  try{canManage.value=!!(await api('/knowledge/capabilities')).can_manage_learning}catch{}
}
function beginEdit(){editing.value=true;void router.replace({query:{...route.query,edit:'1'}})}
function cancelEdit(){editing.value=false;void router.replace({query:{...route.query,edit:undefined}})}
function saved(row:any){doc.value=row;cancelEdit()}
async function remove(){
  if(deleting.value || !doc.value)return
  pendingDelete.value=false;deleting.value=true;error.value=''
  try{await deleteKnowledgeDocument(doc.value.id,doc.value.sha256);await router.replace(backLink.value)}
  catch(e:any){error.value=e.message}
  finally{deleting.value=false}
}
watch(()=>state.user?.id,permissions,{immediate:true})
watch(()=>route.params.slug,load);onMounted(load)
</script>
<template>
  <div class="container">
    <ConfirmDelete v-if="pendingDelete && doc" title="删除这篇在职经验？" :name="doc.title" description="资料将从共享列表与 AI 检索中撤下，原始 Markdown 保留备份。" @cancel="pendingDelete=false" @confirm="remove"/>
    <template v-if="!route.params.slug || route.params.slug === 'ask'">
      <section class="page-hero"><div><p class="eyebrow">01 / THE KNOWLEDGE ATLAS</p><h1 class="h-xl">为业务理解，<br>建立一张<span class="blue">地图。</span></h1><p class="lead">从概念、框架到案例，沿着知识的脉络深入。<br>不只收藏答案，也理解答案从何而来。</p></div><div class="hero-aside"><span class="large-number">01</span><p>知识是起点。<br>把它用在具体问题里。</p><RouterLink :to="route.params.slug === 'ask' ? '/learn' : '/learn/ask'" class="text-link">{{ route.params.slug === 'ask' ? '返回知识目录' : '向知识库提问' }} <ArrowUpRight :size="17" /></RouterLink></div></section>
      <ChatPanel v-if="route.params.slug === 'ask'" scope="global" :conversation-id="String(route.query.conversation || '')" class="wide-chat" />
      <ResourceGallery v-else />
    </template>
    <LoadingState v-else-if="busy && !doc" label="正在加载资料…"/><template v-else-if="doc"><RouterLink :to="backLink" class="back-link"><ArrowLeft :size="15" /> {{doc.meta.kind==='jd'?'返回岗位 JD':doc.meta.author_collection_id?'返回博主合集':'返回知识地图'}}</RouterLink><section class="article-header"><p class="eyebrow">THE KNOWLEDGE ATLAS / READING</p><h1 class="h-xl">{{ doc.title }}</h1><p class="meta">{{ doc.meta.source_author }} · {{ doc.meta.collected_at }} · {{ doc.meta.quality_status === "unverified" ? "未独立核实" : doc.meta.quality_status === "user_provided" ? "用户提供" : "已整理" }} · {{ doc.private ? "我的私有 JD" : doc.kind === "jd" ? "岗位 JD" : doc.meta.resource_group === "overview" ? "GTM 概览" : doc.meta.resource_group === "glossary" ? "GTM 专有名词库" : doc.meta.source_type === "original_research_note" ? "原创研究整理" : "在职经验" }}</p></section><div v-if="editable && !editing" class="knowledge-actions"><button class="text-link" :disabled="deleting" @click="beginEdit"><Pencil :size="15"/>修改内容</button><button class="text-link" :disabled="deleting" @click="pendingDelete=true"><Trash2 :size="15"/>{{deleting?'正在删除…':'删除'}}</button></div><p v-if="doc.meta.content_notice" class="notice">{{ doc.meta.content_notice }}</p><a v-if="doc.meta.source_url" :href="doc.meta.source_url" target="_blank" rel="noopener noreferrer" class="text-link source-link">{{ doc.meta.source_type === "site_reference" ? "查看原始资料" : "查看原帖出处" }} ↗</a><RouterLink v-if="doc.private" :to="'/career?jd_id='+doc.id" class="primary">以此 JD 定制简历 ↗</RouterLink><KnowledgeEditor v-if="editing && editable" :key="doc.id" :document="doc" @saved="saved" @cancel="cancelEdit"/><ArticleBody v-else :source="doc.body" :heading="String(route.query.heading || '')" @ask="state.assistant=true"/><div v-if="!editing" class="article-qa"><p class="eyebrow">ASK ABOUT THIS ARTICLE</p><h2>带着问题，再读一遍。</h2><ChatPanel scope="article" :document-id="doc.id" /></div></template>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.knowledge-actions{display:flex;gap:22px;justify-content:flex-end;margin:20px 0}.knowledge-actions button{display:inline-flex;align-items:center;gap:6px}
</style>
