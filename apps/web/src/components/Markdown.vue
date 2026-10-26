<script setup lang="ts">
import { computed, onMounted, onUpdated, ref } from 'vue'
import { Marked } from 'marked'
import { useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { citationExtension, type Citation } from '../aiCitations'
const props = defineProps<{ source: string; breaks?: boolean; ai?: boolean; citations?: Citation[] }>()
const router = useRouter()
const host = ref<HTMLElement>()
const html = computed(() => {
  const parser = new Marked({ breaks: props.breaks || false, extensions: props.ai ? [citationExtension(props.citations)] : [] })
  return DOMPurify.sanitize(parser.parse(props.source, { async: false }) as string)
})
function followCitation(event: MouseEvent) {
  if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
  const link = (event.target as Element).closest('a.inline-citation')
  if (!link || !host.value?.contains(link)) return
  event.preventDefault()
  void router.push(link.getAttribute('href')!)
}
async function render() {
  const nodes = host.value?.querySelectorAll('code.language-mermaid')
  if (!nodes?.length) return
  const { default: mermaid } = await import('mermaid')
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' })
  for (const node of nodes) {
    try { const { svg } = await mermaid.render('mermaid-' + crypto.randomUUID(), node.textContent || ''); const div = document.createElement('div'); div.innerHTML = DOMPurify.sanitize(svg); node.parentElement?.replaceWith(div) } catch { /* Keep readable source on invalid diagrams. */ }
  }
}
onMounted(render); onUpdated(render)
</script>
<template><div ref="host" class="prose" @click="followCitation" v-html="html"></div></template>
<style scoped>
.prose :deep(.inline-citation){display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:18px;margin:0 3px;padding:0 6px;border-radius:6px;background:var(--gray);color:var(--muted);font:11px/1 var(--sans);text-decoration:none;vertical-align:super;white-space:nowrap}
.prose :deep(.inline-citation:hover),.prose :deep(.inline-citation:focus-visible){color:var(--blue);background:#2446eb0d;outline:1px solid currentColor;outline-offset:2px}
</style>
