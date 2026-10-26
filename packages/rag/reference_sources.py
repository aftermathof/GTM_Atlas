"""Read the same local reference sources used by the website; never execute HTML."""
import hashlib
import json
import re
from html.parser import HTMLParser
from html import unescape
from pathlib import Path

import yaml


class MainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.active = True
        if not self.active:
            return
        if tag in {'script', 'style', 'nav', 'header', 'footer', 'button'}:
            self.ignored += 1
        if self.ignored:
            return
        if re.fullmatch(r'h[1-6]', tag):
            self.parts.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'li':
            self.parts.append('\n- ')
        elif tag == 'br':
            self.parts.append('\n')
        elif tag in {'p', 'div', 'section', 'article', 'ul', 'ol', 'table', 'tr'}:
            self.parts.append('\n\n')
        elif tag in {'td', 'th'}:
            self.parts.append(' | ')
        elif tag == 'img' and dict(attrs).get('alt'):
            self.parts.append(dict(attrs)['alt'])

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'header', 'footer', 'button'} and self.active:
            self.ignored -= 1
        if self.active and not self.ignored and (tag in {'p', 'div', 'li', 'section', 'tr'} or re.fullmatch(r'h[1-6]', tag)):
            self.parts.append('\n')
        if tag == 'main':
            self.active = False

    def handle_data(self, data):
        if self.active and not self.ignored:
            self.parts.append(re.sub(r'\s+', ' ', data))

    def text(self):
        text = re.sub(r'[ \t]*\n[ \t]*', '\n', ''.join(self.parts))
        return re.sub(r'\n{3,}', '\n\n', text).strip()


def reference_documents(project_root):
    root = Path(project_root)
    overview = root / 'knowledge/site/gtm-overview'
    for file in sorted(overview.glob('*.html')):
        raw = file.read_text(encoding='utf-8')
        parser = MainText()
        parser.feed(raw)
        body = parser.text()
        if not body:
            raise ValueError(f'Empty overview main content: {file.name}')
        heading = re.search(r'<title>(.*?)</title>', raw, re.I | re.S)
        title = 'GTM 概览｜' + (unescape(heading[1]).strip() if heading else file.stem)
        yield _document(root, file, 'gtm-reference-overview-' + file.stem, title, body,
                        '/gtm-overview/' + file.name, 'overview')
    book = root / 'knowledge/site/gtm-book'
    for file in sorted(book.glob('chapter-*.html')):
        raw = file.read_text(encoding='utf-8')
        parser = MainText()
        parser.feed(raw)
        body = parser.text()
        if not body:
            raise ValueError(f'Empty book main content: {file.name}')
        heading = re.search(r'<title>(.*?)</title>', raw, re.I | re.S)
        chapter = unescape(heading[1]).split(' · ')[0].strip() if heading else file.stem
        yield _document(root, file, 'gtm-reference-book-' + file.stem,
                        '爆品操盘GTM｜' + chapter, body, '/gtm-book/' + file.name, 'book')
    glossary = root / 'knowledge/glossary/gtm-glossary.json'
    if glossary.exists():
        items = json.loads(glossary.read_text(encoding='utf-8'))
        fields = {'term', 'fullName', 'explanation', 'example'}
        if not isinstance(items, list) or not items:
            raise ValueError('Invalid glossary entries')
        seen, sections = set(), ['# GTM 专有名词库']
        for item in items:
            if not isinstance(item, dict) or not fields <= item.keys() or any(not isinstance(item[k], str) or not item[k].strip() for k in fields):
                raise ValueError('Invalid glossary entry fields')
            if item['term'] in seen:
                raise ValueError('Duplicate glossary term: ' + item['term'])
            seen.add(item['term'])
            sections.append(f"## {item['term']} · {item['fullName']}\n\n{item['explanation']}\n\n{item['example']}")
        yield _document(root, glossary, 'gtm-reference-glossary', 'GTM 专有名词库',
                        '\n\n'.join(sections), '/glossary', 'glossary')


def _document(root, file, did, title, body, url, group):
    meta = {
        'id': did, 'title': title, 'kind': 'learning', 'permission': 'public_display',
        'quality_status': 'user_provided', 'source_type': 'site_reference',
        'source_url': url, 'source_author': 'GTM Atlas', 'role_tags': [], 'industry_tags': [],
        'resource_group': group, 'catalog_visible': False, 'universal_reference': True,
        'source_file_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
        'excerpt': '从站内原始资料提取，可检索并引用；含义与适用条件以原资料为准。',
        'content_notice': '站内学习资料的文字索引，保留标题、段落及图表中的文字；不是独立核实的企业标准。可通过来源链接查看原页面。',
    }
    if group == 'book':
        meta['source_author'] = '朱秋虎'
        meta['content_notice'] = '《爆品操盘GTM》的章节文字索引，保留正文、表格文字和图题；图片内部文字未自动识别。请通过来源链接查看完整图表。'
    return file.relative_to(root).as_posix(), '---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n' + body
