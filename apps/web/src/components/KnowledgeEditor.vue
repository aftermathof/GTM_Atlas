<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { Save, X } from 'lucide-vue-next'
import { editKnowledgeDocument } from '../state'
import NoteEditor from './NoteEditor.vue'
const props=defineProps<{document:any}>()
const emit=defineEmits<{saved:[document:any];cancel:[]}>()
const title=ref(props.document.title),excerpt=ref(props.document.meta.excerpt || ''),body=ref(props.document.body)
const original=ref(JSON.stringify([title.value,excerpt.value,body.value])),busy=ref(false),error=ref('')
const dirty=computed(()=>JSON.stringify([title.value,excerpt.value,body.value])!==original.value)
function canLeave(){return !busy.value && (!dirty.value || window.confirm('资料修改尚未保存，确定放弃修改？'))}
function cancel(){if(canLeave())emit('cancel')}
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate((to,from)=>to.params.slug===from.params.slug || canLeave())
function beforeUnload(event:BeforeUnloadEvent){if(dirty.value || busy.value){event.preventDefault();event.returnValue=''}}
window.addEventListener('beforeunload',beforeUnload)
onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
async function save(){
  if(busy.value)return
  busy.value=true;error.value=''
  try{
    const row=await editKnowledgeDocument(props.document.id,{title:title.value,excerpt:excerpt.value,body:body.value,expected_sha256:props.document.sha256})
    original.value=JSON.stringify([title.value,excerpt.value,body.value]);emit('saved',row)
  }catch(e:any){error.value=e.message}
  finally{busy.value=false}
}
</script>
<template>
  <section class="knowledge-editor" aria-label="修改共享资料">
    <div class="editor-heading"><div><p class="eyebrow">EDIT SHARED ARTICLE</p><h2>修改内容</h2><p class="meta">保存后，共享页面与 AI 检索将更新。</p></div></div>
    <form @submit.prevent="save"><label>标题<input v-model="title" required maxlength="180" :disabled="busy"></label><label>卡片摘要<textarea v-model="excerpt" required rows="3" maxlength="1000" :disabled="busy"></textarea></label><p class="meta">正文支持 Markdown；原帖出处和图片链接可继续保留。</p><NoteEditor v-model="body" :live="true" :disabled="busy"/><p v-if="error" class="error" role="alert">{{error}}</p><div class="editor-actions"><button type="button" class="secondary" :disabled="busy" @click="cancel"><X :size="15"/>取消</button><button class="primary" :disabled="busy || !dirty || !title.trim() || !excerpt.trim() || !body.trim()"><Save :size="15"/>{{busy?'保存与更新索引中…':'保存修改'}}</button></div></form>
  </section>
</template>
<style scoped>
.knowledge-editor{margin:30px 0;border-top:1px solid var(--line);padding-top:28px}.knowledge-editor h2{font-size:28px;font-weight:400}.knowledge-editor label{max-width:900px}.knowledge-editor :deep(.note-editor){border:1px solid var(--line)}.editor-actions{display:flex;justify-content:flex-end;gap:14px;margin:22px 0}.editor-actions button{display:inline-flex;align-items:center;gap:8px}
</style>
