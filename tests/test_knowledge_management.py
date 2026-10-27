import threading
from types import SimpleNamespace

import pytest
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import select
from packages.rag import knowledge
from services.api.auth import current_user
from services.api.db import Base, Document, Chunk, Record, make_database
from services.api.routes_knowledge import router
from services.api.routes_knowledge_management import router as management_router


@pytest.fixture
def managed(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@fixture.test')
    root=tmp_path/'knowledge';root.mkdir()
    for n in [1,2]:
        meta={'id':f'research-l{n:02d}','title':f'原始资料{n}','kind':'learning','permission':'public_display','quality_status':'unverified','source_type':'original_research_note','source_note_id':f'L{n:02d}','role_tags':['gtm'],'industry_tags':[],'source_url':'https://www.xiaohongshu.com/explore/'+str(n)*24,'source_author':'测试作者','excerpt':'原始库存方案'}
        (root/f'item{n}.md').write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True)+f'---\n# 原始资料{n}\n\n原始库存方案{n}，解释补货和渠道。',encoding='utf-8')
    engine,factory=make_database('sqlite://');Base.metadata.create_all(engine)
    with factory() as db:knowledge.ingest(db,root)
    app=FastAPI();app.state.db=factory;app.state.mutation_lock=threading.Lock();app.include_router(router);app.include_router(management_router)
    def user(request: Request):
        token=request.headers.get('Authorization','')
        if token=='Bearer admin':return SimpleNamespace(id='admin',email='admin@fixture.test')
        if token=='Bearer reader':return SimpleNamespace(id='reader',email='reader@fixture.test')
        raise HTTPException(401,'请先登录')
    app.dependency_overrides[current_user]=user
    with TestClient(app) as client:
        yield client,factory,root
    engine.dispose()


def payload(client):
    row=client.get('/api/v1/knowledge/documents/research-l01').json()
    return {'title':'修改后的资料','excerpt':'新内容：渠道试销验证','body':'# 修改后的资料\n\n渠道试销验证 zigzaglaunchsample：先小范围试销再滚动补货。','expected_sha256':row['sha256']}


def test_manage_permissions_and_scope(managed):
    client,factory,root=managed
    assert client.get('/api/v1/knowledge/capabilities').status_code==401
    assert client.get('/api/v1/knowledge/capabilities',headers={'Authorization':'Bearer reader'}).json()['can_manage_learning'] is False
    assert client.get('/api/v1/knowledge/capabilities',headers={'Authorization':'Bearer admin'}).json()['can_manage_learning'] is True
    for headers,expected in [({},401),({'Authorization':'Bearer reader'},403)]:
        assert client.put('/api/v1/knowledge/documents/research-l01',json=payload(client),headers=headers).status_code==expected
        assert client.delete('/api/v1/knowledge/documents/research-l01?expected_sha256=x',headers=headers).status_code==expected
    with factory() as db:
        row=db.get(Document,'research-l02');row.meta={**row.meta,'source_type':'site_reference'};db.commit()
    assert client.put('/api/v1/knowledge/documents/research-l02',json=payload(client),headers={'Authorization':'Bearer admin'}).status_code==403


def test_edit_updates_shared_detail_and_rag_and_survives_ingest(managed):
    client,factory,root=managed
    original=(root/'item1.md').read_bytes()
    before=client.get('/api/v1/knowledge/documents/research-l01').json()
    response=client.put('/api/v1/knowledge/documents/research-l01',json=payload(client),headers={'Authorization':'Bearer admin'})
    assert response.status_code==200,response.text
    row=response.json();assert row['id']==before['id'] and row['meta']['source_note_id']=='L01'
    assert row['sha256']!=before['sha256']
    with factory() as db:
        assert knowledge.search(db,'zigzaglaunchsample')[0]['doc_id']=='research-l01'
        knowledge.ingest(db,root)
        assert db.get(Document,'research-l01').body==row['body']
    assert (root/'item1.md').read_bytes()==original
    assert client.get('/api/v1/knowledge/documents/research-l01').json()['title']=='修改后的资料'


def test_delete_removes_shared_detail_and_chunks_and_does_not_resurrect(managed):
    client,factory,root=managed
    before=client.get('/api/v1/knowledge/documents/research-l01').json()
    response=client.delete('/api/v1/knowledge/documents/research-l01',params={'expected_sha256':before['sha256']},headers={'Authorization':'Bearer admin'})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/knowledge/documents/research-l01').status_code==404
    with factory() as db:
        assert not list(db.scalars(select(Chunk).where(Chunk.doc_id=='research-l01')))
        knowledge.ingest(db,root)
        assert db.get(Document,'research-l01') is None
    assert (root/'item1.md').exists()
    assert client.get('/api/v1/knowledge/documents').json()['total']==1


def test_stale_edit_or_delete_cannot_overwrite_latest_version(managed):
    client,_,_=managed
    update=payload(client)
    assert client.put('/api/v1/knowledge/documents/research-l01',json=update,headers={'Authorization':'Bearer admin'}).status_code==200
    assert client.put('/api/v1/knowledge/documents/research-l01',json=update,headers={'Authorization':'Bearer admin'}).status_code==409
    assert client.delete('/api/v1/knowledge/documents/research-l01',params={'expected_sha256':update['expected_sha256']},headers={'Authorization':'Bearer admin'}).status_code==409


def test_embedding_failure_keeps_previous_document_and_override_atomic(managed,monkeypatch):
    client,factory,_=managed
    before=client.get('/api/v1/knowledge/documents/research-l01').json()
    class Failed:
        enabled=True
        def embed(self,texts):raise RuntimeError('test failure')
    monkeypatch.setattr(knowledge,'EmbeddingProvider',Failed)
    response=client.put('/api/v1/knowledge/documents/research-l01',json=payload(client),headers={'Authorization':'Bearer admin'})
    assert response.status_code==503
    assert client.get('/api/v1/knowledge/documents/research-l01').json()==before
    with factory() as db:assert not list(db.scalars(select(Record).where(Record.kind=='knowledge_override')))
