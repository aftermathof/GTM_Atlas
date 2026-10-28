import type { Note } from './notesStore'

export type NoteFolder = { id: string; title: string; created_at: string }

export function folderNotes(cards: Note[], folder: string) {
  return cards.filter(card => (card.folder_id || '') === folder)
}

export function noteNumbers(cards: Note[]) {
  return new Map([...cards].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id))
    .map((card, index) => [card.id, 'N' + String(index + 1).padStart(2, '0')]))
}
