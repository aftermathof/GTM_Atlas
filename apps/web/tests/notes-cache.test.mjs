import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

const compile = source => ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
function fixture() {
  const state={user:{id:'alice'},token:'alice-token',notesDeleteError:'',notesRevision:0}
  const requests=[]
  const api=path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject}))
  const context=vm.createContext({exports:{},Map,require:()=>({state,api})})
  vm.runInContext(compile(readFileSync(new URL('../src/features/notes/notesStore.ts',import.meta.url),'utf8')),context)
  return {state,api,requests,cache:context.exports}
}
function page(app, query={}) {
  const route=vue.reactive({params:{},query})
  const helpers=vm.createContext({exports:{}})
  vm.runInContext(compile(readFileSync(new URL('../src/features/notes/noteFolders.ts',import.meta.url),'utf8')),helpers)
  const context=vm.createContext({exports:{},window:{addEventListener(){},removeEventListener(){}},require:name=>{
    if(name==='vue')return {...vue,watch(){},onBeforeUnmount(){}}
    if(name==='vue-router')return {useRoute:()=>route,useRouter:()=>({}),onBeforeRouteLeave(){},onBeforeRouteUpdate(){}}
    if(name==='../state')return {state:app.state,api:app.api}
    if(name==='../features/notes/notesStore')return app.cache
    if(name==='../features/notes/noteFolders')return helpers.exports
    return {}
  }})
  const {descriptor}=parse(readFileSync(new URL('../src/pages/Notes.vue',import.meta.url),'utf8'))
  vm.runInContext(compile(compileScript(descriptor,{id:'notes-cache-test'}).content),context)
  return {route,component:context.exports.default.setup({}, {expose(){}})}
}
const folder={id:'folder',title:'我的文件夹',created_at:'2026-10-28'}
const note={id:'note',title:'已缓存笔记',body:'正文',folder_id:'folder',created_at:'2026-10-28',updated_at:'2026-10-28',revision:1}

test('folder and note lists share requests and reuse complete cached lists',async()=>{
  const app=fixture()
  const first=app.cache.fetchNoteFolders(), second=app.cache.fetchNoteFolders()
  assert.equal(app.requests.length,1)
  app.requests[0].resolve([folder]);await Promise.all([first,second])
  await app.cache.fetchNoteFolders()
  assert.equal(app.requests.length,1)
  const pending=app.cache.fetchNotes();app.requests[1].resolve([note]);await pending
  await app.cache.fetchNotes()
  assert.equal(app.requests.length,2)
})

test('returning to notes and switching folders renders synchronously without another request',async()=>{
  const app=fixture()
  const folderLoad=app.cache.fetchNoteFolders();app.requests[0].resolve([folder]);await folderLoad
  const noteLoad=app.cache.fetchNotes();app.requests[1].resolve([note]);await noteLoad
  app.cache.cacheSavedNote(note)
  const {component,route}=page(app)
  const pending=component.load()
  assert.equal(component.loading.value,false)
  assert.equal(component.cards.value[0].title,note.title)
  assert.equal(component.folders.value[0].title,folder.title)
  await pending
  route.query.folder='folder'
  const switching=component.load()
  assert.equal(component.loading.value,false)
  assert.equal(component.visibleCards.value[0].id,note.id)
  await switching
  route.params.id='note'
  const opening=component.load()
  assert.equal(component.loading.value,false)
  assert.equal(component.body.value,'正文')
  await opening
  assert.equal(app.requests.length,2)
})

test('a new folder updates the cache',async()=>{
  const app=fixture()
  const loaded=app.cache.fetchNoteFolders();app.requests[0].resolve([folder]);await loaded
  app.cache.cacheSavedNoteFolder({...folder,id:'new',title:'新文件夹'})
  assert.equal(app.cache.cachedNoteFolders().length,2)
})

test('late folder reads cannot erase a newly created folder',async()=>{
  const app=fixture()
  const pending=app.cache.fetchNoteFolders()
  app.cache.cacheSavedNoteFolder(folder)
  app.requests[0].resolve([])
  await Promise.resolve()
  assert.equal(app.requests.length,2)
  app.requests[1].resolve([folder]);await pending
  assert.equal(app.cache.cachedNoteFolders()[0].id,folder.id)
})

test('a slow folder request cannot overwrite text typed in a cached or new note',async()=>{
  for(const id of ['note','new']){
    const app=fixture();app.cache.cacheSavedNote(note)
    const {component,route}=page(app,{folder:'folder'})
    route.params.id=id
    const pending=component.load()
    assert.equal(component.loading.value,false)
    component.title.value='刚输入的标题';component.body.value='刚输入的正文'
    app.requests[0].resolve([folder]);await pending
    assert.equal(component.title.value,'刚输入的标题')
    assert.equal(component.body.value,'刚输入的正文')
  }
})

test('folders clear on account changes and old responses cannot warm the new account',async()=>{
  const app=fixture()
  const pending=app.cache.fetchNoteFolders()
  app.state.user={id:'bob'};app.state.token='bob-token'
  assert.equal(app.cache.cachedNoteFolders(),undefined)
  app.requests[0].resolve([folder]);await pending
  assert.equal(app.cache.cachedNoteFolders(),undefined)
})


test('folder deletion immediately evicts folders and child notes, then restores them on failure',async()=>{
  const app=fixture()
  let pending=app.cache.fetchNoteFolders();app.requests[0].resolve([folder]);await pending
  pending=app.cache.fetchNotes();app.requests[1].resolve([note,{...note,id:'root',folder_id:null}]);await pending
  app.cache.cacheSavedNote(note)
  const deletion=app.cache.deleteNoteFolder(folder)
  assert.equal(app.cache.cachedNoteFolders().length,0)
  assert.deepEqual(Array.from(app.cache.cachedNotes(), row=>row.id),['root'])
  assert.equal(app.cache.cachedNote(note.id),undefined)
  app.requests[2].reject(new Error('offline'))
  await assert.rejects(deletion,/offline/)
  assert.equal(app.cache.cachedNoteFolders()[0].id,folder.id)
  assert.equal(app.cache.cachedNote(note.id).body,'正文')
  assert.equal(app.cache.cachedNotes().length,2)
})

test('successful folder deletion cannot be undone by a late detail response or account change',async()=>{
  const app=fixture()
  let pending=app.cache.fetchNoteFolders();app.requests[0].resolve([folder]);await pending
  pending=app.cache.fetchNotes();app.requests[1].resolve([note]);await pending
  const detail=app.cache.fetchNote(note.id)
  const deletion=app.cache.deleteNoteFolder(folder)
  app.requests[2].resolve(note)
  await assert.rejects(detail,/删除/)
  app.requests[3].resolve({deleted:true});await deletion
  assert.equal(app.cache.cachedNoteFolders().length,0)
  assert.equal(app.cache.cachedNote(note.id),undefined)
  const next=app.cache.deleteNoteFolder({...folder,id:'another'})
  app.state.user={id:'bob'};app.state.token='bob-token'
  app.requests[4].reject(new Error('offline'));await assert.rejects(next)
  assert.equal(app.cache.cachedNoteFolders(),undefined)
  assert.equal(app.state.notesDeleteError,'')
})

test('folder confirmation opens synchronously and confirmed cards disappear before the request completes',async()=>{
  const app=fixture()
  let pending=app.cache.fetchNoteFolders();app.requests[0].resolve([folder]);await pending
  pending=app.cache.fetchNotes();app.requests[1].resolve([note]);await pending
  const {component}=page(app);await component.load()
  component.requestFolderDelete(folder)
  assert.equal(component.pendingFolderDelete.value.id,folder.id)
  const deletion=component.removeFolder()
  assert.equal(component.pendingFolderDelete.value,null)
  assert.equal(component.folders.value.length,0)
  assert.equal(component.cards.value.length,0)
  app.requests[2].resolve({deleted:true});await deletion
})
