import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

test('overview warming shares one load and retains all five source pages in memory',async()=>{
  let calls=0
  const pages=Object.fromEntries(['index.html',...Array.from({length:4},(_,i)=>'chapter-0'+(i+1)+'.html')].map(name=>[name,readFileSync(new URL('../../../knowledge/site/gtm-overview/'+name,import.meta.url),'utf8')]))
  const context=vm.createContext({exports:{},require:name=>{assert.equal(name,'../../content/overview-pages');calls++;return {overviewPages:pages}}})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/features/knowledge/publicLearning.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context)
  const app=context.exports
  assert.equal(app.peekOverview(),undefined)
  await Promise.all([app.warmOverview(),app.warmOverview()])
  await app.warmOverview()
  assert.equal(calls,1)
  for(const [name,html] of Object.entries(pages)) assert.equal(app.peekOverview(name),html)
})
