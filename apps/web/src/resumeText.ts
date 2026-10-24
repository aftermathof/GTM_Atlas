const resumeHeadings = '个人信息|基本信息|联系方式|求职意向|教育(?:背景|经历)|(?:实习|工作|项目|实践|校园|科研|研究|志愿)(?:经历|经验)|技能(?:特长|清单)?|专业技能|个人技能|语言能力|自我评价|个人总结|荣誉奖项|获奖经历|证书'
const decorativeHeading = new RegExp('^[^A-Za-z0-9\\u3400-\\u9fff]{1,16}(?=(?:'+resumeHeadings+')\\s*[:：]?\\s*$)', 'u')

export function cleanResumeText(value: string) {
  return value.replace(/[\p{Co}\uFE0F\u200D📞☎📧📍📱✉🔗💼🎓📌🏠🌐]/gu, '')
    .split('\n').map(line => line.replace(/^(?:\s*[•●▪◦‣⁃∙·◆◇■□►▶➢]+\s*|\s*[ǼǽŵŴϻ]+(?=\s*(?:[\u3400-\u9fff\d+•●▪◦‣⁃∙·◆◇■□►▶➢]|$))\s*)+/u, '').replace(decorativeHeading, '').replace(/[\uFFFD\x00-\x08\x0E-\x1F\x7F]/gu, '[待确认]').trim()).join('\n').trim()
}

export function cleanDiagnosis(value: string) {
  return value
    .replace(/\[\[?[\w-]+:\d+\]\]?/g, '')
    .replace(/(?:[（(【\[]\s*)?\bf\d+(?:\s*(?:[–—~～-]|至|到|、|，|,)\s*f?\d+)*(?:\s*[）)】\]])?/gi, '')
    .replace(/\*\*([^*\n]*?[^*\s])[ \t]+\*\*/g, '**$1**')
    .replace(/[（(]\s*[）)]/g, '')
}
