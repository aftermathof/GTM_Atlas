import json
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.rag import knowledge
from packages.rag.reference_sources import reference_documents
from services.api.db import Base, Document, make_database
from services.api.routes_knowledge import router
from packages.learning.graph import answer_question
from services.api.schemas import Chat


def reference_project(root):
    overview = root / 'apps/web/public/gtm-overview'
    overview.mkdir(parents=True)
    (overview / 'index.html').write_text('''<html><head><title>GTM概览</title><style>SECRET STYLE</style></head>
<body><nav>SECRET NAV</nav><main><h1>产品经营</h1><p>新品上市与经营节奏。</p>
<h2>上市流程</h2><ol><li>确定目标市场</li><li>复盘经营结果</li></ol>
<table><tr><th>环节</th><th>产物</th></tr><tr><td>定位</td><td>卖点</td></tr></table>
<script>SECRET SCRIPT</script></main><footer>SECRET FOOTER</footer></body></html>''', encoding='utf-8')
    content = root / 'apps/web/src/content'
    content.mkdir(parents=True)
    (content / 'gtm-glossary.json').write_text(json.dumps([
        {'term': 'CAC', 'fullName': 'Customer Acquisition Cost', 'explanation': '客户获取成本需要统一统计口径。', 'example': '获客投入10000元，新增100位客户，CAC为100元。'}
    ], ensure_ascii=False), encoding='utf-8')
    return overview


def test_reference_extraction_preserves_content_and_omits_page_chrome(tmp_path):
    reference_project(tmp_path)
    docs = list(reference_documents(tmp_path))
    assert len(docs) == 2
    raw = '\n'.join(text for _, text in docs)
    for value in ['产品经营', '确定目标市场', '复盘经营结果', '定位', '卖点', 'Customer Acquisition Cost', 'CAC为100元']:
        assert value in raw
    assert 'SECRET' not in raw
    for _, text in docs:
        meta = yaml.safe_load(text.split('---', 2)[1])
        assert meta['permission'] == 'public_display'
        assert meta['catalog_visible'] is False
        assert meta['source_file_sha256']


def test_reference_sources_refresh_search_cite_and_stay_out_of_gallery(tmp_path, monkeypatch):
    overview = reference_project(tmp_path)
    source = tmp_path / 'knowledge'
    source.mkdir()
    monkeypatch.setattr(knowledge, 'EmbeddingProvider', lambda: type('Disabled', (), {'enabled': False})())
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.state.db = factory
    app.include_router(router)
    try:
        with factory() as db:
            report = knowledge.ingest(db, source, reference_root=tmp_path)
            assert report['indexed'] == 2
            assert knowledge.ingest(db, source, reference_root=tmp_path)['indexed'] == 0
            result = knowledge.search(db, 'CAC客户获取成本', role='pmm', industry='consumer_electronics')
            citation = next(item for item in result if item['doc_id'] == 'gtm-reference-glossary')
            assert citation['source_url'] == '/glossary'
            assert citation['url'] == '/learn/gtm-reference-glossary'
            answer = answer_question(db, Chat(message='解释CAC客户获取成本', scope='global'))
            assert any(item['doc_id'] == 'gtm-reference-glossary' for item in answer['citations'])
            overview_result = knowledge.search(db, '新品上市经营节奏')
            assert any(item['doc_id'] == 'gtm-reference-overview-index' for item in overview_result)
        with TestClient(app) as client:
            assert client.get('/api/v1/knowledge/documents').json()['total'] == 0
            assert client.get(citation['url'].replace('/learn/', '/api/v1/knowledge/documents/')).status_code == 200
        path = overview / 'index.html'
        path.write_text(path.read_text(encoding='utf-8').replace('新品上市与经营节奏', '新品市场进入方案'), encoding='utf-8')
        with factory() as db:
            assert knowledge.ingest(db, source, reference_root=tmp_path)['indexed'] == 1
            assert '新品市场进入方案' in db.get(Document, 'gtm-reference-overview-index').body
            path.unlink()
            assert knowledge.ingest(db, source, reference_root=tmp_path)['deleted'] == 1
            assert db.get(Document, 'gtm-reference-overview-index') is None
    finally:
        engine.dispose()


def test_malformed_reference_is_reported_instead_of_silently_dropped(tmp_path):
    reference_project(tmp_path)
    path = tmp_path / 'apps/web/src/content/gtm-glossary.json'
    path.write_text('[{"term":"CAC"}]', encoding='utf-8')
    with pytest.raises(ValueError, match='glossary'):
        list(reference_documents(tmp_path))
