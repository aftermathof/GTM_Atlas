<script setup lang="ts">
import LoadingState from './LoadingState.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, BookOpen, BriefcaseBusiness, MessageSquare, Search, Lock, BookA, Compass } from 'lucide-vue-next'
import { knowledgeDocuments, peekKnowledge, refreshKnowledge, state } from '../state'
import { warmDocument } from '../preload'
import ContextPicker from './ContextPicker.vue'
import GtmGlossaryPreview from './GtmGlossaryPreview.vue'
import GtmOverview from './GtmOverview.vue'
const props = defineProps<{fixedKind?: string}>()
const route=useRoute(), router=useRouter(), items=ref<any[]>([]), query=ref(''), busy=ref(false), error=ref('')
const kinds=[{id:'jd',name:'岗位 JD',en:'JOB DESCRIPTIONS',icon:BriefcaseBusiness,description:'读懂职责与能力要求，明确你的目标。'},{id:'interview',name:'面经',en:'INTERVIEW NOTES',icon:MessageSquare,description:'从真实问题与个人复盘，理解考查方向。'},{id:'learning',name:'在职经验',en:'WORK EXPERIENCE',icon:BookOpen,description:'从市场洞察到上市经营，理解实际工作中的方法与经验。'}]
const visibleKinds=computed(()=>kinds.filter(k=>k.id!=='interview'))
const selected=computed(()=>props.fixedKind || (['overview','jd','learning','glossary'].includes(String(route.query.kind))?String(route.query.kind):'overview'))
const filtered=computed(()=>items.value.filter(d=>!d.meta.demo))
const columns=computed(()=>kinds.filter(k=>k.id===selected.value))
const total=computed(()=>filtered.value.filter(d=>d.kind===selected.value).length)
let generation=0
async function load(){
  const own=++generation, queryString=new URLSearchParams({limit:'100',q:query.value,role:state.context.role,industry:state.context.industry}).toString()
  error.value=''
  const cached=peekKnowledge('/knowledge/documents?'+queryString)
  if(cached){items.value=cached.items;busy.value=false;return}
  busy.value=true
  try{const r=await knowledgeDocuments(queryString);if(own===generation)items.value=r.items}
  catch(e:any){if(own===generation)error.value=e.message}
  finally{if(own===generation)busy.value=false}
}
function refresh(){refreshKnowledge();void load()}

function choose(kind:string){router.replace({query:{...route.query,kind}})}
function count(kind:string){return filtered.value.filter(d=>d.kind===kind).length}
function cards(kind:string){return filtered.value.filter(d=>d.kind===kind)}
function url(d:any){return (d.kind==='interview'?'/interviews/':'/learn/')+d.id}
function warm(id:string){void warmDocument(id,true)}
function badge(d:any){return d.private?'我的上传':d.kind==='jd'?'岗位 JD':d.kind==='interview'?'面经':d.meta.source_type==='original_research_note'?'研究笔记':'在职经验'}
watch(()=>[state.context.role,state.context.industry,state.user?.id],load);onMounted(load)
</script>
<template><section class="resource-gallery">
  <div class="gallery-heading"><div><p class="eyebrow">YOUR GTM READING ROOM</p><h2>{{fixedKind?'把每一次面试，变成下一次的准备。':'岗位、经验与知识，放在一起。'}}</h2></div></div>
  <div v-if="!fixedKind" class="gallery-tabs" aria-label="资料分类"><button :class="{active:selected==='overview'}" @click="choose('overview')"><Compass :size="15"/>GTM 概览</button><button v-for="kind in visibleKinds" :key="kind.id" :class="{active:selected===kind.id}" @click="choose(kind.id)"><component :is="kind.icon" :size="15"/>{{kind.name}}<span>{{count(kind.id)}}</span></button><button :class="{active:selected==='glossary'}" @click="choose('glossary')"><BookA :size="15"/>GTM 专有名词库</button></div>
  <GtmGlossaryPreview v-if="selected==='glossary'"/>
  <GtmOverview v-else-if="selected==='overview'"/>
  <template v-else>
  <div class="list-toolbar"><form class="search-field" @submit.prevent="load"><Search :size="17"/><input v-model="query" aria-label="搜索资料" placeholder="搜索主题、企业或关键词"><button>搜索</button></form><ContextPicker/></div>
  <div class="gallery-meta"><button class="text-link" :disabled="busy" @click="refresh">刷新资料</button><span class="meta">{{total}} 份资料 · 点击卡片阅读全文</span></div>
  <LoadingState v-if="busy" label="正在加载资料…"/><p v-else-if="error" class="error" role="alert">{{error}}</p>
  <div v-else class="gallery-columns single-collection">
    <section v-for="kind in columns" :key="kind.id" class="gallery-collection"><div class="collection-heading"><component :is="kind.icon" :size="20"/><h3>{{kind.name}}</h3><span>{{count(kind.id)}}</span></div><p class="collection-description">{{kind.description}}</p>
      <div class="gallery-cards expanded"><RouterLink v-for="item in cards(kind.id)" :key="item.id" :to="url(item)" class="resource-card" @mouseenter="warm(item.id)" @focus="warm(item.id)"><div class="resource-cover"><span class="eyebrow">{{kind.en}}</span><component :is="kind.icon" :size="30" stroke-width="1"/><span class="cover-id">{{item.meta.source_note_id|| (item.private?'MY JD':'ATLAS')}}</span></div><div class="resource-card-body"><span class="resource-type"><Lock v-if="item.private" :size="11"/>{{badge(item)}}</span><h3>{{item.title}}<ArrowUpRight :size="15"/></h3><p>{{item.excerpt}}</p><div class="resource-tags"><span v-for="tag in (item.meta.tags||[]).slice(0,3)" :key="tag">{{tag}}</span></div><div class="resource-footer"><span>{{item.meta.source_author||'GTM Atlas'}}</span></div></div></RouterLink></div>
      <div v-if="!count(kind.id)" class="collection-empty"><component :is="kind.icon" :size="28" stroke-width="1"/><h3>这个栏目还在积累。</h3><p>{{kind.id==='jd'?'岗位 JD 将陆续补充。':'没有符合条件的资料，试试调整岗位或关键词。'}}</p></div>
    </section>
  </div>
  <p class="gallery-footnote meta">资料保留原帖出处与研究整理的阅读边界。面经是个人经验参考，实际岗位要求以目标 JD 为准。</p>
  </template>
</section></template>
<style scoped>
.gallery-tabs{overflow-x:auto}
.gallery-tabs button{flex-shrink:0}
</style>
