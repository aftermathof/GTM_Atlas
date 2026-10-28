// Internal retrieval identifiers stay in structured citations, not in readable prose.
export function cleanAIText(text: string = ''): string {
  return text.replace(/\[[\w-]+:\d+\](?:\([^\s)]*\))?/g, '')
}
