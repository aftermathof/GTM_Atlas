import { api, historyRecords, knowledgeDocuments, knowledgeDocument, peekKnowledge, peekHistory, state } from './state'
import { cachedNotes, cachedNote, fetchNotes, fetchNote } from './notesStore'
import { warmOverview } from './publicLearning'

let activeKey = '', activeRun: Promise<void> | undefined
function accountKey() { return state.user?.id && state.token ? state.user.id + ':' + state.token : '' }

type Job = { key:string; run:()=>Promise<unknown>; valid:()=>boolean; done:()=>void; pending:Promise<void> }
const queue: Job[] = [], scheduled = new Map<string, Job>()
let inFlight = 0
function drain() {
  while (inFlight < 3 && queue.length) {
    const job = queue.shift()!
    if (!job.valid()) { scheduled.delete(job.key); job.done(); continue }
    inFlight++
    void Promise.resolve().then(() => job.valid() ? job.run() : undefined).catch(() => {}).finally(() => {
      inFlight--; scheduled.delete(job.key); job.done(); drain()
    })
  }
}
function schedule(kind: string, id: string, run: ()=>Promise<unknown>, priority: boolean) {
  const account = accountKey()
  if (!account) return Promise.resolve()
  const key = account + ':' + kind + ':' + id
  const existing = scheduled.get(key)
  if (existing) {
    const index = queue.indexOf(existing)
    if (priority && index >= 0) { queue.splice(index, 1); queue.unshift(existing) }
    return existing.pending
  }
  let done!: ()=>void
  const pending = new Promise<void>(resolve => { done = resolve })
  const job = {key, run, pending, done, valid:()=>accountKey() === account}
  scheduled.set(key, job)
  if (priority) queue.unshift(job)
  else queue.push(job)
  drain()
  return pending
}
export function warmDocument(id: string, priority = false) {
  if (peekKnowledge('/knowledge/documents/' + encodeURIComponent(id))) return Promise.resolve()
  return schedule('document', id, () => knowledgeDocument(id), priority)
}
export function warmNote(id: string, priority = false) {
  if (cachedNote(id)) return Promise.resolve()
  return schedule('note', id, () => fetchNote(id), priority)
}
export function warmHistory(path: string, priority = false) {
  if (peekHistory(path)) return Promise.resolve()
  return schedule('history', path, () => api(path), priority)
}

export function preloadWorkspace() {
  const key = accountKey()
  if (!key) return Promise.resolve()
  if (key === activeKey && activeRun) return activeRun
  activeKey = key
  const current = () => accountKey() === key
  activeRun = (async () => {
    const role = state.context?.role || '', industry = state.context?.industry || ''
    if (role || industry) {
      void knowledgeDocuments('limit=100&q=&role=' + encodeURIComponent(role) + '&industry=' + encodeURIComponent(industry)).catch(() => {})
    }
    const catalog = async () => {
      const ids: string[] = []
      let offset = 0
      while (current()) {
        const page = await knowledgeDocuments('limit=100&q=&role=&industry=' + (offset ? '&offset=' + offset : ''))
        if (!current()) break
        ids.push(...page.items.map((item: {id:string}) => item.id))
        offset += page.items.length
        if (!page.items.length || offset >= page.total) break
      }
      return ids
    }
    const [documents, notes, records, chats] = await Promise.allSettled([
      catalog(), cachedNotes() || fetchNotes(), historyRecords(), api('/ai/conversations'),
    ])
    if (!current()) return
    const paths = new Set<string>()
    if (chats.status === 'fulfilled') for (const chat of chats.value) paths.add('/ai/conversations/' + chat.id)
    if (records.status === 'fulfilled') for (const record of records.value) {
      if (record.kind === 'chat_thread' || record.kind === 'conversation') paths.add('/ai/conversations/' + record.id)
      if (record.kind === 'mock') {
        paths.add('/mock/sessions/' + record.id); paths.add('/mock/sessions/' + record.id + '/report')
      }
      if (record.kind === 'career') {
        paths.add('/career/sessions/' + record.id); paths.add('/career/sessions/' + record.id + '/versions')
      }
    }
    const jobs: (() => Promise<unknown>)[] = [
      () => schedule('overview', 'all', warmOverview, false),
      ...(notes.status === 'fulfilled' ? notes.value.map(note => () => warmNote(note.id)) : []),
      ...[...paths].map(path => () => warmHistory(path)),
      ...(documents.status === 'fulfilled' ? [...new Set(documents.value)].map(id => () => warmDocument(id)) : []),
    ]
    let cursor = 0
    await Promise.all(Array.from({length:3}, async () => {
      while (current() && cursor < jobs.length) {
        const job = jobs[cursor++]
        try { await job() } catch { /* A failed preload can be retried when opening its card. */ }
      }
    }))
  })()
  return activeRun
}
