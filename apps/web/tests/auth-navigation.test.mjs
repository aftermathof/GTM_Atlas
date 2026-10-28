import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function gate(user = null, restore = async () => {}) {
  const state = { user }, redirects = []
  let before, changed
  const router = { beforeEach(callback) { before = callback }, currentRoute: { value: { path:'/career/editor/test', fullPath:'/career/editor/test' } }, replace: target => redirects.push(target) }
  const context = vm.createContext({exports:{}, URLSearchParams, require(name) {
    if (name==='vue') return {watch: (source, callback) => { changed = callback }}
    if (name==='../../state') return {state, restoreSession: () => restore(state)}
    return {}
  }})
  const source=readFileSync(new URL('../src/features/auth/authNavigation.ts',import.meta.url),'utf8')
  vm.runInContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context)
  context.exports.installAuthGuard(router)
  return { state, redirects, navigate: path => before({path:path.split(/[?#]/)[0],fullPath:path,hash:path.includes('#')?'#'+path.split('#')[1]:''}), logout:()=>changed(null) }
}

test('logged-out visitors can only open login and retain the intended destination', async()=>{
  const app=gate()
  assert.equal(await app.navigate('/login'), true)
  for(const path of ['/','/learn','/glossary','/search','/interviews','/career','/history','/settings','/learn?kind=jd']) {
    const result=await app.navigate(path)
    assert.equal(result.path,'/login')
    assert.equal(result.query.next,path)
  }
})

test('valid saved sessions finish restoration before permitting protected navigation',async()=>{
  let finish
  const app=gate(null,state=>new Promise(resolve=>{finish=()=>{state.user={id:'user'};resolve()}}))
  let completed=false
  const pending=app.navigate('/career').then(result=>{completed=true;return result})
  await Promise.resolve()
  assert.equal(completed,false)
  finish()
  assert.equal(await pending,true)
})

test('signed-in navigation does not repeatedly validate the profile',async()=>{
  const app=gate({id:'user'},()=>{throw new Error('unexpected restore')})
  assert.equal(await app.navigate('/history'),true)
})

test('logging out leaves the active private page immediately',()=>{
  const app=gate({id:'user'})
  app.state.user=null;app.logout()
  assert.equal(app.redirects.length,1)
  assert.equal(app.redirects[0].path,'/login')
})


test('Supabase recovery landing links reach login without losing the recovery fragment',async()=>{
  const app=gate()
  const hash='#access_token=recovery-token&type=recovery'
  const result=await app.navigate('/'+hash)
  assert.equal(result.path,'/login')
  assert.equal(result.hash,hash)
  assert.equal(result.query.next,undefined)
})

test('signup callbacks open the standalone confirmation page even when landing on login',async()=>{
  const app=gate()
  const hash='#access_token=signup-token&type=signup'
  for(const path of ['/', '/login']) {
    const result=await app.navigate(path+hash)
    assert.equal(result.path,'/auth/confirmed')
    assert.equal(result.hash,hash)
  }
  assert.equal(await app.navigate('/auth/confirmed'),true)
})

test('failed verification callbacks reach confirmation without exposing tokens in next',async()=>{
  const result=await gate().navigate('/#error=access_denied&error_code=otp_expired')
  assert.equal(result.path,'/auth/confirmed')
  assert.equal(result.query.next,undefined)
})
