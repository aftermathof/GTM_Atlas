<script setup lang="ts">
import LoadingState from './LoadingState.vue'
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ArrowLeft, BookOpen, BriefcaseBusiness, MessageSquare, Search, Lock, BookA, Compass, BookText, FolderOpen, Pencil, Trash2 } from 'lucide-vue-next'
import { knowledgeCapabilities, knowledgeDocuments, knowledgeDocument, peekKnowledgeDocuments, deleteKnowledgeDocument, state } from '../state'
import { warmDocument } from '../preload'
import { cardPage, galleryCards, collectionCards, type ResourceCard } from '../resourceGallery'
import CardPagination from './CardPagination.vue'
import ConfirmDelete from './ConfirmDelete.vue'
import ContextPicker from './ContextPicker.vue'
import GtmGlossaryPreview from './GtmGlossaryPreview.vue'
import GtmOverview from './GtmOverview.vue'
import GtmBook from './GtmBook.vue'
import GtmSop from './GtmSop.vue'
const props = defineProps<{fixedKind?: string}>()
const route=useRoute(), router=useRouter(), items=ref<ResourceCard[]>([]), query=ref(String(route.query.q||'')), busy=ref(false), error=ref('')
const listTop=ref<HTMLElement>(), canManage=ref(false), pendingDelete=ref<any>(null), deleting=ref(false)
const matches=ref<Set<string>|null>(null)
const kinds=[{id:'jd',name:'岗位 JD',en:'JOB DESCRIPTIONS',icon:BriefcaseBusiness,description:'读懂职责与能力要求，明确你的目标。'},{id:'interview',name:'面经',en:'INTERVIEW NOTES',icon:MessageSquare,description:'从真实问题与个人复盘，理解考查方向。'},{id:'learning',name:'在职经验',en:'WORK EXPERIENCE',icon:BookOpen,description:'从市场洞察到上市经营，理解实际工作中的方法与经验。'}]
const selected=computed(()=>props.fixedKind ? (route.query.kind==='jd'?'jd':props.fixedKind) : (['overview','learning','glossary','book','sop'].includes(String(route.query.kind))?String(route.query.kind):'overview'))
const sopOpened=ref(selected.value==='sop')
watch(selected,kind=>{if(kind==='sop')sopOpened.value=true})
const filtered=computed(()=>items.value.filter(d=>!d.meta.demo))
const columns=computed(()=>kinds.filter(k=>k.id===selected.value))
const collection=computed(()=>selected.value==='learning'?String(route.query.collection || ''):'')
const sourceCards=computed(()=>filtered.value.filter(d=>d.kind===selected.value))
const collectionTitle=computed(()=>sourceCards.value.find(d=>d.meta.author_collection_id===collection.value)?.meta.author_collection_title || '博主合集')
const fullEntries=computed(()=>collection.value ? collectionCards(sourceCards.value.filter(d=>d.meta.author_collection_id===collection.value)) : galleryCards(sourceCards.value))
const entries=computed(()=>fullEntries.value.filter(item=>!matches.value || (item.folder?sourceCards.value.some(post=>post.meta.author_collection_id===item.meta.author_collection_id && matches.value!.has(post.id)):matches.value.has(item.id))))
const pagination=computed(()=>cardPage(entries.value,route.query[collection.value?'postPage':'page']))
let generation=0
function catalogQuery(q:string){return new URLSearchParams({limit:'100',q,role:state.context.role,industry:state.context.industry}).toString()}
async function fetchAll(q:string, own:number){
  const queryString=catalogQuery(q)
  const first=await knowledgeDocuments(queryString), rows=[...first.items]
  for(let offset=100;offset<first.total;offset+=100){
    if(own!==generation)return []
    rows.push(...(await knowledgeDocuments(queryString+'&offset='+offset)).items)
  }
  return rows
}
async function load(){
  const own=++generation
  error.value=''
  const cached=peekKnowledgeDocuments(catalogQuery(''))
  const found=query.value.trim()?peekKnowledgeDocuments(catalogQuery(query.value.trim())):null
  if(cached && (!query.value.trim() || found)){
    items.value=cached;matches.value=found?new Set<string>(found.map(item=>item.id)):null;busy.value=false;return
  }
  busy.value=true
  try{
    const all=await fetchAll('',own)
    const found=query.value.trim()?new Set<string>((await fetchAll(query.value.trim(),own)).map((item:any)=>item.id)):null
    if(own===generation){items.value=all;matches.value=found}
  }catch(e:any){if(own===generation)error.value=e.message}
  finally{if(own===generation)busy.value=false}
}
async function permissions(){
  canManage.value=false
  if(!state.user)return
  try{canManage.value=!!(await knowledgeCapabilities()).can_manage_learning}catch{}
}
async function requestDelete(item:ResourceCard){
  if(deleting.value)return
  error.value=''
  try{pendingDelete.value=await knowledgeDocument(item.id)}catch(e:any){error.value=e.message}
}
async function confirmRemove(){
  const item=pendingDelete.value
  if(!item || deleting.value)return
  pendingDelete.value=null;deleting.value=true;error.value=''
  try{await deleteKnowledgeDocument(item.id,item.sha256)}catch(e:any){error.value=e.message}
  finally{deleting.value=false}
}
function editable(item:ResourceCard){return canManage.value && !item.folder && item.kind==='learning' && item.meta.source_type==='original_research_note'}
function editUrl(item:ResourceCard){const target=url(item);return {...target,query:{...target.query,edit:'1'}}}
function choose(kind:string){router.replace({query:{...route.query,kind,collection:undefined,page:undefined,postPage:undefined}})}
function count(kind:string){return filtered.value.filter(d=>d.kind===kind).length}
function url(d:ResourceCard){
  if(d.folder)return {path:'/learn',query:{...route.query,kind:'learning',collection:d.meta.author_collection_id,postPage:undefined}}
  return {path:(d.kind==='interview'?'/interviews/':'/learn/')+d.id,query:collection.value?{collection:collection.value,postPage:String(pagination.value.page),page:route.query.page,q:route.query.q}: {page:route.query.page,q:route.query.q}}
}
function warm(d:ResourceCard){if(!d.folder)void warmDocument(d.id,true)}
function badge(d:ResourceCard){return d.folder?'博主合集':d.private?'我的上传':d.kind==='jd'?'岗位 JD':d.kind==='interview'?'面经':d.meta.source_type==='original_research_note'?'研究笔记':'在职经验'}
async function changePage(page:number){
  await router.replace({query:{...route.query,[collection.value?'postPage':'page']:String(page)}})
  await nextTick();listTop.value?.scrollIntoView({block:'start'})
}
async function search(){
  await router.replace({query:{...route.query,page:undefined,postPage:undefined,q:query.value.trim()||undefined}})
  await load()
}
watch(()=>[state.context.role,state.context.industry,state.user?.id],search)
watch(()=>state.user?.id,permissions,{immediate:true})
watch(()=>state.knowledgeRevision,load)
onMounted(()=>{if(!props.fixedKind && route.query.kind==='jd')void router.replace({path:'/interviews',query:{kind:'jd'}});void load()})
onBeforeUnmount(()=>{generation++})
</script>
<template><section class="resource-gallery">
  <ConfirmDelete v-if="pendingDelete" title="删除这篇在职经验？" :name="pendingDelete.title" description="资料将从共享列表和 AI 检索中撤下，所有用户都会受到影响；原始 Markdown 保留备份。" @cancel="pendingDelete=null" @confirm="confirmRemove"/>
  <div class="gallery-heading"><div><p class="eyebrow">YOUR GTM READING ROOM</p><h2>{{fixedKind?'把每一次面试，变成下一次的准备。':'岗位、经验与知识，放在一起。'}}</h2></div></div>
  <div v-if="!fixedKind" class="gallery-tabs" aria-label="资料分类">
    <button :class="{active:selected==='overview'}" @click="choose('overview')"><Compass :size="15"/>GTM 概览</button>
    <button :class="{active:selected==='glossary'}" @click="choose('glossary')"><BookA :size="15"/>GTM 专有名词库</button>
    <button :class="{active:selected==='book'}" @click="choose('book')"><BookText :size="15"/>爆品操盘GTM</button>
    <button :class="{active:selected==='learning'}" @click="choose('learning')"><BookOpen :size="15"/>在职经验<span>{{count('learning')}}</span></button>
    <button :class="{active:selected==='sop'}" @click="choose('sop')"><FolderOpen :size="15"/>SOP</button>
  </div>
  <div v-else class="gallery-tabs" aria-label="面试资料分类"><button :class="{active:selected==='interview'}" @click="choose('interview')"><MessageSquare :size="15"/>面经<span>{{count('interview')}}</span></button><button :class="{active:selected==='jd'}" @click="choose('jd')"><BriefcaseBusiness :size="15"/>岗位 JD<span>{{count('jd')}}</span></button></div>
  <GtmGlossaryPreview v-if="!fixedKind" v-show="selected==='glossary'"/>
  <GtmOverview v-if="!fixedKind" v-show="selected==='overview'"/>
  <GtmBook v-if="!fixedKind && selected==='book'"/>
  <GtmSop v-if="!fixedKind && sopOpened" v-show="selected==='sop'"/>
  <template v-if="selected!=='glossary' && selected!=='overview' && selected!=='book' && selected!=='sop'">
  <div ref="listTop" class="list-toolbar"><form class="search-field" @submit.prevent="search"><Search :size="17"/><input v-model="query" aria-label="搜索资料" placeholder="搜索主题、企业或关键词"><button>搜索</button></form><ContextPicker/></div>
  <div class="gallery-meta"><RouterLink v-if="collection" :to="{path:'/learn',query:{kind:'learning',page:route.query.page,q:route.query.q}}" class="text-link"><ArrowLeft :size="15"/>返回在职经验</RouterLink><span class="meta">{{collection?entries.length:sourceCards.length}} 份资料 · 每页 9 项</span><span v-if="deleting" class="meta" role="status">正在删除资料…</span></div>
  <LoadingState v-if="busy" label="正在加载资料…"/><p v-else-if="error" class="error" role="alert">{{error}}</p>
  <div v-else class="gallery-columns single-collection">
    <section v-for="kind in columns" :key="kind.id" class="gallery-collection"><div class="collection-heading"><component :is="collection?FolderOpen:kind.icon" :size="20"/><h3>{{collection?collectionTitle:kind.name}}</h3><span>{{collection?entries.length:count(kind.id)}}</span></div><p class="collection-description">{{collection?'按原帖创建顺序，从旧到新阅读。':kind.description}}</p>
      <div class="gallery-cards expanded"><article v-for="item in pagination.items" :key="item.id" class="gallery-card-shell"><RouterLink :to="url(item)" class="resource-card" :class="{'folder-card':item.folder}" @mouseenter="warm(item)" @focus="warm(item)"><div class="resource-cover"><span class="eyebrow">{{item.folder?'AUTHOR COLLECTION':kind.en}}</span><component :is="item.folder?FolderOpen:kind.icon" :size="item.folder?40:30" stroke-width="1"/><span class="cover-id">{{item.folder?item.postCount+' 篇':selected==='learning'?'L'+item.displayNumber:item.meta.source_note_id|| (item.private?'MY JD':'ATLAS')}}</span></div><div class="resource-card-body"><span class="resource-type"><Lock v-if="item.private" :size="11"/>{{badge(item)}}</span><h3>{{item.title}}<ArrowUpRight :size="15"/></h3><p>{{item.excerpt}}</p><div class="resource-tags"><span v-for="tag in (item.meta.tags||[]).slice(0,3)" :key="tag">{{tag}}</span></div><div class="resource-footer"><span>{{item.meta.source_author||'GTM Atlas'}}</span><span v-if="collection && item.meta.displayed_date">{{item.meta.displayed_date}}</span><span v-else-if="item.folder">打开文件夹</span></div></div></RouterLink><div v-if="editable(item)" class="resource-actions"><RouterLink :to="editUrl(item)" class="text-link"><Pencil :size="13"/>修改内容</RouterLink><button type="button" class="text-link" :disabled="deleting" @click="requestDelete(item)"><Trash2 :size="13"/>删除</button></div></article></div>
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

<style scoped>
.gallery-card-shell{display:flex;flex-direction:column;min-width:0}.gallery-card-shell>.resource-card{flex:1}.resource-actions{display:flex;justify-content:flex-end;gap:20px;padding:12px 16px;border:1px solid var(--line);border-top:0}.resource-actions .text-link{display:inline-flex;gap:6px;align-items:center;font-size:12px}.gallery-meta{justify-content:flex-start}.gallery-meta .text-link{margin-right:16px}
</style>
