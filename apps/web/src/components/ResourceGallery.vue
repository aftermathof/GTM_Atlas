<script setup lang="ts">
import LoadingState from './LoadingState.vue'
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, BookOpen, BriefcaseBusiness, MessageSquare, Search, Lock, BookA, Compass, BookText, FolderOpen } from 'lucide-vue-next'
import { knowledgeDocuments, peekKnowledge, state } from '../state'
import { warmDocument } from '../preload'
import { cardPage, galleryCards, oldestFirst, type ResourceCard } from '../resourceGallery'
import CardPagination from './CardPagination.vue'
import ContextPicker from './ContextPicker.vue'
import GtmGlossaryPreview from './GtmGlossaryPreview.vue'
import GtmOverview from './GtmOverview.vue'
import GtmBook from './GtmBook.vue'
const props = defineProps<{fixedKind?: string}>()
const route=useRoute(), router=useRouter(), items=ref<ResourceCard[]>([]), query=ref(''), busy=ref(false), error=ref('')
const listTop=ref<HTMLElement>()
const kinds=[{id:'jd',name:'岗位 JD',en:'JOB DESCRIPTIONS',icon:BriefcaseBusiness,description:'读懂职责与能力要求，明确你的目标。'},{id:'interview',name:'面经',en:'INTERVIEW NOTES',icon:MessageSquare,description:'从真实问题与个人复盘，理解考查方向。'},{id:'learning',name:'在职经验',en:'WORK EXPERIENCE',icon:BookOpen,description:'从市场洞察到上市经营，理解实际工作中的方法与经验。'}]
const selected=computed(()=>props.fixedKind ? (route.query.kind==='jd'?'jd':props.fixedKind) : (['overview','learning','glossary','book'].includes(String(route.query.kind))?String(route.query.kind):'overview'))
const filtered=computed(()=>items.value.filter(d=>!d.meta.demo))
const columns=computed(()=>kinds.filter(k=>k.id===selected.value))
const collection=computed(()=>selected.value==='learning'?String(route.query.collection || ''):'')
const sourceCards=computed(()=>filtered.value.filter(d=>d.kind===selected.value))
const collectionTitle=computed(()=>sourceCards.value.find(d=>d.meta.author_collection_id===collection.value)?.meta.author_collection_title || '博主合集')
const entries=computed(()=>collection.value ? oldestFirst(sourceCards.value.filter(d=>d.meta.author_collection_id===collection.value)) : galleryCards(sourceCards.value))
const pagination=computed(()=>cardPage(entries.value,route.query[collection.value?'postPage':'page']))
let generation=0
async function load(){
  const own=++generation, queryString=new URLSearchParams({limit:'100',q:query.value,role:state.context.role,industry:state.context.industry}).toString()
  error.value=''
  const cached=peekKnowledge('/knowledge/documents?'+queryString)
  if(cached && cached.items.length>=cached.total){items.value=cached.items;busy.value=false;return}
  busy.value=true
  try{
    const r=cached || await knowledgeDocuments(queryString), rows=[...r.items]
    for(let offset=100;offset<r.total;offset+=100){
      if(own!==generation)return
      const page=await knowledgeDocuments(queryString+'&offset='+offset)
      rows.push(...page.items)
    }
    if(own===generation)items.value=rows
  }
  catch(e:any){if(own===generation)error.value=e.message}
  finally{if(own===generation)busy.value=false}
}
function choose(kind:string){router.replace({query:{...route.query,kind,collection:undefined,page:undefined,postPage:undefined}})}
function count(kind:string){return filtered.value.filter(d=>d.kind===kind).length}
function url(d:ResourceCard){
  if(d.folder)return {path:'/learn',query:{...route.query,kind:'learning',collection:d.meta.author_collection_id,postPage:undefined}}
  return {path:(d.kind==='interview'?'/interviews/':'/learn/')+d.id,query:collection.value?{collection:collection.value,postPage:String(pagination.value.page),page:route.query.page}: {page:route.query.page}}
}
function warm(d:ResourceCard){if(!d.folder)void warmDocument(d.id,true)}
function badge(d:ResourceCard){return d.folder?'博主合集':d.private?'我的上传':d.kind==='jd'?'岗位 JD':d.kind==='interview'?'面经':d.meta.source_type==='original_research_note'?'研究笔记':'在职经验'}
async function changePage(page:number){
  await router.replace({query:{...route.query,[collection.value?'postPage':'page']:String(page)}})
  await nextTick();listTop.value?.scrollIntoView({block:'start'})
}
async function search(){
  await router.replace({query:{...route.query,page:undefined,postPage:undefined}})
  await load()
}
watch(()=>[state.context.role,state.context.industry,state.user?.id],search)
onMounted(()=>{if(!props.fixedKind && route.query.kind==='jd')void router.replace({path:'/interviews',query:{kind:'jd'}});void load()})
onBeforeUnmount(()=>{generation++})
</script>
<template><section class="resource-gallery">
  <div class="gallery-heading"><div><p class="eyebrow">YOUR GTM READING ROOM</p><h2>{{fixedKind?'把每一次面试，变成下一次的准备。':'岗位、经验与知识，放在一起。'}}</h2></div></div>
  <div v-if="!fixedKind" class="gallery-tabs" aria-label="资料分类">
    <button :class="{active:selected==='overview'}" @click="choose('overview')"><Compass :size="15"/>GTM 概览</button>
    <button :class="{active:selected==='glossary'}" @click="choose('glossary')"><BookA :size="15"/>GTM 专有名词库</button>
    <button :class="{active:selected==='book'}" @click="choose('book')"><BookText :size="15"/>爆品操盘GTM</button>
    <button :class="{active:selected==='learning'}" @click="choose('learning')"><BookOpen :size="15"/>在职经验<span>{{count('learning')}}</span></button>
  </div>
  <div v-else class="gallery-tabs" aria-label="面试资料分类"><button :class="{active:selected==='interview'}" @click="choose('interview')"><MessageSquare :size="15"/>面经<span>{{count('interview')}}</span></button><button :class="{active:selected==='jd'}" @click="choose('jd')"><BriefcaseBusiness :size="15"/>岗位 JD<span>{{count('jd')}}</span></button></div>
  <GtmGlossaryPreview v-if="!fixedKind" v-show="selected==='glossary'"/>
  <GtmOverview v-if="!fixedKind" v-show="selected==='overview'"/>
  <GtmBook v-if="!fixedKind && selected==='book'"/>
  <template v-if="selected!=='glossary' && selected!=='overview' && selected!=='book'">
  <div ref="listTop" class="list-toolbar"><form class="search-field" @submit.prevent="search"><Search :size="17"/><input v-model="query" aria-label="搜索资料" placeholder="搜索主题、企业或关键词"><button>搜索</button></form><ContextPicker/></div>
  <div class="gallery-meta"><span class="meta">{{collection?entries.length:sourceCards.length}} 份资料 · 每页 9 项</span><RouterLink v-if="collection" :to="{path:'/learn',query:{kind:'learning',page:route.query.page}}" class="text-link"><ArrowLeft :size="15"/>返回在职经验</RouterLink></div>
  <LoadingState v-if="busy" label="正在加载资料…"/><p v-else-if="error" class="error" role="alert">{{error}}</p>
  <div v-else class="gallery-columns single-collection">
    <section v-for="kind in columns" :key="kind.id" class="gallery-collection"><div class="collection-heading"><component :is="collection?FolderOpen:kind.icon" :size="20"/><h3>{{collection?collectionTitle:kind.name}}</h3><span>{{collection?entries.length:count(kind.id)}}</span></div><p class="collection-description">{{collection?'按原帖创建顺序，从旧到新阅读。':kind.description}}</p>
      <div class="gallery-cards expanded"><RouterLink v-for="item in pagination.items" :key="item.id" :to="url(item)" class="resource-card" :class="{'folder-card':item.folder}" @mouseenter="warm(item)" @focus="warm(item)"><div class="resource-cover"><span class="eyebrow">{{item.folder?'AUTHOR COLLECTION':kind.en}}</span><component :is="item.folder?FolderOpen:kind.icon" :size="item.folder?40:30" stroke-width="1"/><span class="cover-id">{{item.folder?item.postCount+' 篇':item.meta.source_note_id|| (item.private?'MY JD':'ATLAS')}}</span></div><div class="resource-card-body"><span class="resource-type"><Lock v-if="item.private" :size="11"/>{{badge(item)}}</span><h3>{{item.title}}<ArrowUpRight :size="15"/></h3><p>{{item.excerpt}}</p><div class="resource-tags"><span v-for="tag in (item.meta.tags||[]).slice(0,3)" :key="tag">{{tag}}</span></div><div class="resource-footer"><span>{{item.meta.source_author||'GTM Atlas'}}</span><span v-if="collection && item.meta.displayed_date">{{item.meta.displayed_date}}</span><span v-else-if="item.folder">打开文件夹</span></div></div></RouterLink></div>
      <CardPagination :page="pagination.page" :pages="pagination.pages" :total="pagination.total" @change="changePage"/>
      <div v-if="!entries.length" class="collection-empty"><component :is="kind.icon" :size="28" stroke-width="1"/><h3>这个栏目还在积累。</h3><p>{{kind.id==='jd'?'岗位 JD 将陆续补充。':'没有符合条件的资料，试试调整岗位或关键词。'}}</p></div>
    </section>
  </div>
  <p class="gallery-footnote meta">资料保留原帖出处。面经是个人经验参考，实际岗位要求以目标 JD 为准。</p>
  </template>
</section></template>
<style scoped>
.gallery-tabs{overflow-x:auto}
.gallery-tabs button{flex-shrink:0}
.list-toolbar{scroll-margin-top:90px}
.folder-card .resource-cover{background:rgba(0,47,167,.055);border-top:3px solid var(--blue)}
.folder-card .cover-id{font-size:27px}
.resource-footer>span:last-child{max-width:65%;overflow:hidden;text-overflow:ellipsis}
</style>
