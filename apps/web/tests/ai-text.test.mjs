import assert from 'node:assert/strict'
import {test} from 'node:test'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
import vm from 'node:vm'
test('AI display hides internal source IDs and keeps normal links and numbers',()=>{
  const source=readFileSync(new URL('../src/features/ai/aiText.ts',import.meta.url),'utf8')
  const context={exports:{}}
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context)
  const clean=context.exports.cleanAIText
  assert.equal(clean('建议 [note-4f477ec9-7f18-46e6-b3c1-b58264acbd1f:0]。'),'建议 。')
  assert.equal(clean('[jd-channel:12] [note-abc:1](/notes/abc)'), ' ')
  assert.equal(clean('[官网](https://example.com) [1] 4P'), '[官网](https://example.com) [1] 4P')
})
