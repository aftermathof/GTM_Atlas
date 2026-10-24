import re


def clean_resume_text(value):
    value = re.sub(r'[\ue000-\uf8ff\U000f0000-\U0010ffff\ufffd\ufe0f\u200d📞☎📧📍📱✉🔗💼🎓📌🏠🌐]', '', value)
    prefix = r'^(?:\s*[•●▪◦‣⁃∙·◆◇■□►▶➢]+\s*|\s*[ǼǽŵŴϻ]+(?=\s*(?:[\u3400-\u9fff\d+•●▪◦‣⁃∙·◆◇■□►▶➢]|$))\s*)+'
    return '\n'.join(re.sub(prefix, '', line).strip() for line in value.splitlines()).strip()
