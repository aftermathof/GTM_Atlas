import type { TokenizerAndRendererExtension } from 'marked'

export type Citation = {
  chunk_id: string
  doc_id?: string
  title: string
  heading_path?: string
  url: string
}

export function citationHref(citation: Citation): string {
  if (!/^\/(?![\/\\])/.test(citation.url) || /[\\\u0000-\u0020]/.test(citation.url)) return ''
  const url = new URL(citation.url, 'https://gtm.local')
  if (citation.heading_path) url.searchParams.set('heading', citation.heading_path)
  return url.pathname + url.search + url.hash
}

export function citationSources(citations: Citation[] = []) {
  const seen = new Set<string>()
  return citations.flatMap(citation => {
    const href = citationHref(citation)
    const key = citation.doc_id || citation.url.split(/[?#]/)[0]
    if (!href || seen.has(key)) return []
    seen.add(key)
    return [{ ...citation, key, href, number: seen.size }]
  })
}

function escapeAttribute(text: string): string {
  return text.replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)
}

export function citationExtension(citations: Citation[] = []): TokenizerAndRendererExtension {
  const sources = citationSources(citations)
  const links = new Map(citations.map(citation => {
    const key = citation.doc_id || citation.url.split(/[?#]/)[0]
    return [citation.chunk_id, { citation, number: sources.find(source => source.key === key)?.number }]
  }))
  return {
    name: 'inlineCitation',
    level: 'inline',
    start: text => text.indexOf('['),
    tokenizer(text) {
      const match = /^\[([\w-]+:\d+)\](?:\([^\s)]*\))?/.exec(text)
      if (match) return { type: 'inlineCitation', raw: match[0], chunkId: match[1] }
    },
    renderer(token) {
      const link = links.get(token.chunkId)
      if (!link?.number) return ''
      const href = citationHref(link.citation)
      if (!href) return ''
      const title = [link.citation.title, link.citation.heading_path].filter(Boolean).join(' · ')
      return `<a class="inline-citation" href="${escapeAttribute(href)}" title="${escapeAttribute(title)}" aria-label="${escapeAttribute('引用 ' + link.number + '：' + title)}">${link.number}</a>`
    },
  }
}
