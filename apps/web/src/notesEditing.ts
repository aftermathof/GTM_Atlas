export function inlineEdit(text: string, from: number, to: number, marker: string) {
  const size = marker.length
  const valid = (at: number) => text.slice(at, at + size) === marker &&
    (size !== 1 || (text[at - 1] !== '*' && text[at + 1] !== '*'))
  let left = -1, right = -1
  const combined = [...text.matchAll(/\*{3}(?!\*)([\s\S]*?\S)\*{3}(?!\*)/g)].find(match =>
    from >= match.index! + 3 && to <= match.index! + match[0].length - 3)
  if (combined) {
    left = combined.index!; right = left + combined[0].length - 3
  } else if (to - from > size * 2 && valid(from) && valid(to - size)) {
    left = from; right = to - size
  } else if (from >= size && valid(from - size) && valid(to)) {
    left = from - size; right = to
  } else if (from === to) {
    for (let at = 0; at < text.length; at++) {
      if (!valid(at)) continue
      if (left < 0) left = at
      else {
        right = at
        if (from >= left + size && from <= right && !/\n\s*\n/.test(text.slice(left, right))) break
        left = -1; right = -1
      }
      at += size - 1
    }
    if (right < 0 || from < left + size || from > right) left = right = -1
  }
  if (left >= 0 && right >= 0) {
    const value = text.slice(0, left) + text.slice(left + size, right) + text.slice(right + size)
    return {text: value, from: Math.max(left, from - size), to: Math.min(right - size, to - size)}
  }
  const selected = text.slice(from, to) || '内容'
  return {text: text.slice(0, from) + marker + selected + marker + text.slice(to), from: from + size, to: from + size + selected.length}
}
