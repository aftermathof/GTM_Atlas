from packages.agent_core.providers import EmbeddingProvider
from packages.career.retrieval import career_evidence
from services.api.db import Base, Document, Chunk, make_database


def test_career_retrieval_embeds_the_same_query_once_per_request(monkeypatch):
    engine, factory = make_database('sqlite://')
    Base.metadata.create_all(engine)
    monkeypatch.setenv('EMBEDDING_MODEL', 'test-model')
    monkeypatch.setattr(EmbeddingProvider, 'enabled', property(lambda self: True))
    calls = []
    def embed(self, texts):
        calls.extend(texts)
        return [[1.0, 0.0] for _ in texts]
    monkeypatch.setattr(EmbeddingProvider, 'embed', embed)
    try:
        with factory() as db:
            for kind in ['jd', 'learning', 'interview']:
                db.add(Document(id=kind, title='用户调研', kind=kind, body='用户调研', path=kind, sha256='test', meta={'permission':'public_display','quality_status':'user_provided','role_tags':[],'industry_tags':[]}))
            db.flush()
            for kind in ['jd', 'learning', 'interview']:
                db.add(Chunk(id=kind+':0', doc_id=kind, heading='用户调研', body='用户调研', embedding=[1.0,0.0], embedding_model='test-model'))
            db.commit()
            first = career_evidence(db, {}, instruction='用户调研')
            assert {item['kind'] for item in first} == {'jd','learning','interview'}
            assert calls == ['用户调研']
            second = career_evidence(db, {}, instruction='渠道分析')
            assert calls == ['用户调研','渠道分析']
            assert len(second) == 3
    finally:
        engine.dispose()
