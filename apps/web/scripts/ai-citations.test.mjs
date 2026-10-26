import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import { Marked } from 'marked'
import * as vue from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

function helpers() {
  const source = readFileSync(new URL('../src/aiCitations.ts', import.meta.url), 'utf8')
  const context = { exports: {}, URL }
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context)
  return context.exports
}

const citations = [
  { chunk_id: 'note-a:0', doc_id: 'a', title: '渠道笔记', heading_path: '渠道选择', url: '/notes/a' },
  { chunk_id: 'guide-b:2', doc_id: 'b', title: '上市指南', heading_path: '上市准备', url: '/learn/b?kind=learning' },
  { chunk_id: 'note-a:3', doc_id: 'a', title: '渠道笔记', heading_path: '执行检查', url: '/notes/a' },
]

test('source list groups chunks by file and keeps existing citation order', () => {
  const { citationSources } = helpers()
  assert.deepEqual(Array.from(citationSources(citations), c => [c.number, c.title]), [[1, '渠道笔记'], [2, '上市指南']])
  assert.equal(citationSources([]).length, 0)
  assert.equal(citationSources([citations[1]])[0].number, 1)
})

test('inline numbers match the list and retain each chunk chapter at its sentence', () => {
  const { citationExtension, citationHref } = helpers()
  const parser = new Marked({ extensions: [citationExtension(citations)] })
  const html = parser.parse('先准备上市。[guide-b:2] 再检查渠道。[note-a:3] 继续跟进。[note-a:0]')
  assert.deepEqual([...html.matchAll(/class="inline-citation"[^>]*>(\d+)<\/a>/g)].map(m => m[1]), ['2', '1', '1'])
  assert.match(html, /先准备上市。<a /)
  assert.match(html, /title="渠道笔记 · 执行检查"/)
  assert.match(html, /heading=%E6%89%A7%E8%A1%8C%E6%A3%80%E6%9F%A5/)
  assert.equal(citationHref(citations[1]), '/learn/b?kind=learning&heading=%E4%B8%8A%E5%B8%82%E5%87%86%E5%A4%87')
})

test('unknown markers disappear while ordinary links, numbers and code remain intact', () => {
  const { citationExtension } = helpers()
  const parser = new Marked({ extensions: [citationExtension(citations)] })
  const html = parser.parse('[missing:0] [note-a:0](/wrong) [官网](https://example.com) [1]\n\n\x60[note-a:0]\x60\n\n\x60\x60\x60text\n[note-a:0]\n\x60\x60\x60')
  assert.ok(!html.includes('missing:0'))
  assert.ok(!html.includes('/wrong'))
  assert.equal((html.match(/class="inline-citation"/g) || []).length, 1)
  assert.match(html, /href="https:\/\/example.com"/)
  assert.match(html, /\[1\]/)
  assert.match(html, /<code>\[note-a:0\]<\/code>/)
  assert.match(html, /<code class="language-text">\[note-a:0\]/)
})

test('source metadata is escaped and nonlocal links cannot become citations', () => {
  const { citationExtension, citationSources, citationHref } = helpers()
  for (const url of ['javascript:alert(1)', '//evil.test/a', '/\\evil.test/a', 'https://evil.test/a']) {
    const citation = { ...citations[0], url }
    assert.equal(citationHref(citation), '')
    assert.equal(citationSources([citation]).length, 0)
    assert.ok(!new Marked({ extensions: [citationExtension([citation])] }).parse('[note-a:0]').includes('<a'))
  }
  const html = new Marked({ extensions: [citationExtension([{ ...citations[0], title: '\"><img src=x onerror=alert(1)>' }])] }).parse('[note-a:0]')
  assert.ok(!html.includes('<img'))
  assert.match(html, /&quot;&gt;&lt;img/)
})

function markdown(props) {
  const { descriptor } = parse(readFileSync(new URL('../src/components/Markdown.vue', import.meta.url), 'utf8'))
  const navigation = []
  const sanitized = []
  const context = { exports: {}, require: name => {
    if (name === 'vue') return { ...vue, onMounted() {}, onUpdated() {} }
    if (name === 'vue-router') return { useRouter: () => ({ push: url => navigation.push(url) }) }
    if (name === 'marked') return { Marked }
    if (name === 'dompurify') return { default: { sanitize: html => { sanitized.push(html); return html } } }
    if (name === '../aiCitations') return helpers()
    throw new Error('Unexpected import: ' + name)
  } }
  vm.runInNewContext(ts.transpileModule(compileScript(descriptor, { id: 'markdown-citations-test' }).content, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context)
  return { component: context.exports.default.setup(props, { expose() {} }), navigation, sanitized }
}

test('Markdown renders citations through sanitization and keeps ordinary article text unchanged', () => {
  const { component, sanitized } = markdown({ ai: true, source: '先检查渠道。[note-a:3]', citations })
  assert.match(component.html.value, /先检查渠道。<a class="inline-citation"/)
  assert.match(component.html.value, />1<\/a>/)
  assert.equal(sanitized.length, 1)
  const article = markdown({ source: '原文 [note-a:0]', ai: false, citations })
  assert.ok(!article.component.html.value.includes('inline-citation'))
  assert.match(article.component.html.value, /\[note-a:0\]/)
})

test('citation clicks navigate internally and modified clicks keep normal browser behavior', () => {
  const { component, navigation } = markdown({ ai: true, source: '', citations })
  const href = helpers().citationHref(citations[2])
  const link = { getAttribute: name => name === 'href' ? href : null }
  component.host.value = { contains: element => element === link }
  let prevented = 0
  const event = { button: 0, target: { closest: () => link }, preventDefault: () => prevented++ }
  component.followCitation(event)
  assert.deepEqual(navigation, [href])
  assert.equal(prevented, 1)
  for (const modifier of ['ctrlKey', 'metaKey', 'shiftKey', 'altKey']) component.followCitation({ ...event, [modifier]: true })
  component.followCitation({ ...event, button: 1 })
  component.followCitation({ ...event, target: { closest: () => null } })
  assert.deepEqual(navigation, [href])
  assert.equal(prevented, 1)
})
