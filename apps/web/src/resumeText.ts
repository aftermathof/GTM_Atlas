export function cleanResumeText(value: string) {
  return value.replace(/[\p{Co}\uFFFD\uFE0F\u200D📞☎📧📍📱✉🔗💼🎓📌🏠🌐]/gu, '')
    .split('\n').map(line => line.replace(/^\s*[•●▪◦‣⁃∙·◆◇■□►▶➢]+\s*/u, '').trim()).join('\n').trim()
}

export function cleanDiagnosis(value: string) {
  return value
    .replace(/\[\[?[\w-]+:\d+\]\]?/g, '')
    .replace(/(?:[（(【\[]\s*)?\bf\d+(?:\s*(?:[–—~～-]|至|到|、|，|,)\s*f?\d+)*(?:\s*[）)】\]])?/gi, '')
    .replace(/\*\*([^*\n]*?[^*\s])[ \t]+\*\*/g, '**$1**')
    .replace(/[（(]\s*[）)]/g, '')
}
