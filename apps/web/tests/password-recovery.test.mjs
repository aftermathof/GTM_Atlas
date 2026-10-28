import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import {parse,compileScript,compileTemplate} from '@vue/compiler-sfc'
import * as vue from 'vue'

function recovery(options={}) {
  const requests=[], navigations=[], state={user:null,context:{}}
  let cleared=0
  const route={params:{page:'login'},query:options.query||{},hash:options.hash||''}
  const {descriptor}=parse(readFileSync(new URL('../src/pages/Utility.vue',import.meta.url),'utf8'))
  const context=vm.createContext({exports:{},URLSearchParams,require(name){
    if(name==='vue')return {...vue,onMounted(){},watch(){}}
    if(name==='vue-router')return {useRoute:()=>route,useRouter:()=>({push:async target=>navigations.push(target),replace:async target=>{navigations.push(target);route.hash=target.hash||''}})}
    if(name==='../state')return {state,clearSession(){cleared++},historyRecords:async()=>[],post:async(path,body)=>{requests.push({path,body});return options.post?options.post(path,body):{message:'操作成功'}},saveSession(){if(!options.login)throw new Error('recovery must not automatically sign in')}}
    return {}
  }})
  const source=compileScript(descriptor,{id:'password-recovery-test'}).content
  vm.runInContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context)
  return {component:context.exports.default.setup({},{expose(){}}),requests,navigations,state,get cleared(){return cleared}}
}

test('password visibility uses one persistent icon button and supports repeated toggles',()=>{
  const source=readFileSync(new URL('../src/pages/Utility.vue',import.meta.url),'utf8')
  const {descriptor}=parse(source)
  const field=descriptor.template.content.match(/<div class="auth-password">[\s\S]*?<\/div>/)[0]
  const compiled=compileTemplate({source:field,filename:'password-toggle.vue',id:'password-toggle-test'})
  const context=vm.createContext({exports:{},require:()=>({...vue,resolveComponent:name=>name,withDirectives:node=>node})})
  vm.runInContext(ts.transpileModule(compiled.code,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context)
  const c=recovery().component, ctx=vue.proxyRefs(c)
  c.password.value='keep-this-password'
  function nodes(node) { return [node,...(Array.isArray(node.children)?node.children.flatMap(child=>typeof child==='object'?nodes(child):[]):[])] }
  for(let index=0;index<8;index++){
    const tree=nodes(context.exports.render(ctx,[]))
    const button=tree.find(node=>node.type==='button'),input=tree.find(node=>node.type==='input')
    assert.ok(button)
    assert.equal(button.props.type,'button')
    assert.equal(button.props['aria-label'],index%2?'隐藏密码':'显示密码')
    assert.equal(input.props.type,index%2?'text':'password')
    assert.ok(tree.some(node=>node.type==='Eye' || node.type==='EyeOff'))
    assert.equal(tree.some(node=>typeof node.children==='string' && /^(显示|隐藏)$/.test(node.children)),false)
    button.props.onClick()
    assert.equal(c.password.value,'keep-this-password')
  }
  assert.match(descriptor.styles.map(style=>style.content).join('\n'),/::-ms-reveal/)
})

test('forgot password opens email-only recovery and sends no existing password',async()=>{
  const app=recovery(), c=app.component
  c.email.value='user@example.test';c.password.value='old-password';c.error.value='old-error'
  c.forgotPassword()
  assert.equal(c.recovering.value,true)
  assert.equal(c.password.value,'')
  assert.equal(c.error.value,'')
  await c.requestRecovery()
  assert.equal(app.requests[0].path,'/auth/request-password-reset')
  assert.equal(JSON.stringify(app.requests[0].body),'{"email":"user@example.test"}')
  assert.equal(c.success.value,'操作成功')
})

test('successful login always opens home even when redirected from settings',async()=>{
  const app=recovery({login:true,query:{next:'/settings'},post:async()=>({token:'access',user:{id:'user',preferences:{}}})})
  await app.component.auth()
  assert.equal(app.component.error.value,'')
  assert.equal(app.navigations[0],'/')
})

test('recovery callback keeps its token only in the form and removes the URL fragment',async()=>{
  const app=recovery({hash:'#access_token=temporary-recovery&type=recovery&refresh_token=temporary-refresh'})
  await app.component.readRecoveryLink()
  assert.equal(app.component.resetting.value,true)
  assert.equal(app.component.recoveryToken.value,'temporary-recovery')
  assert.equal(app.navigations[0].path,'/login')
  assert.equal(app.navigations[0].hash,undefined)
  assert.equal(app.state.user,null)
})

test('reset requires matching passwords and returns to login after success',async()=>{
  const app=recovery({hash:'#access_token=temporary&type=recovery'}),c=app.component
  await c.readRecoveryLink()
  c.password.value='new';c.confirmPassword.value='different'
  await c.resetPassword()
  assert.equal(app.requests.length,0)
  assert.match(c.error.value,/不一致/)
  c.confirmPassword.value='new'
  await c.resetPassword()
  assert.equal(app.requests[0].path,'/auth/reset-password')
  assert.equal(app.requests[0].body.recovery_token,'temporary')
  assert.equal(app.requests[0].body.password,'new')
  assert.equal(c.resetting.value,false)
  assert.equal(c.recoveryToken.value,'')
  assert.equal(c.password.value,'')
  assert.equal(app.cleared,1)
})

test('failed email delivery reports the error and retains the email for retry',async()=>{
  const app=recovery({post:async()=>{throw new Error('发送频率过高')}}),c=app.component
  c.email.value='user@example.test';c.forgotPassword()
  await c.requestRecovery()
  assert.equal(c.email.value,'user@example.test')
  assert.equal(c.busy.value,false)
  assert.match(c.error.value,/频率/)
})

test('switching account forms hides and clears passwords but preserves the email',()=>{
  const c=recovery().component
  c.email.value='user@example.test';c.password.value='private-password';c.showPassword.value=true
  c.error.value='previous error';c.success.value='previous success'
  c.toggleAuth()
  assert.equal(c.register.value,true)
  assert.equal(c.password.value,'')
  assert.equal(c.showPassword.value,false)
  assert.equal(c.email.value,'user@example.test')
  assert.equal(c.error.value,'')
  assert.equal(c.success.value,'')
})

test('returning from password recovery clears password visibility and confirmation',()=>{
  const c=recovery().component
  c.resetting.value=true;c.showPassword.value=true;c.password.value='private-password';c.confirmPassword.value='private-password'
  c.returnToLogin()
  assert.equal(c.authStep.value,'login')
  assert.equal(c.showPassword.value,false)
  assert.equal(c.password.value,'')
  assert.equal(c.confirmPassword.value,'')
})
