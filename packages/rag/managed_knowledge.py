"""Persistent admin overrides for public learning notes; original Markdown stays intact."""
import hashlib
import yaml


def editable_learning(meta):
    return (meta.get('kind') == 'learning' and meta.get('permission') == 'public_display'
            and meta.get('source_type') == 'original_research_note' and meta.get('quality_status') != 'deprecated')


def managed_source(meta, change):
    meta = {k: str(v) if hasattr(v, "isoformat") else v for k, v in meta.items()}
    updated = {**meta, 'title': change['title'], 'excerpt': change['excerpt'],
               'managed_revision': change['revision'], 'managed_updated_at': change['updated_at']}
    body = change['body'].strip()
    raw = '---\n' + yaml.safe_dump(updated, allow_unicode=True, sort_keys=False) + '---\n' + body + '\n'
    return updated, body, hashlib.sha256(raw.encode('utf-8')).hexdigest()
