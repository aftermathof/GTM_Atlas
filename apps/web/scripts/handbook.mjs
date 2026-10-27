import { readdir, readFile, mkdir, writeFile, unlink } from 'node:fs/promises'
import path from 'node:path'
const root = path.resolve('../../knowledge/learning')
await mkdir('handbook/articles', { recursive: true })
const oldFiles = JSON.parse(await readFile('handbook/.generated.json', 'utf8').catch(() => '[]'))
for (const file of oldFiles) {
  if (/^[\w-]+\.md$/.test(file)) await unlink(path.join('handbook/articles', file)).catch(() => {})
}
const links = []
const generated = []
async function files(directory) {
  const entries = await readdir(directory, {withFileTypes:true})
  const groups = await Promise.all(entries.filter(entry=>!entry.isSymbolicLink()).map(entry=>entry.isDirectory()?files(path.join(directory,entry.name)):[path.join(directory,entry.name)]))
  return groups.flat().filter(file=>file.endsWith('.md'))
}
for (const fullPath of await files(root)) {
  const content = await readFile(fullPath, 'utf8')
  if (!/^permission: public_display$/m.test(content)) continue
  const id = content.match(/^id: ([\w-]+)$/m)?.[1]
  if (!id) throw new Error('Knowledge document requires a safe unique id')
  const file = id+'.md'
  // Reuse the workbench's shared public images without importing a second asset copy.
  const page = content.replace(/!\[([^\]]*)\]\((\/xhs-author-assets\/[a-f0-9]{24}\.(?:webp|png|jpg))\)/g, (_, alt, src) => {
    const label = alt.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<img :src="'${src}'" alt="${label}" loading="lazy">`
  })
  await writeFile(path.join('handbook/articles', file), page)
  generated.push(file)
  const title = content.match(/^# (.+)$/m)?.[1] || file
  links.push(`- [${title}](./articles/${file.replace('.md', '')})`)
}
await writeFile('handbook/index.md', '# GTM 知识手册\n\n收录原创学习资料与用户提供的研究笔记，保留出处与阅读边界。\n\n' + links.join('\n'))
await writeFile('handbook/.generated.json', JSON.stringify(generated))
