import json
import re
from html import unescape


import yaml

from packages.rag.reference_sources import reference_documents
from services.api.config import ROOT


def test_handbook_entry_precedes_foundation_and_source_pages_still_exist():
    directory = ROOT/'knowledge/site/gtm-sop'
    home = (directory/'index.html').read_text(encoding='utf-8')
    assert home.index('id="handbook"') < home.index('class="foundation"')
    assert 'href="handbook-index.html"' in home
    assert len(list(directory.glob('source-*.html'))) == 15
    for page in directory.glob('source-*.html'):
        assert 'href="handbook-index.html"' in page.read_text(encoding='utf-8')


def test_handbook_accounts_for_every_pdf_page_and_does_not_publish_covers():
    directory = ROOT/'knowledge/site/gtm-sop'
    manifest = json.loads((directory/'handbook-manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['chapters']) == 8
    kept = [p for chapter in manifest['chapters'] for p in chapter['pages']]
    assert len(kept) == len(set(kept))
    omitted = [item['page'] for item in manifest['omitted']]
    assert set(kept).isdisjoint(omitted)
    assert set(kept+omitted) == set(range(1,62))
    assert {1,2,3,11,14,34,40,49,55,59,61} <= set(omitted)
    for chapter in manifest['chapters']:
        raw = (directory/chapter['file']).read_text(encoding='utf-8')
        assert '<main' in raw
        assert '感谢聆听' not in raw
        assert 'fonts.googleapis.com' not in raw and 'unpkg.com' not in raw
        assert 'C:\\Users' not in raw
        for page in chapter['pages']:
            assert f'id="page-{page}"' in raw


def test_handbook_chapters_are_indexed_with_author_and_actual_content():
    docs = [(p, raw) for p, raw in reference_documents(ROOT) if '/gtm-sop/handbook-chapter-' in p]
    assert len(docs) == 8
    bodies = []
    for path, raw in docs:
        meta = yaml.safe_load(raw.split('---', 2)[1])
        assert meta['source_author'] == '晴子西西'
        assert meta['resource_group'] == 'sop'
        assert meta['source_url'].startswith('/gtm-sop/handbook-chapter-')
        bodies.append(raw.split('---', 2)[2])
    text = '\n'.join(bodies)
    for word in ['商业成功','产品路标','进销存','价值定价','市场洞察','月度','Kick Off','Consumer Profile']:
        assert word in text
    assert '感谢聆听' not in text


def test_finance_examples_and_all_glossary_terms_survive_pdf_cleanup():
    directory = ROOT/'knowledge/site/gtm-sop'

    def rows(chapter, page):
        raw = (directory/f'handbook-chapter-{chapter:02d}.html').read_text(encoding='utf-8')
        section = raw.split(f'id="page-{page}"', 1)[1].split('</section>', 1)[0]
        found = []
        for row in re.findall(r'<tr>(.*?)</tr>', section, re.S):
            cells = [unescape(re.sub('<[^>]+>', '', cell)).strip() for cell in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
            if any(cells):
                found.append(cells)
        return found

    short_term = rows(3, 32)
    assert len(short_term) == 10  # Header plus nine original price examples.
    assert any(r[0:2] == ['产品A', '899'] and r[-2:] == ['-6', '-1%'] for r in short_term)
    lifecycle = rows(3, 33)
    assert len(lifecycle) == 9  # Header plus eight original lifecycle examples.
    assert any(r[0:2] == ['产品A', '869'] and r[-2:] == ['315773', '-14227'] for r in lifecycle)
    glossary = rows(8, 60)
    assert len(glossary) == 37
    assert ['产品', 'Consumer Profile', '用户画像'] in glossary
    assert ['销售', 'Shipment', '出货'] in glossary

