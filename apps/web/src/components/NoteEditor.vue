<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { Compartment, EditorState, StateField, Transaction } from '@codemirror/state'
import { Decoration, EditorView, WidgetType, keymap, placeholder, type DecorationSet } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, isolateHistory } from '@codemirror/commands'
import { marked, Tokenizer } from 'marked'
import DOMPurify from 'dompurify'
import { inlineEdit } from '../notesEditing'

const props = defineProps<{ modelValue: string; live: boolean; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const host = ref<HTMLElement>()
let view: EditorView | undefined
const liveMode = new Compartment(), editable = new Compartment()

class RenderedBlock extends WidgetType {
  constructor(readonly raw: string, readonly from: number, readonly html: string) { super() }
  eq(other: RenderedBlock) { return this.raw === other.raw && this.from === other.from && this.html === other.html }
  toDOM(editor: EditorView) {
    const dom = document.createElement('div')
    dom.className = 'note-rendered prose'
    dom.innerHTML = DOMPurify.sanitize(this.html)
    dom.addEventListener('mousedown', event => {
      if (props.disabled) return
      event.preventDefault()
      editor.dispatch({selection:{anchor:this.from}})
      editor.focus()
      // Resolve coordinates after revealing source, without guessing repeated text offsets.
      requestAnimationFrame(() => {
        if (!editor.dom.isConnected) return
        const position = editor.posAtCoords({x:event.clientX, y:event.clientY})
        if (position !== null) editor.dispatch({selection:{anchor:Math.max(this.from, Math.min(position, this.from + this.raw.trimEnd().length))}})
      })
    })
    return dom
  }
  ignoreEvent() { return true }
}

function renderBlocks(state: EditorState) {
  const ranges = [], selection = state.selection.main
  let from = 0
  const source = state.doc.toString(), definitions: {from:number; to:number}[] = []
  const tokenizer = new Tokenizer(), definition = tokenizer.def.bind(tokenizer)
  tokenizer.def = remaining => {
    const token = definition(remaining)
    if (token && source.endsWith(remaining)) {
      const start = source.length - remaining.length
      definitions.push({from:start, to:start + token.raw.length})
    }
    return token
  }
  const tokens = marked.lexer(source, {gfm:true, breaks:true, tokenizer})
  for (const token of tokens) {
    from = source.indexOf(token.raw, from)
    let skipped = definitions.find(range => from >= range.from && from < range.to)
    while (from >= 0 && skipped) {
      from = source.indexOf(token.raw, skipped.to)
      skipped = definitions.find(range => from >= range.from && from < range.to)
    }
    if (from < 0) break
    const end = from + token.raw.length
    const to = end - (token.raw.match(/\n+$/)?.[0].length || 0)
    const active = selection.from <= to && selection.to >= from
    if (token.type !== 'space' && to > from && !active) {
      ranges.push(Decoration.replace({widget:new RenderedBlock(token.raw, from, marked.parser(Object.assign([token], {links:tokens.links}), {async:false, breaks:true}) as string), block:true}).range(from, to))
    }
    from = end
  }
  return Decoration.set(ranges, true)
}
const livePreview = StateField.define<DecorationSet>({
  create: renderBlocks,
  update: (value, transaction) => transaction.docChanged || transaction.selection ? renderBlocks(transaction.state) : value,
  provide: field => EditorView.decorations.from(field),
})
function change(text: string, from: number, to: number, isolated = false) {
  if (!view || props.disabled) return
  const previous = view.state.doc.toString()
  let start = 0, end = previous.length, nextEnd = text.length
  while (start < end && start < nextEnd && previous[start] === text[start]) start++
  while (end > start && nextEnd > start && previous[end - 1] === text[nextEnd - 1]) { end--; nextEnd-- }
  view.dispatch({changes:{from:start, to:end, insert:text.slice(start, nextEnd)}, selection:{anchor:from, head:to}, scrollIntoView:true,
    annotations: isolated ? isolateHistory.of('full') : []})
  view.focus()
}
function toggle(marker: string) {
  if (!view) return
  const {from, to} = view.state.selection.main
  const result = inlineEdit(view.state.doc.toString(), from, to, marker)
  change(result.text, result.from, result.to, true)
}
function insert(before: string, after = '', fallback = '内容') {
  if (!view) return
  const {from, to} = view.state.selection.main, text = view.state.doc.toString()
  const selected = text.slice(from, to) || fallback
  change(text.slice(0, from) + before + selected + after + text.slice(to), from + before.length, from + before.length + selected.length, true)
}
onMounted(() => {
  view = new EditorView({parent:host.value, state:EditorState.create({doc:props.modelValue, extensions:[
    history(), keymap.of([
      {key:'Mod-b', run:() => { toggle('**'); return true }},
      {key:'Mod-i', run:() => { toggle('*'); return true }},
      ...historyKeymap, ...defaultKeymap,
    ]), EditorView.lineWrapping,
    placeholder('从这里开始记录…'),
    EditorView.contentAttributes.of({'aria-label':'笔记 Markdown 正文', spellcheck:'false'}),
    editable.of([EditorView.editable.of(!props.disabled), EditorState.readOnly.of(!!props.disabled)]),
    liveMode.of(props.live ? [livePreview] : []),
    EditorView.updateListener.of(update => { if (update.docChanged) emit('update:modelValue', update.state.doc.toString()) }),
  ]})})
})
watch(() => props.modelValue, value => {
  if (view && value !== view.state.doc.toString()) view.dispatch({changes:{from:0, to:view.state.doc.length, insert:value}, annotations:Transaction.addToHistory.of(false)})
})
watch(() => props.live, value => view?.dispatch({effects:liveMode.reconfigure(value ? [livePreview] : [])}))
watch(() => props.disabled, value => view?.dispatch({effects:editable.reconfigure([EditorView.editable.of(!value), EditorState.readOnly.of(!!value)])}))
onBeforeUnmount(() => view?.destroy())
defineExpose({insert, toggle})
</script>

<template><div ref="host" class="note-editor" :class="{live}"/></template>

<style scoped>
.note-editor{min-height:54vh;padding:24px 0;font-size:16px;line-height:1.95}
.note-editor :deep(.cm-editor){background:transparent;min-height:54vh}
.note-editor :deep(.cm-editor.cm-focused){outline:none}
.note-editor :deep(.cm-scroller){font-family:ui-monospace,Consolas,monospace;line-height:1.95;overflow:visible}
.note-editor :deep(.cm-content){padding:0 8px;caret-color:var(--blue)}
.note-editor :deep(.cm-line){padding:0;overflow-wrap:anywhere}
.note-editor :deep(.cm-selectionBackground){background:#002fa71b!important}
.note-editor :deep(.note-rendered){font-family:var(--sans-zh);margin:0;padding:0;cursor:text;overflow-wrap:anywhere;white-space:normal}
.note-editor :deep(.note-rendered h1),.note-editor :deep(.note-rendered h2),.note-editor :deep(.note-rendered h3){border:0;margin:0;padding:0;font-weight:500}
.note-editor :deep(.note-rendered p){margin:0}
.note-editor :deep(.note-rendered blockquote){background:#002fa708;border-left:3px solid #002fa740;padding:12px 18px;margin:4px 0;color:var(--ink)}
.note-editor :deep(.note-rendered pre){white-space:pre-wrap;overflow-wrap:anywhere}
.note-editor :deep(.note-rendered table){width:100%;border-collapse:collapse}
.note-editor :deep(.note-rendered td),.note-editor :deep(.note-rendered th){border:1px solid var(--line);padding:8px 12px}
@media(max-width:760px){.note-editor{font-size:15px;padding:16px 0}.note-editor :deep(.cm-content){padding:0}}
</style>
