from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.sql import Select

from packages.rag.knowledge import search
from services.api.db import Base, Chunk, Document, make_database
from services.api.routes_knowledge import router


def test_catalog_reads_summaries_and_preserves_full_text_filter_and_fallback():
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    body = '# Heading\n- provenance\n\nFirst readable paragraph.\n' + 'details ' * 500 + 'unique needle'
    with factory() as db:
        for did, excerpt in [('summary', 'Saved summary'), ('fallback', '')]:
            db.add(Document(id=did, title=did, kind='learning', body=body, sha256='hash', path=did,
                            meta={'permission': 'public_display', 'excerpt': excerpt}))
        db.commit()
    reads = []
    def capture(conn, statement, *args):
        if isinstance(statement, Select):
            reads.append(list(statement.selected_columns.keys()))
    event.listen(engine, 'before_execute', capture)
    app = FastAPI()
    app.state.db = factory
    app.include_router(router)
    try:
        with TestClient(app) as client:
            items = client.get('/api/v1/knowledge/documents?q=unique%20needle').json()['items']
            assert len(items) == 2
            by_id = {item['id']: item for item in items}
            assert by_id['summary']['excerpt'] == 'Saved summary'
            assert by_id['fallback']['excerpt'] == 'First readable paragraph.'
            assert by_id['summary']['minutes'] == max(3, len(body) // 350)
        assert all('body' not in columns and 'sha256' not in columns for columns in reads)
    finally:
        engine.dispose()


def test_retrieval_does_not_transfer_full_document_bodies():
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    with factory() as db:
        db.add(Document(id='doc', title='CAC', kind='learning', body='long document ' * 10000,
                        sha256='hash', path='doc', meta={'permission': 'public_display', 'quality_status': 'user_provided'}))
        db.flush()
        db.add(Chunk(id='doc:0', doc_id='doc', heading='CAC', body='CAC customer acquisition cost'))
        db.commit()
    reads = []
    def capture(conn, cursor, statement, *args):
        reads.append(statement)
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        with factory() as db:
            result = search(db, 'CAC')
            assert result[0]['chunk_id'] == 'doc:0'
            assert result[0]['text'] == 'CAC customer acquisition cost'
        assert all('knowledge_documents.body' not in sql.split('FROM', 1)[0] for sql in reads)
    finally:
        engine.dispose()


def test_large_catalog_response_is_compressed():
    from services.api.main import create_app
    with TestClient(create_app('sqlite://')) as client:
        response = client.get('/api/v1/knowledge/documents?limit=100', headers={'Accept-Encoding': 'gzip'})
        assert response.status_code == 200
        assert response.headers['content-encoding'] == 'gzip'
        assert int(response.headers['content-length']) < len(response.content)
