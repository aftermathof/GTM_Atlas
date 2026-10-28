let pages: Record<string, string> | undefined
let pending: Promise<void> | undefined

export function peekOverview(page = 'index.html') { return pages?.[page] }
export function warmOverview() {
  if (pages) return Promise.resolve()
  if (!pending) pending = import('../../content/overview-pages').then(module => { pages = module.overviewPages }).finally(() => { pending = undefined })
  return pending
}
