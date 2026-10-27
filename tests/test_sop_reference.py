import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from packages.rag import knowledge
from packages.rag.reference_sources import reference_documents, MainText
from services.api.db import Base, make_database
from services.api.config import ROOT


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.targets.append(attrs[key])


def test_actual_sop_covers_every_source_and_all_local_links():
    root = ROOT / 'knowledge/site/gtm-sop'
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['documents']) == 15
    assert len(manifest['stages']) == 7
    assert sum(d.get('node_count', 0) for d in manifest['documents']) == 270
    assert sum(d.get('sheet_count', 0) for d in manifest['documents']) == 9
    for doc in manifest['documents']:
        assert hashlib.sha256((root / doc['source']).read_bytes()).hexdigest() == doc['sha256']
        raw = (root / doc['page']).read_text(encoding='utf-8')
        parser = MainText()
        parser.feed(raw)
        assert doc['title'] in parser.text()
        assert 'C:\\Users' not in raw
        assert '阅读边界与核对说明' not in raw and '整理者建议' not in raw
    for file in root.glob('*.html'):
        parser = Links()
        parser.feed(file.read_text(encoding='utf-8'))
        for target in parser.targets:
            url = urlsplit(target)
            assert not url.scheme and not url.netloc, target
            dest = root / unquote(url.path) if url.path else file
            assert dest.exists(), (file.name, target)
            if url.fragment:
                linked = Links()
                linked.feed(dest.read_text(encoding='utf-8'))
                assert unquote(url.fragment) in linked.ids, (file.name, target)


def test_sop_reference_extracts_text_and_retrieves_with_source_link(tmp_path, monkeypatch):
    directory = tmp_path / 'knowledge/site/gtm-sop'
    directory.mkdir(parents=True)
    (directory / 'source-01.html').write_text(
        '<title>PSI管理 · SOP</title><aside>SECRET目录</aside><main><h1>PSI管理</h1>'
        '<p>渠道库存滚动预测</p><table><tr><th>指标</th><th>公式</th></tr>'
        '<tr><td>DOS库存周转天数</td><td>=C6/C5*7</td></tr></table>'
        '<nav>SECRET下一页</nav></main>', encoding='utf-8')
    (directory / 'index.html').write_text('<main>不要重复索引目录</main>', encoding='utf-8')
    docs = list(reference_documents(tmp_path))
    assert len(docs) == 1
    meta = yaml.safe_load(docs[0][1].split('---', 2)[1])
    assert meta['resource_group'] == 'sop'
    assert meta['source_url'] == '/gtm-sop/source-01.html'
    assert meta['catalog_visible'] is False and meta['universal_reference'] is True
    assert 'SECRET' not in docs[0][1]
    assert '=C6/C5*7' in docs[0][1]
    monkeypatch.setattr(knowledge, 'EmbeddingProvider', lambda: type('Disabled', (), {'enabled': False})())
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    try:
        with factory() as db:
            assert knowledge.ingest(db, tmp_path/'knowledge', reference_root=tmp_path)['indexed'] == 1
            matches = knowledge.search(db, 'DOS库存周转天数', role='gtm', industry='consumer_electronics')
            assert matches[0]['source_url'] == '/gtm-sop/source-01.html'
    finally:
        engine.dispose()


def test_actual_sop_has_fifteen_distinct_reference_documents():
    docs = [(p, raw) for p, raw in reference_documents(ROOT) if p.startswith('knowledge/site/gtm-sop/source-')]
    assert len(docs) == 15
    assert len({yaml.safe_load(raw.split('---', 2)[1])['id'] for _, raw in docs}) == 15
    body = '\n'.join(raw for _, raw in docs)
    for term in ['GTM定位', 'DOS', '生命周期', 'GR6', '产品净收入', '渠道激励政策']:
        assert term in body


def test_every_original_mind_topic_and_xlsx_formula_is_in_the_reader():
    root = ROOT / 'knowledge/site/gtm-sop'
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    for doc in manifest['documents']:
        parser = MainText()
        parser.feed((root/doc['page']).read_text(encoding='utf-8'))
        body = re.sub(r'\s+', '', parser.text())
        original = root/doc['source']
        if original.suffix == '.xmind':
            with zipfile.ZipFile(original) as z:
                sheets = json.loads(z.read('content.json'))
            def check(topic):
                assert re.sub(r'\s+', '', topic.get('title', '')) in body
                for children in topic.get('children', {}).values():
                    for child in children:
                        check(child)
            for sheet in sheets:
                check(sheet['rootTopic'])
        elif original.suffix == '.xlsx':
            with zipfile.ZipFile(original) as z:
                if 'xl/sharedStrings.xml' in z.namelist():
                    for item in ET.fromstring(z.read('xl/sharedStrings.xml')):
                        text = ''.join(t.text or '' for t in item.findall('.//m:t', ns))
                        assert re.sub(r'\s+', '', text) in body
                for name in z.namelist():
                    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                        for formula in ET.fromstring(z.read(name)).findall('.//m:f', ns):
                            assert re.sub(r'\s+', '', '='+(formula.text or '')) in body
