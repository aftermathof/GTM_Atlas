<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import Markdown from './Markdown.vue'
const props = defineProps<{ source: string; heading?: string }>()
const emit = defineEmits<{ ask: [] }>()
const article = ref<HTMLElement>(), headings = ref<{text:string;depth:number}[]>([])
let elements: HTMLElement[] = []
function scrollToHeading(index: number) { elements[index]?.scrollIntoView({behavior:'smooth',block:'start'}) }
async function syncHeadings() {
  await nextTick()
  elements = Array.from(article.value?.querySelectorAll<HTMLElement>('.prose h2,.prose h3') || [])
  headings.value = elements.map(el=>({text:el.textContent?.trim() || '',depth:Number(el.tagName.slice(1))}))
  if (props.heading) elements.find(el=>el.textContent?.trim()===props.heading)?.scrollIntoView({block:'start'})
}
watch(()=>[props.source,props.heading],syncHeadings)
onMounted(syncHeadings)
</script>
<template>
  <div ref="article" class="article-grid">
    <aside class="sidebar"><nav aria-label="文章目录"><p v-if="headings.length" class="eyebrow">目录</p><button v-for="(heading,index) in headings" :key="index" class="toc-link" :class="{subheading:heading.depth===3}" @click="scrollToHeading(index)">{{ heading.text }}</button></nav><button class="text-link" @click="emit('ask')">询问当前文章 ↗</button></aside>
    <Markdown :source="source"/>
  </div>
</template>
<style scoped>
.sidebar nav{display:flex;flex-direction:column;max-height:65dvh;overflow:auto}
.toc-link{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);padding:12px 0;font-size:13px;line-height:1.7;color:var(--muted)}
.toc-link:hover{color:var(--blue)}
.toc-link.subheading{padding-left:12px;font-size:12px}
.sidebar>.text-link{margin-top:16px}
:deep(.prose h2),:deep(.prose h3){scroll-margin-top:108px}
@media(max-width:760px){.sidebar{display:block}.sidebar nav{max-height:220px}}
</style>
