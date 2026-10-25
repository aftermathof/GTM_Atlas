<script setup lang="ts">
import { computed, onMounted, onUpdated, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
const props = defineProps<{ source: string; breaks?: boolean }>()
const host = ref<HTMLElement>()
const html = computed(() => DOMPurify.sanitize(marked.parse(props.source, { async: false, breaks: props.breaks || false }) as string))
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
<template><div ref="host" class="prose" v-html="html"></div></template>
