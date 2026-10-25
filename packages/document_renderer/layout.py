"""Arrange resume text into template fields without generating or rewriting content."""
import re
from packages.career.structure import SECTION_NAMES
from packages.career.text import clean_resume_text

SECTION_LABELS = {
    'personal': ('个人信息', '基本信息', '联系方式', 'Personal Information'),
    'education': ('教育背景', '教育经历', 'Education'),
    'projects': ('项目经历', '项目经验', '研究项目', 'Projects'),
    'experience': ('实习经历', '工作经历', '实习与工作经历', '实习/工作经历', 'Experience'),
    'skills': ('技能特长', '专业技能', '个人技能', '技能', 'Skills'),
    'summary': ('自我评价', '个人总结', 'Summary'),
    'other': ('其他经历',),
}
DATE = re.compile(r'(?:19|20)\d{2}(?:[./年-]\d{1,2}(?:月)?)?\s*(?:至|到|[-–—~～])\s*(?:(?:19|20)\d{2}(?:[./年-]\d{1,2}(?:月)?)?|至今|现在|present)', re.I)
ACTION = re.compile(r'^(?:工作内容|工作职责|职责|项目简介|项目成果|成果产出|负责|参与|协助|完成|通过|实现|提升|累计|推动|主导|与|为|向|对|针对|基于|面向|围绕|输出|策划|搭建|构建|建立|组织|撰写|支持|维护|开展|整理|分析|跟进|执行|收集|设计|制定|管理|运营[：:])')
COMPANY = re.compile(r'公司|集团|工作室|实验室|研究院|Company|Corp|Inc\b|Ltd\b', re.I)
SKILL_LABEL = r'(?:办公(?:工具|软件)|语言(?:能力)?|英语(?:写作|能力|水平)?|AI\s*(?:工具|能力)|数据分析|设计工具|编程语言|专业能力|工具技能)\s*[:：]'


def content_lines(text, section):
    labels = '|'.join(re.escape(s) for s in SECTION_LABELS.get(section, ()))
    lines = []
    for line in clean_resume_text(text).splitlines():
        if labels:
            line = re.sub(r'^(?:' + labels + r')\s*(?:[:：]\s*|$)', '', line, flags=re.I)
        if line.strip():
            lines.append(line.strip())
    return lines


def _entries(lines, education=False):
    entries, headers, items = [], [], []

    def finish():
        if not headers and not items:
            return
        date = next((m.group() for line in headers if (m := DATE.search(line))), '')
        parts = [DATE.sub('', line).strip(' |｜,，;；') for line in headers]
        parts = [part for part in parts if part]
        # Most extracted headers are either separate lines or one company/role/date line.
        if not education and parts:
            first = re.split(r'\s*[|｜]\s*|\s{2,}|\s+(?=\S*(?:实习生|经理|专员|助理|负责人|Intern\b|Manager\b))', parts[0], maxsplit=1, flags=re.I)
            parts = first + parts[1:]
        entries.append({'organization': parts[0] if parts else '',
                        'role': ' · '.join(parts[1:]), 'date': date, 'items': items[:]})

    for line in lines:
        is_date = bool(DATE.search(line))
        named_role = bool(re.search(r'(?:[|｜]|\s+)\s*\S*(?:实习生|经理|专员|助理|负责人|Intern\b|Manager\b)', line, re.I))
        is_header = len(line) < 160 and not ACTION.search(line) and not re.search(r'[:：。；;]', line) and (is_date or bool(COMPANY.search(line)) or named_role or (education and bool(re.search(r'大学|学院|学校|University|College', line, re.I))))
        # A date and its school/company may arrive on adjacent physical lines.
        has_date = any(DATE.search(h) for h in headers)
        has_org = any(DATE.sub('', h).strip(' |｜') for h in headers)
        if is_header and (items or (headers and is_date and has_date) or (headers and not is_date and has_org)):
            finish(); headers, items = [], []
        if is_header or (headers and not items and len(line) < 65 and not ACTION.search(line) and not re.search(r'[:：。；;]', line)):
            headers.append(line)
        elif not headers and not education and len(line) < 120 and not ACTION.search(line):
            headers.append(line)
        else:
            continuation = (items and not re.search(r'[。；;.!?！？]$', items[-1])
                            and not ACTION.search(line) and not re.match(r'^[^:：]{1,16}[:：]', line))
            if continuation:
                space = ' ' if re.search(r'[A-Za-z0-9]$', items[-1]) and re.match(r'[A-Za-z0-9]', line) else ''
                items[-1] += space + line
            else:
                items.append(line)
    finish()
    return entries


def build_layout(facts, structure):
    sections = {key: [] for key in SECTION_NAMES}
    for fact in facts:
        section = fact.get('section') or structure['assignments'][fact['id']]
        sections[section].extend(content_lines(fact['text'], section))
    for key in ('education', 'projects', 'experience'):
        sections[key] = _entries(sections[key], education=key == 'education')
    sections['skills'] = [item.strip(' ;；') for line in sections['skills']
                          for item in re.split(r'[；;。]?\s*(?=' + SKILL_LABEL + r')', line, flags=re.I) if item.strip(' ;；')]
    return sections


def qa_fragments(fact, section):
    # Entry dates may move to the right column; check each source component, not its old order.
    for line in content_lines(fact['text'], section):
        if section in {'education', 'projects', 'experience'} and DATE.search(line) and not ACTION.search(line):
            for match in DATE.finditer(line):
                yield match.group()
            line = DATE.sub('', line)
            yield from (part.strip() for part in re.split(r'[|｜]|\s+', line) if part.strip())
        elif section == 'skills':
            yield from (part.strip(' ;；') for part in re.split(r'[；;。]?\s*(?=' + SKILL_LABEL + ')', line, flags=re.I) if part.strip(' ;；'))
        else:
            yield line
