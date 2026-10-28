import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'

function loader({count=7, failure=false, stop=false, records=[], chats=[],chatWait}={}) {
  const state={user:{id:'alice'},token:'alice-token'}
  const calls=[], pages=[]
  let active=0, peak=0
  const warm=async id=>{
    calls.push(id);peak=Math.max(peak,++active)
    if(stop){state.user=null;state.token=''}
    await new Promise(done=>setTimeout(done,0));active--
    if(id==='d0')throw new Error('temporary failure')
  }
  const context=vm.createContext({exports:{},Promise,require:name=> name==='./state'?{
    state,preloadHistory:async()=>records,preloadDocuments:async()=>{if(failure)throw new Error('unavailable');await warm('bulk-documents')},api:async path=>{if(path==='/ai/conversations'){await chatWait;return chats}return warm('history:'+path)},peekHistory:()=>undefined,peekKnowledge:()=>undefined,knowledgeDocument:warm,knowledgeDocuments:async query=>{
      if(failure)throw new Error('catalog unavailable')
      const params=new URLSearchParams(query),offset=Number(params.get('offset')||0)
      pages.push(offset)
      return {total:count,items:Array.from({length:Math.min(100,count-offset)},(_,i)=>({id:'d'+(offset+i)}))}
    }
  }:name==='./features/notes/notesStore'?{cachedNotes:()=>undefined,cachedNote:()=>undefined,fetchNotes:async()=>[{id:'n0'},{id:'n1'}],fetchNote:warm}:{warmOverview:async()=>{}}})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/preload.ts',import.meta.url),'utf8'),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText,context)
  return {load:context.exports.preloadWorkspace,warm:context.exports.warmDocument,state,calls,pages,get peak(){return peak}}
}

test('a slow chat list does not block document or note preloading',async()=>{
  let release
  const app=loader({chatWait:new Promise(resolve=>{release=resolve})})
  const pending=app.load()
  await new Promise(resolve=>setTimeout(resolve,10))
  assert.ok(app.calls.includes('bulk-documents'))
  assert.ok(app.calls.includes('n0'))
  release()
  await pending
})
test('background preloading covers all pages and own notes, shares runs and limits concurrency',async()=>{
  const app=loader({count:105})
  await Promise.all([app.load(),app.load()])
  assert.deepEqual(app.pages,[0,100])
  assert.deepEqual([...app.calls].sort(),['bulk-documents','n0','n1'])
  assert.ok(app.peak<=3)
})
test('switching accounts stops queued private and public preloads',async()=>{
  const app=loader({stop:true})
  await app.load()
  assert.ok(app.calls.length<=3)
})
test('notes still preload when the public catalog is unavailable',async()=>{
  const app=loader({failure:true})
  await app.load()
  assert.deepEqual(app.calls,['n0','n1'])
})

test('hover warming and token rotations share one global concurrency limit',async()=>{
  const app=loader()
  const old=Array.from({length:3},(_,i)=>app.warm('old'+i))
  await Promise.resolve()
  app.state.token='new-token'
  const next=Array.from({length:5},(_,i)=>app.warm('next'+i,true))
  await Promise.all([...old,...next])
  assert.equal(app.calls.length,8)
  assert.ok(app.peak<=3)
})
test('hovered cards move ahead of background jobs still waiting for a slot',async()=>{
  const app=loader()
  const first=Array.from({length:3},(_,i)=>app.warm('first'+i))
  await Promise.resolve()
  const queued=app.warm('background'), hovered=app.warm('hover',true)
  await Promise.all([...first,queued,hovered])
  assert.equal(app.calls[3],'hover')
})

test('history metadata warms unique chats, Mock reviews and resume version lists',async()=>{
  const app=loader({count:0,records:[{id:'c',kind:'chat_thread'},{id:'m',kind:'mock'},{id:'r',kind:'career'}],chats:[{id:'c'}]})
  await app.load()
  assert.equal(app.calls.filter(path=>path==='history:/ai/conversations/c').length,1)
  for(const path of ['/career/sessions/r','/career/sessions/r/versions']) assert.ok(app.calls.includes('history:'+path))
  assert.ok(!app.calls.includes('history:/mock/sessions/m/report'))
  assert.ok(app.peak<=3)
})
