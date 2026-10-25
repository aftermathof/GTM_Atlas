import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function confirmation(hash, response = { ok: true }) {
  const requests = [], navigations = []
  const { descriptor } = parse(readFileSync(new URL('../src/pages/EmailConfirmed.vue', import.meta.url), 'utf8'))
  const context = vm.createContext({ exports: {}, URLSearchParams, TypeError,
    fetch: async (url, options) => { requests.push({ url, options }); if(response instanceof Error) throw response; return response },
    require(name) {
      if(name==='vue') return { ...vue, onMounted() {} }
      if(name==='vue-router') return { useRoute:()=>({hash}), useRouter:()=>({replace:async target=>navigations.push(target)}) }
      if(name==='../state') return {API_ORIGIN:'https://api.example.test'}
      return {}
    }
  })
  const source = compileScript(descriptor, {id:'email-confirmation-test'}).content
  vm.runInContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context)
  return {component:context.exports.default.setup({}, {expose(){}}), requests, navigations}
}

test('verified signup checks the callback token without signing in and clears its URL fragment',async()=>{
  const app=confirmation('#access_token=signup-token&type=signup&refresh_token=private')
  await app.component.confirmEmail()
  assert.equal(app.component.status.value,'success')
  assert.equal(app.requests[0].options.headers.Authorization,'Bearer signup-token')
  assert.equal(app.navigations[0].path,'/auth/confirmed')
  assert.equal(app.navigations[0].hash,undefined)
})

test('missing expired or recovery links never show signup success',async()=>{
  for(const hash of ['', '#error=access_denied&error_code=otp_expired', '#access_token=reset&type=recovery']) {
    const app=confirmation(hash)
    await app.component.confirmEmail()
    assert.equal(app.component.status.value,'error')
    assert.equal(app.requests.length,0)
  }
})

test('invalid tokens and unavailable API cannot display successful verification',async()=>{
  for(const result of [{ok:false,status:401}, {ok:false,status:503}, new TypeError('Failed to fetch')]) {
    const app=confirmation('#access_token=invalid&type=signup',result)
    await app.component.confirmEmail()
    assert.equal(app.component.status.value,'error')
    assert.ok(app.component.message.value)
  }
})
