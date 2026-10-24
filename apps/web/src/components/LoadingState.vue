<script setup lang="ts">
defineProps<{ label?: string; compact?: boolean }>()
</script>
<template><div class="loading-state" :class="{compact}" role="status" aria-live="polite"><span class="loading-ring" aria-hidden="true"></span><span>{{ label || '正在加载…' }}</span></div></template>
<style scoped>
.loading-state{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;min-height:min(50dvh,420px);padding:32px 16px;color:var(--blue);font-size:clamp(22px,3vw,28px);font-weight:500;text-align:center}
.loading-state.compact{min-height:140px;font-size:22px}
.loading-ring{width:28px;height:28px;border:2px solid var(--line);border-top-color:var(--blue);border-radius:50%;animation:loading-spin 1s linear infinite}
@keyframes loading-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.loading-ring{animation:none}}
</style>
