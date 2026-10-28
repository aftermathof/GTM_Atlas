import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

test('login stays standalone even after a signed-in session has been restored',()=>{
  const route=vue.reactive({path:'/login',query:{next:'/'}})
  const state=vue.reactive({user:{id:'restored-user'}})
  const context=vm.createContext({exports:{},require:name=>{
    if(name==='vue')return {...vue,onMounted(){},watch(){}}
    if(name==='vue-router')return {useRoute:()=>route}
    if(name==='./state')return {state,initialize(){}}
    if(name==='./preload')return {preloadWorkspace:async()=>{}}
    return {}
  }})
  const {descriptor}=parse(readFileSync(new URL('../src/App.vue',import.meta.url),'utf8'))
  vm.runInContext(ts.transpileModule(compileScript(descriptor,{id:'auth-layout-test'}).content,{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText,context)
  const app=context.exports.default.setup({}, {expose(){}})
  assert.equal(app.workspaceVisible.value,false)
  route.path='/auth/confirmed'
  assert.equal(app.workspaceVisible.value,false)
  for(const path of ['/','/learn','/notes']) {
    route.path=path
    assert.equal(app.workspaceVisible.value,true)
  }
  state.user=null
  assert.equal(app.workspaceVisible.value,false)
})

test('the shared account email field prompts the user to enter an email',()=>{
  const {descriptor}=parse(readFileSync(new URL('../src/pages/Utility.vue',import.meta.url),'utf8'))
  const input=descriptor.template.content.match(/<input[^>]*type="email"[^>]*>/)?.[0]
  assert.ok(input)
  assert.match(input,/placeholder="请输入邮箱"/)
})
