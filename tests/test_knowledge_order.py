import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.db import Base, Document, Record, make_database
from services.api.routes_knowledge import router


@pytest.mark.parametrize(('kind', 'prefix'), [('jd', 'J'), ('interview', 'I'), ('learning', 'L')])
def test_numbered_resources_sort_before_pagination(kind, prefix, monkeypatch):
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.state.db = factory
    app.include_router(router)
    with factory() as db:
        for did, number in [('a', '02'), ('b', '10'), ('c', '01'), ('d', '100'), ('e', '11')]:
            db.add(Document(id=did, title=did, kind=kind, body=did, sha256=did, path=did,
                            meta={'permission': 'public_display', 'source_note_id': prefix + number}))
        db.commit()
    try:
        with TestClient(app) as client:
            result = client.get('/api/v1/knowledge/documents', params={'kind': kind, 'limit': 2}).json()
            assert result['total'] == 5
            assert [d['meta']['source_note_id'] for d in result['items']] == [prefix + '01', prefix + '02']
            page = client.get('/api/v1/knowledge/documents', params={'kind': kind, 'offset': 2}).json()
            assert [d['meta']['source_note_id'] for d in page['items']] == [prefix + '10', prefix + '11', prefix + '100']
            if kind == 'jd':
                from types import SimpleNamespace
                monkeypatch.setattr('services.api.routes_knowledge.current_user', lambda request: SimpleNamespace(id='owner'))
                with factory() as db:
                    db.add(Record(id='private', owner='owner', kind='private_jd', data={'title': 'My JD', 'body': 'Private content'}))
                    db.commit()
                items = client.get('/api/v1/knowledge/documents?kind=jd', headers={'Authorization': 'test'}).json()['items']
                assert items[0]['id'] == 'private'
                assert [d['meta']['source_note_id'] for d in items[1:]] == ['J01', 'J02', 'J10', 'J11', 'J100']
    finally:
        engine.dispose()
