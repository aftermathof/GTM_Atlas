import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'

function helpers() {
  const context = vm.createContext({exports:{}, TextDecoder, Error})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/features/ai/streaming.ts', import.meta.url), 'utf8'), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText, context)
  return context.exports
}
function response(parts) {
  const encoder = new TextEncoder()
  return new Response(new ReadableStream({start(controller) {
    for (const part of parts) controller.enqueue(typeof part==='string'?encoder.encode(part):part)
    controller.close()
  }}), {headers:{'Content-Type':'text/event-stream'}})
}
const event = value => 'data: ' + JSON.stringify(value) + '\r\n\r\n'

test('stream parser handles split UTF-8, SSE frames, sources and final validated result', async () => {
  const bytes = new TextEncoder().encode(': heartbeat\r\n\r\n'+event({type:'sources',citations:[{chunk_id:'note:0'}]})+event({type:'start',label:'正在回答',model:'test'})+event({type:'delta',text:'你好'})+event({type:'delta',text:'，继续'})+event({type:'result',value:{answer:'已校验',conversation_id:'one'}}))
  const parts = Array.from(bytes, byte => Uint8Array.of(byte)), updates=[]
  const final = await helpers().readAIStream(response(parts), progress => updates.push(progress))
  assert.equal(final.answer, '已校验')
  assert.equal(updates.at(-1).text, '你好，继续')
  assert.equal(updates.at(-1).citations[0].chunk_id, 'note:0')
})

test('partial output without final result and explicit errors reject instead of succeeding', async () => {
  let partial=''
  await assert.rejects(helpers().readAIStream(response([event({type:'delta',text:'部分'})]), p=>partial=p.text), /中断|未完成/)
  assert.equal(partial, '部分')
  await assert.rejects(helpers().readAIStream(response([event({type:'error',detail:'模型未返回完整正文',status:502})]), ()=>{}), /完整正文/)
})

test('a citation split across deltas does not expose its unfinished internal identifier', async()=>{
  const updates=[]
  await helpers().readAIStream(response([
    event({type:'sources',citations:[{chunk_id:'note-private:0'}]}),
    event({type:'delta',text:'答案[note-'}),event({type:'delta',text:'private:0]'}),
    event({type:'result',value:{answer:'答案[note-private:0]'}}),
  ]), progress=>updates.push(progress.text))
  assert.equal(updates.at(-2),'答案')
  assert.equal(updates.at(-1),'答案[note-private:0]')
})

test('new generations reset rejected previews, while replacements preserve the latest text', async () => {
  const updates=[]
  await helpers().readAIStream(response([
    event({type:'start',label:'改写'}),event({type:'delta',text:'旧稿'}),
    event({type:'start',label:'改写'}),event({type:'delta',text:'新稿'}),
    event({type:'replace',text:'校正后的预览'}),event({type:'result',value:{text:'最终稿'}}),
  ]), progress=>updates.push(progress))
  assert.equal(updates.at(-1).text,'校正后的预览')
  assert.equal(updates.at(-3).text,'')
})

test('text arrives before the result, rather than being replayed after completion', async () => {
  const encoder=new TextEncoder()
  let controller, received=false
  const body=new ReadableStream({start(value){controller=value}})
  const pending=helpers().readAIStream(new Response(body), progress=>{
    if(progress.text==='先显示'){
      received=true
      controller.enqueue(encoder.encode(event({type:'result',value:{answer:'完成'}})))
      controller.close()
    }
  })
  controller.enqueue(encoder.encode(event({type:'delta',text:'先显示'})))
  assert.equal((await pending).answer,'完成')
  assert.equal(received,true)
})
