<script setup lang="ts">
import { ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { pageToJump } from '../resourceGallery'
const props=defineProps<{page: number; pages: number; total: number}>()
const emit = defineEmits<{change: [page: number]}>()
const target=ref(String(props.page)), error=ref('')
watch(()=>[props.page,props.pages],()=>{target.value=String(props.page);error.value=''})
function jump(){
  const page=pageToJump(target.value,props.pages)
  if(page===null){error.value='请输入 1–'+props.pages+' 之间的整数页码';return}
  error.value='';emit('change',page)
}
</script>
<template>
  <nav v-if="total > 9" class="card-pagination" aria-label="列表分页">
    <button type="button" class="secondary" :disabled="page <= 1" @click="emit('change', page - 1)"><ChevronLeft :size="15"/>上一页</button>
    <span class="meta" role="status" aria-live="polite">第 {{page}} / {{pages}} 页 · 共 {{total}} 项 · 每页 9 项</span>
    <button type="button" class="secondary" :disabled="page >= pages" @click="emit('change', page + 1)">下一页<ChevronRight :size="15"/></button>
    <form class="page-jump" @submit.prevent="jump"><label>跳至<input v-model="target" type="text" inputmode="numeric" aria-label="跳转页码" :aria-invalid="!!error" @input="error=''">页</label><button type="submit" class="secondary">跳转</button></form>
    <p v-if="error" class="error jump-error" role="alert">{{error}}</p>
  </nav>
</template>
<style scoped>
.card-pagination{display:flex;align-items:center;justify-content:center;gap:20px;flex-wrap:wrap;margin:32px 0 12px;padding-top:24px;border-top:1px solid var(--line)}
.card-pagination button{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.card-pagination button:disabled{opacity:.35;cursor:not-allowed}
.page-jump,.page-jump label{display:flex;flex-direction:row;align-items:center;gap:8px;font-size:12px;margin:0}
.page-jump input{width:60px;text-align:center;min-height:36px;padding:6px!important}
.jump-error{width:100%;text-align:center;margin:0;font-size:12px}
@media(max-width:760px){.card-pagination{gap:12px}.card-pagination>.meta{font-size:11px;order:3;width:100%;text-align:center}.page-jump{order:4}.card-pagination button{font-size:12px}}
</style>
