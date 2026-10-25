import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'
import { EditorState } from '@codemirror/state'
import { history, undo, redo, isolateHistory } from '@codemirror/commands'
import { marked, Tokenizer } from 'marked'

const source = () => {
  const context = vm.createContext({exports:{}})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/notesEditing.ts', import.meta.url), 'utf8'), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText, context)
  return context.exports
}
test('bold and italic toggle off on a repeated selection and inside formatted text', () => {
  const { inlineEdit } = source()
  for (const marker of ['**', '*']) {
    const wrapped = inlineEdit('重点内容', 0, 4, marker)
    assert.equal(wrapped.text, marker + '重点内容' + marker)
    assert.equal(inlineEdit(wrapped.text, wrapped.from, wrapped.to, marker).text, '重点内容')
    assert.equal(inlineEdit(wrapped.text, marker.length + 1, marker.length + 1, marker).text, '重点内容')
    assert.equal(inlineEdit(wrapped.text, 0, wrapped.text.length, marker).text, '重点内容')
  }
})
test('formatting respects line boundaries and selected text', () => {
  const { inlineEdit } = source()
  assert.equal(inlineEdit('前文\n正文', 3, 5, '**').text, '前文\n**正文**')
  assert.equal(inlineEdit('**粗体**\n正文', 8, 8, '**').text, '**粗体**\n正**内容**文')
  assert.equal(inlineEdit('**粗体**', 3, 3, '*').text, '**粗*内容*体**')
})

test('typing and format changes share undo/redo history', () => {
  const { inlineEdit } = source()
  let state = EditorState.create({doc:'', extensions:[history()]})
  state = state.update({changes:{from:0,insert:'重点'},selection:{anchor:0,head:2}}).state
  const formatted = inlineEdit(state.doc.toString(), 0, 2, '**')
  state = state.update({changes:{from:0,to:2,insert:formatted.text}, annotations:isolateHistory.of('full')}).state
  const target = {get state(){return state},dispatch(transaction){state=transaction.state}}
  assert.equal(undo(target), true)
  assert.equal(state.doc.toString(),'重点')
  assert.equal(undo(target), true)
  assert.equal(state.doc.toString(),'')
  assert.equal(redo(target),true)
  assert.equal(redo(target),true)
  assert.equal(state.doc.toString(),'**重点**')
})

test('combined bold/italic can toggle each format independently at the caret', () => {
  const { inlineEdit } = source()
  assert.equal(inlineEdit('***重点***',4,4,'*').text,'**重点**')
  assert.equal(inlineEdit('***重点***',4,4,'**').text,'*重点*')
  assert.equal(inlineEdit('*跨行\n重点*',5,5,'*').text,'跨行\n重点')
})

function store() {
  const state = {user:{id:'alice'},token:'alice-token'}
  let requests = 0, resolve
  const context = vm.createContext({exports:{}, Map, require:() => ({state,api:() => {requests++;return new Promise(done=>{resolve=done})}})})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/notesStore.ts',import.meta.url),'utf8'),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText,context)
  return {cache:context.exports,state,get requests(){return requests},respond(value){resolve(value)}}
}
test('returning to the list reuses cached cards and mutations update them',async()=>{
  const {cache,respond}=store()
  const pending=cache.fetchNotes(); respond([]); await pending
  assert.deepEqual(cache.cachedNotes(),[])
  cache.cacheSavedNote({id:'1',title:'笔记',body:'正文',updated_at:'2026-10-26'})
  assert.equal(cache.cachedNotes()[0].title,'笔记')
  assert.equal(cache.cachedNote('1').body,'正文')
  cache.evictNote('1')
  assert.equal(cache.cachedNotes().length,0)
})
test('account changes clear private cache and ignore old account responses',async()=>{
  const {cache,state,respond}=store()
  const pending=cache.fetchNotes()
  state.user={id:'bob'};state.token='bob-token'
  assert.equal(cache.cachedNotes(),undefined)
  respond([{id:'alice-private'}]); await pending
  assert.equal(cache.cachedNotes(),undefined)
  assert.equal(cache.cachedNote('alice-private'),undefined)
})

test('opening a note shares its background preload request', async()=>{
  const app=store()
  const first=app.cache.fetchNote('1'), second=app.cache.fetchNote('1')
  assert.equal(app.requests,1)
  app.respond({id:'1',body:'正文',revision:1})
  await Promise.all([first,second])
  assert.equal(app.cache.cachedNote('1').body,'正文')
})
test('late preloads cannot restore a deleted note or overwrite a saved revision',async()=>{
  const {cache,respond}=store()
  const pending=cache.fetchNote('1')
  cache.evictNote('1')
  respond({id:'1',body:'旧内容',revision:1}); await pending
  assert.equal(cache.cachedNote('1'),undefined)
  const next=cache.fetchNote('2')
  cache.cacheSavedNote({id:'2',body:'新内容',revision:2})
  respond({id:'2',body:'旧内容',revision:1}); await next
  assert.equal(cache.cachedNote('2').body,'新内容')
})

test('live preview preserves source offsets after reference definitions and resolves links',()=>{
  const component=readFileSync(new URL('../src/components/NoteEditor.vue',import.meta.url),'utf8')
  const fn=component.slice(component.indexOf('function renderBlocks('),component.indexOf('const livePreview ='))
  const context=vm.createContext({exports:{},marked,Tokenizer,
    RenderedBlock:class {constructor(raw,from,html){Object.assign(this,{raw,from,html})}},
    Decoration:{replace:options=>({range:(from,to)=>({from,to,...options})}),set:ranges=>ranges}
  })
  vm.runInContext(ts.transpileModule(fn+'\nexports.renderBlocks=renderBlocks',{
    compilerOptions:{target:ts.ScriptTarget.ES2022}
  }).outputText,context)
  const text='[ref]: https://example.com\n\nUse [reference][ref].\nNext line\n\n'
  const ranges=context.exports.renderBlocks({doc:{toString:()=>text},selection:{main:{from:text.length,to:text.length}}})
  assert.equal(ranges.length,1)
  assert.equal(ranges[0].from,text.indexOf('Use'))
  assert.match(ranges[0].widget.html,/href="https:\/\/example.com"/)
  assert.match(ranges[0].widget.html,/<br>/)
  for (const word of ['foo','example.com']) {
    const source='[foo]: https://example.com\n\n'+word+'\n\n'
    const blocks=context.exports.renderBlocks({doc:{toString:()=>source},selection:{main:{from:source.length,to:source.length}}})
    assert.equal(blocks.length,1)
    assert.equal(blocks[0].from,source.lastIndexOf(word))
  }
})

test('delete confirmation keeps keyboard focus inside while its buttons are disabled',()=>{
  const component=readFileSync(new URL('../src/pages/Notes.vue',import.meta.url),'utf8')
  const fn=component.slice(component.indexOf('function trapDelete('),component.indexOf('async function deleteCard('))
  let focused=0,prevented=0
  const context=vm.createContext({exports:{},deleteDialog:{value:{focus(){focused++}}}})
  vm.runInContext(ts.transpileModule(fn+'\nexports.trapDelete=trapDelete',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText,context)
  context.exports.trapDelete({key:'Tab',currentTarget:{querySelectorAll:()=>[]},preventDefault(){prevented++}})
  assert.equal(focused,1)
  assert.equal(prevented,1)
})
