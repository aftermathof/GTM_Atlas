import { api, state } from '../../state'
import type { NoteFolder } from './noteFolders'

export type Note = { id: string; title: string; body: string; created_at: string; updated_at: string; revision: number; folder_id?: string | null }
let owner = '', cards: Note[] | undefined
let folders: NoteFolder[] | undefined, pendingFolders: Promise<NoteFolder[]> | undefined, folderVersion = 0
const details = new Map<string, Note>()
const pendingDetails = new Map<string, Promise<Note>>()
const versions = new Map<string, number>()
const deleted = new Set<string>()
const deletedFolders = new Set<string>()
let pendingList: Promise<Note[]> | undefined, listVersion = 0
function checkOwner() {
  const current = state.user?.id + ':' + state.token
  if (owner !== current) {
    owner = current; cards = undefined; details.clear(); pendingDetails.clear(); versions.clear(); deleted.clear()
    state.notesDeleteError = ''
    pendingList = undefined; listVersion++
    folders = undefined; pendingFolders = undefined; folderVersion++
    deletedFolders.clear()
  }
  return current
}
export function cachedNotes() { checkOwner(); return cards }
export function cachedNote(id: string) { checkOwner(); const row=details.get(id); return row && !deletedFolders.has(row.folder_id || '') ? row : undefined }
export function cachedNoteFolders() { checkOwner(); return folders }
export function fetchNoteFolders(): Promise<NoteFolder[]> {
  const account = checkOwner()
  if (folders) return Promise.resolve(folders)
  if (pendingFolders) return pendingFolders
  const version = folderVersion
  const pending: Promise<NoteFolder[]> = api('/notes/folders').then(rows => {
    if (account === checkOwner()) {
      if (version !== folderVersion) {
        if (pendingFolders === pending) pendingFolders = undefined
        return fetchNoteFolders()
      }
      rows = rows.filter((row: NoteFolder) => !deletedFolders.has(row.id))
      folders = rows
    }
    return rows
  }).finally(() => { if (pendingFolders === pending) pendingFolders = undefined })
  pendingFolders = pending
  return pending
}
export function cacheSavedNoteFolder(folder: NoteFolder) {
  checkOwner(); folderVersion++
  if (folders) folders = [...folders.filter(row => row.id !== folder.id), folder]
}
export function fetchNotes(): Promise<Note[]> {
  const account = checkOwner()
  if (cards) return Promise.resolve(cards)
  if (pendingList) return pendingList
  const version = listVersion
  const pending: Promise<Note[]> = api('/notes').then(rows => {
    if (account === checkOwner()) {
      if (version !== listVersion) {
        if (pendingList === pending) pendingList = undefined
        return fetchNotes()
      }
      rows = rows.filter((row: Note) => !deleted.has(row.id) && !deletedFolders.has(row.folder_id || ''))
      cards = rows
    }
    return rows
  }).finally(() => { if (pendingList === pending) pendingList = undefined })
  pendingList = pending
  return pending
}
export function fetchNote(id: string): Promise<Note> {
  const account = checkOwner()
  if (deleted.has(id)) return Promise.reject(new Error('这篇笔记已删除'))
  const cached = cachedNote(id)
  if (cached) return Promise.resolve(cached)
  const existing = pendingDetails.get(id)
  if (existing) return existing
  const version = versions.get(id) || 0
  const pending: Promise<Note> = api('/notes/' + encodeURIComponent(id)).then(row => {
    if (account === checkOwner() && (deleted.has(id) || deletedFolders.has(row.folder_id || ''))) throw new Error('这篇笔记或所属文件夹已删除')
    if (account === checkOwner() && version === (versions.get(id) || 0)) details.set(id, row)
    return row
  }).finally(() => { if (pendingDetails.get(id) === pending) pendingDetails.delete(id) })
  pendingDetails.set(id, pending)
  return pending
}
export function cacheSavedNote(row: Note) {
  checkOwner(); if(deletedFolders.has(row.folder_id || ''))return
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

export async function deleteNote(note: Note) {
  const account = checkOwner()
  if (deleted.has(note.id)) return
  const detail = details.get(note.id)
  deleted.add(note.id); evictNote(note.id)
  state.notesDeleteError = ''; state.notesRevision = (state.notesRevision || 0) + 1
  try {
    await api('/notes/' + encodeURIComponent(note.id), {method:'DELETE'})
  } catch (error: any) {
    if (account === checkOwner()) {
      deleted.delete(note.id); listVersion++
      if (detail) details.set(note.id, detail)
      if (cards && !cards.some(row => row.id === note.id)) cards = [...cards, {...note, body:''}].sort((a,b) => b.updated_at.localeCompare(a.updated_at))
      state.notesDeleteError = '删除失败，笔记已恢复：' + error.message
      state.notesRevision = (state.notesRevision || 0) + 1
    }
    throw error
  }
}

export async function deleteNoteFolder(folder: NoteFolder) {
  const account = checkOwner()
  if(deletedFolders.has(folder.id))return
  const removedCards = (cards || []).filter(row => row.folder_id === folder.id)
  const removedDetails = new Map([...details].filter(([, row]) => row.folder_id === folder.id))
  deletedFolders.add(folder.id); folderVersion++; listVersion++
  if(folders)folders=folders.filter(row => row.id !== folder.id)
  if(cards)cards=cards.filter(row => row.folder_id !== folder.id)
  for(const id of new Set([...removedCards.map(row=>row.id), ...removedDetails.keys()]))forgetNote(id)
  state.notesDeleteError=''; state.notesRevision=(state.notesRevision || 0)+1
  try {
    await api('/notes/folders/' + encodeURIComponent(folder.id), {method:'DELETE'})
  } catch(error: any) {
    if(account===checkOwner()) {
      deletedFolders.delete(folder.id); folderVersion++; listVersion++
      if(folders && !folders.some(row=>row.id===folder.id))folders=[...folders,folder].sort((a,b)=>a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id))
      if(cards)cards=[...cards,...removedCards.filter(row=>!cards!.some(current=>current.id===row.id))].sort((a,b)=>b.updated_at.localeCompare(a.updated_at))
      for(const [id,row] of removedDetails)if(!details.has(id))details.set(id,row)
      state.notesDeleteError='删除文件夹失败，内容已恢复：'+error.message
      state.notesRevision=(state.notesRevision || 0)+1
    }
    throw error
  }
}
