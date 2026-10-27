<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
defineProps<{page: number; pages: number; total: number}>()
const emit = defineEmits<{change: [page: number]}>()
</script>
<template>
  <nav v-if="total > 9" class="card-pagination" aria-label="列表分页">
    <button type="button" class="secondary" :disabled="page <= 1" @click="emit('change', page - 1)"><ChevronLeft :size="15"/>上一页</button>
    <span class="meta" role="status" aria-live="polite">第 {{page}} / {{pages}} 页 · 共 {{total}} 项 · 每页 9 项</span>
    <button type="button" class="secondary" :disabled="page >= pages" @click="emit('change', page + 1)">下一页<ChevronRight :size="15"/></button>
  </nav>
</template>
<style scoped>
.card-pagination{display:flex;align-items:center;justify-content:center;gap:24px;margin:32px 0 12px;padding-top:24px;border-top:1px solid var(--line)}
.card-pagination button{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.card-pagination button:disabled{opacity:.35;cursor:not-allowed}
@media(max-width:760px){.card-pagination{gap:12px;flex-wrap:wrap}.card-pagination .meta{font-size:11px;order:3;width:100%;text-align:center}.card-pagination button{font-size:12px}}
</style>
