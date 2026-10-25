import { api, state } from './state'

export type Note = { id: string; title: string; body: string; created_at: string; updated_at: string; revision: number }
let owner = '', cards: Note[] | undefined
const details = new Map<string, Note>()
const pendingDetails = new Map<string, Promise<Note>>()
const versions = new Map<string, number>()
let pendingList: Promise<Note[]> | undefined, listVersion = 0
function checkOwner() {
  const current = state.user?.id + ':' + state.token
  if (owner !== current) {
    owner = current; cards = undefined; details.clear(); pendingDetails.clear(); versions.clear()
    pendingList = undefined; listVersion++
  }
  return current
}
export function cachedNotes() { checkOwner(); return cards }
export function cachedNote(id: string) { checkOwner(); return details.get(id) }
export function fetchNotes(): Promise<Note[]> {
  const account = checkOwner()
  if (pendingList) return pendingList
  const version = listVersion
  const pending: Promise<Note[]> = api('/notes').then(rows => {
    if (account === checkOwner()) {
      if (version !== listVersion) {
        if (pendingList === pending) pendingList = undefined
        return fetchNotes()
      }
      cards = rows
    }
    return rows
  }).finally(() => { if (pendingList === pending) pendingList = undefined })
  pendingList = pending
  return pending
}
export function fetchNote(id: string): Promise<Note> {
  const account = checkOwner()
  const cached = details.get(id)
  if (cached) return Promise.resolve(cached)
  const existing = pendingDetails.get(id)
  if (existing) return existing
  const version = versions.get(id) || 0
  const pending: Promise<Note> = api('/notes/' + encodeURIComponent(id)).then(row => {
    if (account === checkOwner() && version === (versions.get(id) || 0)) details.set(id, row)
    return row
  }).finally(() => { if (pendingDetails.get(id) === pending) pendingDetails.delete(id) })
  pendingDetails.set(id, pending)
  return pending
}
export function cacheSavedNote(row: Note) {
  forgetNote(row.id); details.set(row.id, row); listVersion++
  if (cards) cards = [{...row, body: ''}, ...cards.filter(item => item.id !== row.id)].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
}
export function forgetNote(id: string) {
  checkOwner(); versions.set(id, (versions.get(id) || 0) + 1); details.delete(id); pendingDetails.delete(id)
}
export function evictNote(id: string) {
  forgetNote(id); listVersion++
  if (cards) cards = cards.filter(item => item.id !== id)
}
