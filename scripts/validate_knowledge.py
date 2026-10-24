"""Offline validation for the project's Markdown knowledge sources."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import yaml


def validate(root):
    root = Path(root).resolve()
    errors, ids, numbers, sources = [], set(), set(), set()
    counts = Counter()
    if not root.is_dir():
        return {'counts': {}, 'errors': ['knowledge root does not exist']}
    for file in sorted(root.rglob('*.md')):
        name = file.relative_to(root).as_posix()
        try:
            if file.is_symlink() or not file.resolve().is_relative_to(root):
                raise ValueError('unsafe file path')
            raw = file.read_text(encoding='utf-8')
            parts = raw.split('---', 2)
            if len(parts) != 3 or parts[0].strip():
                raise ValueError('missing YAML frontmatter')
            meta = yaml.safe_load(parts[1])
            required = {'id', 'title', 'kind', 'permission', 'quality_status', 'source_type', 'role_tags', 'industry_tags'}
            if not isinstance(meta, dict) or not required <= meta.keys():
                raise ValueError('missing required metadata')
            did, kind = str(meta['id']), meta['kind']
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', did) or kind not in {'jd', 'interview', 'learning'}:
                raise ValueError('invalid id or kind')
            if did in ids:
                raise ValueError('duplicate id: ' + did)
            ids.add(did)
            if any(not isinstance(meta[k], list) or any(not isinstance(x, str) for x in meta[k]) for k in ['role_tags', 'industry_tags']):
                raise ValueError('tags must be lists of strings')
            if re.search(r'(?:securityId|xsec_token|access_token|refresh_token)=', raw, re.I):
                raise ValueError('session parameter in exported content')
            if meta['permission'] != 'public_display' or meta['quality_status'] == 'deprecated':
                counts['excluded'] += 1
                continue
            required_note = {'source_note_id', 'source_url', 'source_author', 'excerpt'}
            if not required_note <= meta.keys() or any(not isinstance(meta[k], str) or not meta[k].strip() for k in required_note):
                raise ValueError('missing display number, source or excerpt')
            number = meta['source_note_id']
            if not re.fullmatch({'jd': 'J', 'interview': 'I', 'learning': 'L'}[kind] + r'\d{2,}', number):
                raise ValueError('number prefix does not match kind: ' + number)
            identity = (number[0], int(number[1:]))
            if identity in numbers:
                raise ValueError('duplicate source_note_id: ' + number)
            numbers.add(identity)
            url = urlparse(meta['source_url'])
            if url.scheme not in {'http', 'https'} or not url.netloc:
                raise ValueError('invalid source_url')
            source_id = meta.get('source_id') or meta.get('source_job_id') or url.path.rstrip('/').rsplit('/', 1)[-1].removesuffix('.html')
            source = (url.netloc.removeprefix('www.'), str(source_id))
            if source in sources:
                raise ValueError('duplicate source across categories: ' + str(source_id))
            sources.add(source)
            if len(parts[2].strip()) < 10:
                raise ValueError('missing substantive body')
            counts[kind] += 1
        except (ValueError, TypeError, KeyError, OSError, yaml.YAMLError) as error:
            errors.append(name + ': ' + str(error))
    return {'counts': dict(counts), 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / 'knowledge')
    args = parser.parse_args()
    report = validate(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report['errors']))
