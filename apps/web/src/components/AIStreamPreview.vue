<script setup lang="ts">
import Markdown from './Markdown.vue'
import type { AIProgress } from '../features/ai/streaming'
defineProps<{ progress: AIProgress | null; busy: boolean }>()
</script>
<template>
  <section v-if="busy || progress?.text" class="ai-stream-preview" aria-label="AI 生成预览">
    <p class="meta" role="status">{{ busy ? (progress?.label || '正在准备回答') + '…' : '回答未完成，以下为未确认的预览' }}</p>
    <Markdown v-if="progress?.text" ai :source="progress.text" :citations="progress.citations"/>
  </section>
</template>
<style scoped>
.ai-stream-preview{border-left:2px solid var(--blue);padding:4px 20px;margin:20px 0;overflow-wrap:anywhere;min-width:0}.ai-stream-preview :deep(.prose){max-width:none}.ai-stream-preview :deep(pre){overflow:auto}
</style>
