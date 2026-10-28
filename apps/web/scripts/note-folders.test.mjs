import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'
import ts from 'typescript'

test('each folder and root restart numbering and retain order across updates and pages', () => {
  const context = vm.createContext({exports:{}, Map})
  vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/noteFolders.ts', import.meta.url), 'utf8'), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText, context)
  const { folderNotes, noteNumbers } = context.exports
  const cards = [
    {id:'b',folder_id:'a',created_at:'2026-10-02',updated_at:'2026-10-05'},
    {id:'root',created_at:'2026-10-01'},
    {id:'a',folder_id:'a',created_at:'2026-10-01'},
    {id:'other',folder_id:'b',created_at:'2026-10-03'},
  ]
  assert.equal(folderNotes(cards, '').length, 1)
  assert.equal(folderNotes(cards, 'a').length, 2)
  assert.equal(folderNotes(cards, 'empty').length, 0)
  assert.equal(noteNumbers(folderNotes(cards, '')).get('root'), 'N01')
  assert.equal(noteNumbers(folderNotes(cards, 'a')).get('a'), 'N01')
  assert.equal(noteNumbers(folderNotes(cards, 'a')).get('b'), 'N02')
  assert.equal(noteNumbers(folderNotes(cards, 'b')).get('other'), 'N01')
  const many = Array.from({length:12}, (_, index) => ({id:String(index), folder_id:'a', created_at:`2026-10-${String(index + 1).padStart(2, '0')}`}))
  const numbered = noteNumbers(folderNotes([...many].reverse(), 'a'))
  assert.equal(numbered.get('9'), 'N10')
  assert.equal(numbered.get('11'), 'N12')
  assert.equal(noteNumbers(folderNotes([...cards].reverse(), 'a')).get('a'), 'N01')
})
