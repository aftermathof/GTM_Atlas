<script setup lang="ts">
import { watch } from 'vue'
import { state } from '../state'

watch(() => state.context.role, role => {
  if (role !== 'gtm' && role !== 'custom') state.context.role = 'gtm'
  if (state.context.role !== 'custom') state.context.role_raw = ''
}, { immediate: true })
</script>
<template>
  <div class="context-picker">
    <label>目标岗位<select v-model="state.context.role"><option value="gtm">GTM</option><option value="custom">自定义/以JD为准</option></select></label>
    <label>关注行业<select v-model="state.context.industry"><option value="">全部行业</option><option v-for="r in state.industries" :key="r.id" :value="r.id">{{ r.name }}</option></select></label>
    <label v-if="state.context.role === 'custom'" class="custom-role">原始岗位名称<input v-model="state.context.role_raw" placeholder="例如 QB / QC，按你的 JD 保留原名"></label>
  </div>
</template>
