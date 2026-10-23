"""Import the supplied original research notes without duplicating collection files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import yaml


def import_notes(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    index = json.loads((source / '知识库.json').read_text(encoding='utf-8-sig'))
    if index.get('content_type') != 'original_research_notes':
        raise ValueError('Expected an original research-note collection')
    report = {'learning': 0, 'interview': 0, 'jd': 0, 'documents': []}
    seen = set()
    for note in index['notes']:
        source_id = str(note['id'])
        if not re.fullmatch(r'[A-Za-z0-9_-]+', source_id) or source_id in seen:
            raise ValueError('Invalid or duplicate note ID')
        seen.add(source_id)
        path = (source / note['file']).resolve()
        if not path.is_relative_to(source) or path.is_symlink() or path.suffix != '.md':
            raise ValueError('Unsafe note path')
        kind = 'interview' if note['category'] == '实习校招面经' else 'learning' if note['category'] == '学习与在职经验' else None
        if kind is None:
            raise ValueError('Unknown note category; do not infer a JD from an interview')
        raw = path.read_bytes()
        body = raw.decode('utf-8-sig').replace('\r\n', '\n')
        tags = note.get('tags', [])
        text = note['title'] + ' ' + ' '.join(tags) + ' ' + note.get('overview', '')
        roles = ['gtm']
        for role, pattern in [('pmm', '产品|上市|定位'), ('overseas_channel_sales', '渠道|销售|库存|PSI'), ('kol_marketing', 'KOL|达人|内容营销'), ('growth', '增长|复盘|数据')]:
            if re.search(pattern, text, re.I):
                roles.append(role)
        industries = []
        if re.search('飞书|软件|SaaS', text, re.I): industries.append('software')
        if re.search('消费电子|安克|影石|韶音|倍思|小米|传音|耳机|手机|充电', text): industries.append('consumer_electronics')
        if re.search('AI硬件', text, re.I): industries.append('ai_hardware')
        if re.search('机器人|智元', text): industries.append('robotics')
        meta = {
            'id': 'research-' + source_id.lower(), 'title': note['title'], 'kind': kind,
            'role_tags': roles, 'industry_tags': industries, 'tags': tags,
            'source_type': 'original_research_note', 'source_url': note.get('source_url'),
            'source_author': note.get('author'), 'note_author': '用户提供的原创研究整理',
            'collected_at': index.get('collected_at'), 'displayed_date': note.get('displayed_date'),
            'permission': 'public_display', 'quality_status': 'unverified', 'language': 'zh-CN',
            'collection': 'GTM分类60篇', 'source_note_id': source_id,
            'tagging_method': 'title_and_summary_keywords_v1',
            'source_file_sha256': hashlib.sha256(raw).hexdigest(), 'excerpt': note.get('overview', ''),
            'limitations': note.get('limitations', []),
            'content_notice': '完整研究笔记；不等于原帖逐字全文，个人自述未经企业确认。',
        }
        directory = destination / ('interviews' if kind == 'interview' else 'learning') / 'research-notes'
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (meta['id'] + '.md')
        if target.is_symlink(): raise ValueError('Refusing symlink output')
        target.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n' + body, encoding='utf-8')
        report[kind] += 1
        report['documents'].append({'id': meta['id'], 'kind': kind, 'source_sha256': meta['source_file_sha256']})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', default='knowledge')
    parser.add_argument('--report', default='docs/IMPORT_REPORT.json')
    args = parser.parse_args()
    report = import_notes(args.source, args.destination)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'documents'}, ensure_ascii=False))
