export type AIProgress = { text: string; label: string; model: string; citations: any[] }

export async function readAIStream(response: Response, update: (progress: AIProgress) => void): Promise<any> {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('回答连接不可用，请保留输入后重试')
  const decoder = new TextDecoder()
  let buffer = '', progress: AIProgress = {text:'', label:'正在生成', model:'', citations:[]}
  function consume(frame: string) {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
    if (!data) return
    const event = JSON.parse(data)
    if (event.type === 'error') throw Object.assign(new Error(event.detail || '回答未完成，请保留输入后重试'), {aiStream:true, status:event.status})
    if (event.type === 'result') return {value:event.value}
    if (event.type === 'start') progress = {...progress, text:'', label:event.label || '正在生成', model:event.model || ''}
    else if (event.type === 'sources') progress = {...progress, citations:event.citations || []}
    else if (event.type === 'delta') progress = {...progress, text:progress.text + event.text}
    else if (event.type === 'replace') progress = {...progress, text:event.text}
    let text = progress.text
    const bracket = text.lastIndexOf('[')
    if (bracket >= 0 && !text.slice(bracket).includes(']') && progress.citations.some(citation => ('[' + citation.chunk_id + ']').startsWith(text.slice(bracket)))) text = text.slice(0, bracket)
    update({...progress, text})
  }
  try {
    while (true) {
      const {value, done} = await reader.read()
      buffer += decoder.decode(value, {stream:!done})
      let separator: RegExpExecArray | null
      while ((separator = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, separator.index)
        buffer = buffer.slice(separator.index + separator[0].length)
        const result = consume(frame)
        if (result) return result.value
      }
      if (done) {
        const result = consume(buffer)
        if (result) return result.value
        throw new Error('回答连接中断，未收到完整结果；当前输入和预览已保留，请重试')
      }
    }
  } catch (error: any) {
    if (error?.aiStream || error?.name === 'AbortError') throw error
    throw Object.assign(new Error('回答连接中断，未收到完整结果；当前输入和预览已保留，请重试'), {aiStream:true})
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
