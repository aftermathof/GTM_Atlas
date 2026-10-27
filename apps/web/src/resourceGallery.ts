export type ResourceCard = {
  id: string
  title: string
  kind: string
  meta: Record<string, any>
  excerpt?: string
  private?: boolean
  folder?: boolean
  postCount?: number
}

export function cardPage<T>(items: T[], requested: unknown) {
  const pages = Math.max(1, Math.ceil(items.length / 9))
  const value = Number(requested)
  const page = Math.min(pages, Math.max(1, Number.isFinite(value) ? Math.floor(value) : 1))
  return { page, pages, total: items.length, items: items.slice((page - 1) * 9, page * 9) }
}

export function galleryCards(items: ResourceCard[]): ResourceCard[] {
  const folders = new Map<string, ResourceCard>()
  const cards: ResourceCard[] = []
  for (const item of items) {
    const key = item.kind === 'learning' && item.meta.author_collection_id
    if (!key) { cards.push(item); continue }
    let folder = folders.get(key)
    if (!folder) {
      folder = {
        id: 'collection:' + key, title: item.meta.author_collection_title || item.meta.source_author,
        kind: 'learning', folder: true, postCount: 0,
        meta: { author_collection_id: key, source_author: item.meta.source_author, tags: [] },
        excerpt: '打开博主合集，按原帖时间从旧到新阅读。',
      }
      folders.set(key, folder); cards.push(folder)
    }
    folder.postCount!++
  }
  return cards
}

function postTime(item: ResourceCard) {
  const published = item.meta.published_at || item.meta.source_published_at
  const explicit = published && Date.parse(String(published))
  if (Number.isFinite(explicit)) return Number(explicit)
  const source = item.meta.source_id || String(item.meta.source_url || '').split(/[?#]/)[0].split('/').pop()
  // XHS IDs carry the creation sequence; do not invent a year for displayed edit dates.
  if (/^[a-f0-9]{24}$/i.test(source || '')) return parseInt(source.slice(0, 8), 16) * 1000
  const date = String(item.meta.displayed_date || '').match(/\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b/)
  return date ? Date.UTC(Number(date[1]), Number(date[2]) - 1, Number(date[3])) : Infinity
}

export function oldestFirst(items: ResourceCard[]) {
  return [...items].sort((a, b) => postTime(a) - postTime(b) || a.id.localeCompare(b.id, 'zh-CN', { numeric: true }))
}
