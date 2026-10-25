<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
defineProps<{ title: string; name?: string; description?: string }>()
const emit=defineEmits<{cancel:[];confirm:[]}>()
const dialog=ref<HTMLElement>(), cancel=ref<HTMLButtonElement>()
let previous: HTMLElement | null=null
onMounted(()=>{previous=document.activeElement as HTMLElement;cancel.value?.focus()})
onBeforeUnmount(()=>{if(previous?.isConnected)previous.focus()})
function trap(event:KeyboardEvent) {
  if(event.key==='Escape'){event.preventDefault();event.stopPropagation();emit('cancel')}
  if(event.key!=='Tab')return
  const buttons=dialog.value?.querySelectorAll<HTMLButtonElement>('button')
  if(!buttons?.length)return
  const first=buttons[0],last=buttons[buttons.length-1]
  if(event.shiftKey && document.activeElement===first){event.preventDefault();last.focus()}
  else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first.focus()}
}
</script>
<template>
  <Teleport to="body"><div class="delete-backdrop" @click.self="emit('cancel')">
    <section ref="dialog" class="delete-dialog" role="alertdialog" aria-modal="true" aria-labelledby="record-delete-title" aria-describedby="record-delete-description" @keydown="trap">
      <p class="eyebrow">MANAGE YOUR RECORDS</p><h2 id="record-delete-title">{{title}}</h2>
      <p v-if="name" class="delete-name">{{name}}</p>
      <p id="record-delete-description">{{description || '删除后无法恢复。'}}</p>
      <div class="delete-actions"><button ref="cancel" class="secondary" @click="emit('cancel')">取消</button><button class="primary delete-confirm" @click="emit('confirm')">确认删除</button></div>
    </section>
  </div></Teleport>
</template>
<style scoped>
.delete-backdrop{position:fixed;inset:0;z-index:100;background:#0a0a0a40;display:grid;place-items:center;padding:24px}.delete-dialog{width:min(440px,100%);background:var(--bg);border:1px solid var(--line);padding:32px}.delete-dialog h2{font-size:26px;font-weight:400;margin:18px 0}.delete-dialog p{font-size:13px;color:var(--muted);line-height:1.9;overflow-wrap:anywhere}.delete-dialog .delete-name{font-size:17px;color:var(--ink);margin-bottom:14px}.delete-actions{display:flex;justify-content:flex-end;gap:12px;margin-top:28px}.delete-confirm{background:#a52c2c;border-color:#a52c2c}
</style>
