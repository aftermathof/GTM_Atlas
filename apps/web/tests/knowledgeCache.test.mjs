import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
const source=await readFile(new URL('../src/state.ts',import.meta.url),'utf8')
const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText
async function setup(){
  let clock=1000
  class Clock extends Date{static now(){return clock}}
  const storage=()=>{const values=new Map();return {getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,String(value)),removeItem:key=>values.delete(key)}}
  const localStorage=storage(),sessionStorage=storage(),listeners={},calls=[]
  const context=vm.createContext({Date:Clock,Headers,FormData,URLSearchParams,localStorage,sessionStorage,crypto:{randomUUID:()=>String(clock++)},window:{addEventListener:(name,fn)=>listeners[name]=fn},fetch:async(url,options={})=>{
    calls.push({url,method:options.method||'GET'})
    const parsed=new URL(url,'http://fixture.test')
    let value={ok:true}
    if(parsed.pathname==='/api/v1/knowledge/preload')value={items:[{id:'article',title:'Article',body:'Cached body',meta:{kind:'learning'}}]}
    else if(parsed.pathname==='/api/v1/knowledge/capabilities')value={can_manage_learning:true}
    else if(parsed.pathname.endsWith('/documents/article'))value={id:'article',title:'Article',body:'Cached body',meta:{kind:'learning'},sha256:'hash'}
    else if(parsed.pathname==='/api/v1/knowledge/documents'){
      const offset=Number(parsed.searchParams.get('offset')||0),limit=Number(parsed.searchParams.get('limit')||100)
      value={total:201,items:Array.from({length:Math.min(limit,201-offset)},(_,i)=>({id:'doc'+(offset+i)}))}
    }
    return new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}})
  }})
  const vue=new vm.SyntheticModule(['reactive'],function(){this.setExport('reactive',value=>value)},{context})
  const module=new vm.SourceTextModule(code,{context,initializeImportMeta:meta=>{meta.env={}}})
  await module.link(name=>{assert.equal(name,'vue');return vue});await module.evaluate()
  return {api:module.namespace,calls,advance:()=>clock+=86400000,localStorage,listeners}
}
test('learning, interviews, JD and article bodies remain cached beyond 30 seconds',async()=>{
  const {api,calls,advance}=await setup()
  for(const kind of ['learning','interview','jd'])await api.knowledgeDocuments('limit=100&kind='+kind)
  await api.knowledgeDocument('article');advance()
  for(const kind of ['learning','interview','jd'])await api.knowledgeDocuments('limit=100&kind='+kind)
  await api.knowledgeDocument('article')
  assert.equal(calls.length,4)
  assert.equal(api.peekKnowledge('/knowledge/documents/article').body,'Cached body')
})
test('complete catalog is synchronously available only after all pages are cached',async()=>{
  const {api}=await setup();const query='limit=100&q=&role=gtm&industry='
  await api.knowledgeDocuments(query)
  assert.equal(api.peekKnowledgeDocuments(query),undefined)
  await api.knowledgeDocuments(query+'&offset=100')
  assert.equal(api.peekKnowledgeDocuments(query),undefined)
  await api.knowledgeDocuments(query+'&offset=200')
  assert.equal(api.peekKnowledgeDocuments(query).length,201)
  assert.equal(api.peekKnowledge('/knowledge/documents?'+query).items.length,100)
})
test('preloaded article bodies do not expire while navigating',async()=>{
  const {api,calls,advance}=await setup();await api.preloadDocuments();advance()
  assert.equal(api.peekKnowledge('/knowledge/documents/article').body,'Cached body')
  await api.knowledgeDocument('article');assert.equal(calls.length,1)
})
test('editing and deleting invalidate content, lists and permissions',async()=>{
  const {api,calls}=await setup();const query='limit=100&kind=learning'
  await api.knowledgeDocuments(query);await api.knowledgeDocument('article');await api.knowledgeCapabilities()
  await api.editKnowledgeDocument('article',{title:'Changed',body:'Changed body',excerpt:'Changed summary',expected_sha256:'hash'})
  assert.equal(api.peekKnowledge('/knowledge/documents?'+query),undefined)
  assert.equal(api.peekKnowledge('/knowledge/documents/article'),undefined)
  await api.knowledgeDocuments(query);await api.deleteKnowledgeDocument('article','hash')
  assert.equal(api.peekKnowledge('/knowledge/documents?'+query),undefined)
  assert.equal(api.state.knowledgeRevision,2)
  assert.equal(calls.filter(x=>x.method==='PUT').length,1)
  assert.equal(calls.filter(x=>x.method==='DELETE').length,1)
})
test('account changes and another tab knowledge edit invalidate cache',async()=>{
  const {api,calls,listeners,localStorage}=await setup();await api.knowledgeDocument('article')
  listeners.storage({storageArea:localStorage,key:'atlas-knowledge-revision',newValue:'changed'})
  assert.equal(api.peekKnowledge('/knowledge/documents/article'),undefined)
  await api.knowledgeDocument('article');api.saveSession({token:'different-account'})
  assert.equal(api.peekKnowledge('/knowledge/documents/article'),undefined)
  await api.knowledgeDocument('article');api.clearSession()
  assert.equal(api.peekKnowledge('/knowledge/documents/article'),undefined)
  assert.equal(calls.length,3)
})
