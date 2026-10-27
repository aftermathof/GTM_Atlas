"""Read-only checks for an author collection. No browser, credentials or publication."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, unquote

import yaml

try:
    from PIL import Image
except ImportError:
    Image = None

TOKEN = re.compile(r'(?:xsec_token|securityId|access_token|refresh_token)=', re.I)
ID = re.compile(r'^[0-9a-f]{24}$', re.I)
PREFIX = {'learning': 'L', 'interview': 'I', 'jd': 'J'}


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(root, relative):
    path = Path(relative)
    if path.is_absolute():
        raise ValueError('absolute path is not a batch-relative path')
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('path escapes its declared root')
    return target


def read_note(path):
    raw = path.read_text(encoding='utf-8')
    parts = re.split(r'^---\s*$', raw, maxsplit=2, flags=re.M)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError('missing frontmatter')
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        raise ValueError('frontmatter is not a mapping')
    return meta, parts[2], raw


def source_id(url):
    parsed = urlsplit(str(url))
    if parsed.hostname not in {'xiaohongshu.com', 'www.xiaohongshu.com'}:
        return None
    parts = parsed.path.strip('/').split('/')
    is_note = (len(parts) == 2 and parts[0] == 'explore') or (len(parts) == 3 and parts[:2] == ['discovery', 'item']) or (len(parts) == 4 and parts[:2] == ['user', 'profile'])
    return parts[-1] if is_note and ID.fullmatch(parts[-1]) else None


def reserved_labels(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'source_note_id', 'numbers', 'reserved_numbers'}:
                for label in child if isinstance(child, list) else [child]:
                    if re.fullmatch(r'[JIL]\d+', str(label)):
                        yield str(label)
            elif isinstance(child, (dict, list)):
                yield from reserved_labels(child)
    elif isinstance(value, list):
        for child in value:
            yield from reserved_labels(child)


def scan_project(project, prefix='L', reserved=None, history_text=None):
    project = Path(project).resolve()
    root = project / 'knowledge'
    if not root.is_dir():
        raise ValueError('project must contain knowledge/')
    errors, records, protected = [], [], {}
    ids, labels, sources = set(), set(), set()
    for path in sorted(root.rglob('*.md')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            errors.append(name + ': unsafe knowledge path')
            continue
        protected[name] = checksum(path)
        try:
            meta, _, _ = read_note(path)
            did, kind, label = str(meta['id']), meta['kind'], str(meta['source_note_id'])
            if kind not in PREFIX or not re.fullmatch(PREFIX[kind] + r'\d+', label):
                raise ValueError('invalid kind/number')
        except (ValueError, KeyError, yaml.YAMLError):
            errors.append(name + ': invalid metadata/frontmatter')
            continue
        sid = source_id(meta.get('source_url', '')) or ''
        if sid and meta.get('source_id') and str(meta['source_id']) != sid:
            errors.append(name + ': source ID/URL mismatch')
        if TOKEN.search(str(meta.get('source_url', ''))):
            errors.append(name + ': session parameters in source URL')
        for field, value, seen in [('id', did, ids), ('number', label, labels), ('source_id', sid, sources)]:
            if value and value in seen:
                errors.append(name + ': duplicate ' + field)
            if value:
                seen.add(value)
        records.append({'id': did, 'kind': kind, 'source_note_id': label, 'source_id': sid,
                        'path': name, 'sha256': protected[name]})
    used = set(labels)
    if reserved:
        used.update(reserved_labels(json.loads(Path(reserved).read_text(encoding='utf-8'))))
    if history_text is not None:
        used.update(a + b for a, b in re.findall(r'(?m)^[+\- ]*source_note_id:\s*[\'"]?([JIL])(\d+)', history_text))
        used.update(a.upper() + b for a, b in re.findall(r'research-([jil])(\d+)\.md', history_text, re.I))
    maximum = max([int(label[1:]) for label in used if label.startswith(prefix)] or [0])
    return {'prefix': prefix, 'next_number': f'{prefix}{maximum + 1:02d}', 'history_checked': history_text is not None,
            'existing_xhs_ids': sorted(s for s in sources if ID.fullmatch(s)), 'records': records,
            'protected_files': protected, 'errors': errors}


def validate_batch(batch, project=None, published=False):
    batch = Path(batch).resolve()
    manifest = json.loads((batch / 'manifest.json').read_text(encoding='utf-8'))
    errors, counts, kept_files = [], Counter(), set()
    if TOKEN.search(json.dumps(manifest, ensure_ascii=False)):
        errors.append('manifest contains session parameters')
    scan = scan_project(project) if project else None
    if scan:
        errors.extend(scan['errors'])
    by_id = {r['id']: r for r in scan['records']} if scan else {}
    existing_sources = set(scan['existing_xhs_ids']) if scan else set()
    existing_numbers = {r['source_note_id'] for r in scan['records']} if scan else set()
    seen_ids, seen_numbers, seen_notes = set(), set(), set()
    prefix = manifest.get('asset_url_prefix', '/xhs-author-assets/')
    if not re.fullmatch(r'/[A-Za-z0-9_/-]+/', prefix) or '..' in prefix:
        errors.append('invalid asset_url_prefix')
    posts = manifest.get('posts', [])
    allowed = {'staged', 'existing_skipped', 'video_skipped', 'excluded', 'failed', 'pending'}
    for post in posts:
        sid, status = str(post.get('source_id', '')), post.get('status')
        label = sid or '(missing source id)'
        if not ID.fullmatch(sid) or sid in seen_ids:
            errors.append(label + ': invalid/duplicate source ID')
        seen_ids.add(sid)
        url = str(post.get('source_url', ''))
        parsed = urlsplit(url)
        if source_id(url) != sid or parsed.scheme != 'https' or parsed.query or parsed.fragment:
            errors.append(label + ': source URL is not canonical or does not match ID')
        if status not in allowed:
            errors.append(label + ': unknown status')
        counts[str(status)] += 1
        if status in {'failed', 'excluded'} and not post.get('reason'):
            errors.append(label + ': missing failure/exclusion reason')
        if status == 'existing_skipped' and scan and sid not in existing_sources:
            errors.append(label + ': skipped-existing source not found in project')
        if status != 'staged':
            continue
        try:
            note = within(batch, post['note_file'])
            if not note.is_relative_to((batch / 'notes').resolve()):
                raise ValueError('note is not under notes/')
            meta, body, raw = read_note(note)
            required = {'id', 'title', 'kind', 'permission', 'quality_status', 'source_type', 'source_note_id',
                        'source_id', 'source_url', 'source_author', 'role_tags', 'industry_tags', 'tags',
                        'collected_at', 'displayed_date', 'excerpt', 'limitations', 'content_notice'}
            if not required <= meta.keys():
                raise ValueError('missing required metadata')
            number, did = str(meta['source_note_id']), str(meta['id'])
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', did) or meta['kind'] not in {'learning', 'interview'}:
                raise ValueError('invalid document ID or kind')
            if not re.fullmatch(PREFIX[meta['kind']] + r'\d{2,}', number) or number != post.get('source_note_id'):
                raise ValueError('invalid or inconsistent display number')
            if str(meta['source_id']) != sid or meta['source_url'] != url or meta['source_author'] != manifest['author']:
                raise ValueError('note/manifest identity mismatch')
            if meta['permission'] != 'public_display' or meta['source_type'] != 'original_research_note' or meta['quality_status'] != 'unverified':
                raise ValueError('incorrect source/permission/quality boundary')
            if any(not isinstance(meta[key], list) or any(not isinstance(item, str) for item in meta[key])
                   for key in ['role_tags', 'industry_tags', 'tags', 'limitations']):
                raise ValueError('metadata lists are not lists')
            if not str(meta['excerpt']).strip() or len(re.findall(r'^# ', body, re.M)) != 1:
                raise ValueError('missing summary or invalid top-level heading count')
            for heading in ['## 内容概述', '## 来源内容整理', '## 阅读边界与核对说明']:
                if heading not in body:
                    raise ValueError('missing required body section')
            if TOKEN.search(raw):
                raise ValueError('session parameters in note')
            if did in seen_notes or number in seen_numbers:
                raise ValueError('duplicate batch ID/number')
            seen_notes.add(did); seen_numbers.add(number)
            if scan:
                existing = by_id.get(did)
                if published:
                    if not existing or existing['source_id'] != sid or existing['source_note_id'] != number or existing['sha256'] != checksum(note):
                        raise ValueError('published note is missing or not identical')
                elif did in by_id or number in existing_numbers or sid in existing_sources:
                    raise ValueError('new note collides with project; do not overwrite')
            image_numbers, note_files = set(), []
            for item in post.get('images', []):
                if item.get('index') in image_numbers or not isinstance(item.get('index'), int) or item['index'] < 1:
                    raise ValueError('invalid/duplicate image index')
                image_numbers.add(item['index'])
                if item.get('decision') not in {'keep', 'duplicate', 'irrelevant', 'unreadable'} or not item.get('reason'):
                    raise ValueError('missing image decision/reason')
                if item['decision'] != 'keep':
                    if item.get('file'):
                        raise ValueError('dropped image has a final file')
                    continue
                asset = within(batch, item['file'])
                if not asset.is_relative_to((batch / 'assets').resolve()) or checksum(asset) != item['sha256']:
                    raise ValueError('unsafe image path or checksum mismatch')
                if published and project:
                    published_asset = within(Path(project) / 'knowledge/site', prefix.strip('/') + '/' + asset.relative_to(batch / 'assets').as_posix())
                    if not published_asset.is_file() or checksum(published_asset) != checksum(asset):
                        raise ValueError('published image is missing or not identical')
                if asset in note_files:
                    raise ValueError('same image retained twice in one post')
                note_files.append(asset)
                counts['image_references'] += 1
                if asset not in kept_files and Image:
                    with Image.open(asset) as im:
                        im.verify()
                    counts['decoded_images'] += 1
                kept_files.add(asset)
            links = re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', body)
            expected = sorted(prefix + p.relative_to(batch / 'assets').as_posix() for p in note_files)
            if sorted(unquote(link) for link in links) != expected:
                raise ValueError('Markdown images do not match retained assets')
            counts['notes'] += 1
        except (ValueError, KeyError, OSError, yaml.YAMLError) as exc:
            errors.append(label + ': ' + (str(exc) if isinstance(exc, ValueError) else 'invalid file or metadata'))
    if manifest.get('inventory_file'):
        inventory = json.loads(within(batch, manifest['inventory_file']).read_text(encoding='utf-8'))
        if {str(row.get('id') or row.get('source_id')) for row in inventory} != seen_ids:
            errors.append('manifest does not account for the full inventory')
    if project and manifest.get('snapshot_file'):
        snapshot = json.loads(within(batch, manifest['snapshot_file']).read_text(encoding='utf-8'))
        for name, digest in snapshot.get('protected_files', {}).items():
            try:
                if checksum(within(Path(project) / 'knowledge', name)) != digest:
                    errors.append('original knowledge file changed: ' + name)
            except (ValueError, OSError):
                errors.append('original knowledge file missing/unsafe: ' + name)
    assets = {p.resolve() for p in (batch / 'assets').rglob('*') if p.is_file()}
    if assets != kept_files:
        errors.append('assets/ contains missing or unreferenced final files')
    return {'notes': counts['notes'], 'image_references': counts['image_references'], 'unique_assets': len(kept_files),
            'decoded_images': counts['decoded_images'], 'image_decoder_available': Image is not None,
            'statuses': {key: counts[key] for key in sorted(allowed) if counts[key]},
            'complete': not errors and not counts['pending'] and not counts['failed'], 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    scan = sub.add_parser('scan')
    scan.add_argument('--project', type=Path, required=True)
    scan.add_argument('--prefix', choices=['L', 'I'], default='L')
    scan.add_argument('--reserved', type=Path)
    scan.add_argument('--git-history', action='store_true')
    scan.add_argument('--output', type=Path)
    validate = sub.add_parser('validate')
    validate.add_argument('--batch', type=Path, required=True)
    validate.add_argument('--project', type=Path)
    validate.add_argument('--published', action='store_true')
    args = parser.parse_args()
    if args.command == 'scan':
        history = None
        if args.git_history:
            run = subprocess.run(['git', '-C', str(args.project), 'log', '--all', '--format=', '-p', '--', 'knowledge'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
            if run.returncode == 0:
                history = run.stdout
        result = scan_project(args.project, args.prefix, args.reserved, history)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        result = validate_batch(args.batch, args.project, args.published)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['errors']))


if __name__ == '__main__':
    main()
