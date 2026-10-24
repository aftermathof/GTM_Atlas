import re

HEADINGS = r'个人信息|基本信息|联系方式|求职意向|教育(?:背景|经历)|(?:实习|工作|项目|实践|校园|科研|研究|志愿)(?:经历|经验)|技能(?:特长|清单)?|专业技能|个人技能|语言能力|自我评价|个人总结|荣誉奖项|获奖经历|证书'


def clean_resume_text(value):
    value = re.sub(r'[\ue000-\uf8ff\U000f0000-\U0010ffff\ufe0f\u200d📞☎📧📍📱✉🔗💼🎓📌🏠🌐]', '', value)
    prefix = r'^(?:\s*[•●▪◦‣⁃∙·◆◇■□►▶➢]+\s*|\s*[ǼǽŵŴϻ]+(?=\s*(?:[\u3400-\u9fff\d+•●▪◦‣⁃∙·◆◇■□►▶➢]|$))\s*)+'
    lines = []
    for line in value.splitlines():
        line = re.sub(prefix, '', line)
        # Only a complete known section heading makes an unfamiliar prefix decorative.
        line = re.sub(r'^[^A-Za-z0-9\u3400-\u9fff]{1,16}(?=(?:' + HEADINGS + r')\s*[:：]?\s*$)', '', line)
        line = re.sub(r'[\ufffd\x00-\x08\x0e-\x1f\x7f]', '[待确认]', line)
        lines.append(line.strip())
    return '\n'.join(lines).strip()
