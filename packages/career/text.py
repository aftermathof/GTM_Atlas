import re


def clean_resume_text(value):
    value = re.sub(r'[\ue000-\uf8ff\U000f0000-\U0010ffff\ufffd\ufe0f\u200d📞☎📧📍📱✉🔗💼🎓📌🏠🌐]', '', value)
    return '\n'.join(re.sub(r'^\s*[•●▪◦‣⁃∙·◆◇■□►▶➢]+\s*', '', line).strip() for line in value.splitlines()).strip()
