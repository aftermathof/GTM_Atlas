import yaml
from sqlalchemy import select

from packages.rag import knowledge
from packages.rag.reference_sources import reference_documents
from packages.learning.graph import answer_question
from services.api.config import ROOT
from services.api.db import Base, Document, make_database
from services.api.schemas import Chat


def book_project(root):
    directory = root / 'knowledge/site/gtm-book'
    directory.mkdir(parents=True)
    for number in range(1, 8):
        title = f'第{number}章 产品操盘' if number < 7 else '附录1 TR 与 GR 业务内容对应表'
        body = '辨定操营盘 ILFOR 五步法，辨机会、定目标、操上市、营销售、盘复盘。' if number == 3 else f'章节{number}的完整文字。'
        (directory / f'chapter-{number:02d}.html').write_text(
            f'<html><head><title>{title} · 爆品操盘GTM</title></head><body>'
            f'<aside>SECRET SIDEBAR</aside><main><article><h1>{title}</h1><p>{body}</p>'
            '<table><tr><td>概念评审</td><td>CDCP</td></tr></table></article>'
            '<nav>SECRET NEXT</nav><footer>SECRET FOOTER</footer></main>'
            '<script>SECRET SCRIPT</script></body></html>', encoding='utf-8')
    (directory / 'index.html').write_text('<main>Do not index a duplicate contents page</main>', encoding='utf-8')
    return directory


def test_book_chapters_extract_without_chrome_and_have_citable_metadata(tmp_path):
    book_project(tmp_path)
    documents = list(reference_documents(tmp_path))
    assert len(documents) == 7
    for path, raw in documents:
        meta = yaml.safe_load(raw.split('---', 2)[1])
        assert meta['id'].startswith('gtm-reference-book-chapter-')
        assert meta['source_author'] == '朱秋虎'
        assert meta['resource_group'] == 'book'
        assert meta['catalog_visible'] is False
        assert meta['universal_reference'] is True
        assert meta['source_url'].startswith('/gtm-book/chapter-')
        assert path.startswith('knowledge/site/gtm-book/')
        assert '概念评审' in raw and 'CDCP' in raw
        assert 'SECRET' not in raw


def test_book_is_retrieved_and_reaches_ai_evidence_with_role_and_industry_filters(tmp_path):
    book_project(tmp_path)
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    try:
        with factory() as db:
            assert knowledge.ingest(db, tmp_path/'knowledge', reference_root=tmp_path)['indexed'] == 7
            matches = knowledge.search(db, '辨定操营盘ILFOR五步法', role='gtm', industry='consumer_electronics')
            assert matches[0]['doc_id'] == 'gtm-reference-book-chapter-03'
            assert matches[0]['source_url'] == '/gtm-book/chapter-03.html'
            result = answer_question(db, Chat(message='辨定操营盘ILFOR五步法', scope='learning', role='gtm', industry='consumer_electronics'))
            assert any(item['doc_id'] == 'gtm-reference-book-chapter-03' for item in result['citations'])
            assert all(doc.meta['catalog_visible'] is False for doc in db.scalars(select(Document)))
    finally:
        engine.dispose()


def test_actual_book_all_chapters_loaded_and_no_untyped_markdown_in_site():
    documents = [(path, raw) for path, raw in reference_documents(ROOT) if path.startswith('knowledge/site/gtm-book/')]
    assert len(documents) == 7
    assert '辨定操营盘' in ''.join(raw for _, raw in documents)
    assert 'KANO' in ''.join(raw for _, raw in documents)
    assert not list((ROOT/'knowledge/site/gtm-book').glob('*.md'))
