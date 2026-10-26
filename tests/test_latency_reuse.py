from tests.test_workflows import client, login
from services.api import routes_career


def test_unchanged_confirmation_reuses_analysis_but_edits_recompute(client, monkeypatch):
    headers = login(client)
    resume = client.post('/api/v1/career/resumes', headers=headers,
                         files={'file': ('resume.txt', '姓名：张三\n项目：负责渠道营销，组织用户访谈并分析渠道转化数据，核对实际销售结果'.encode(), 'text/plain')}).json()
    response = client.post('/api/v1/career/sessions', headers=headers,
                           json={'resume_id': resume['id'], 'role': 'kol_marketing', 'industry': 'consumer_electronics'})
    assert response.status_code == 200, response.text
    session = response.json()
    calls = []
    for name in ('extract_structure', 'diagnose'):
        original = getattr(routes_career, name)
        def wrapped(*args, _fn=original, _name=name, **kwargs):
            calls.append(_name)
            return _fn(*args, **kwargs)
        monkeypatch.setattr(routes_career, name, wrapped)
    path = '/api/v1/career/sessions/' + session['id'] + '/confirm-facts'
    result = client.post(path, headers=headers, json={'facts': session['facts']})
    assert result.status_code == 200, result.text
    assert calls == []
    facts = result.json()['facts']
    facts[0]['text'] = '姓名：李四'
    assert client.post(path, headers=headers, json={'facts': facts}).status_code == 200
    assert calls == ['extract_structure', 'diagnose']
    history = client.get('/api/v1/history?prefetch=true', headers=headers).json()
    saved = next(row for row in history if row['id'] == session['id'])
    assert saved['snapshot']['facts'][0]['text'] == '姓名：李四'
    assert saved['snapshot']['editing_blocks']
    assert saved['versions'] == []


def test_mock_embeddings_are_batched(monkeypatch):
    from packages.mock import graph
    from packages.agent_core.providers import EmbeddingProvider
    from services.api.schemas import MockSetup
    monkeypatch.setenv('EMBEDDING_BASE_URL', 'https://offline.invalid')
    monkeypatch.setenv('EMBEDDING_API_KEY', 'offline-test')
    monkeypatch.setenv('EMBEDDING_MODEL', 'test-vector')
    batches = []
    def embed(self, texts):
        batches.append(texts)
        return [[float(i)] for i in range(len(texts))]
    monkeypatch.setattr(EmbeddingProvider, 'embed', embed)
    def search(db, query, *args, **kwargs):
        assert ('test-vector', query) in kwargs.get('embedding_cache', {})
        return []
    monkeypatch.setattr(graph, 'search', search)
    result = graph.plan_interview(None, MockSetup(role='kol_marketing', industry='consumer_electronics', count=5))
    assert len(result['questions']) == 5
    assert len(batches) == 1
    assert len(batches[0]) == 5


def test_resume_parse_does_not_block_health(client, monkeypatch):
    import asyncio
    import threading
    import httpx
    headers = login(client)
    started, release = threading.Event(), threading.Event()
    original = routes_career.parse_resume
    def slow_parse(*args):
        started.set()
        assert release.wait(4)
        return original(*args)
    monkeypatch.setattr(routes_career, 'parse_resume', slow_parse)
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url='http://test') as api:
            upload = asyncio.create_task(api.post('/api/v1/career/resumes', headers=headers,
                files={'file': ('resume.txt', b'Name: Alice\nProject: channel research and interviews', 'text/plain')}))
            try:
                assert await asyncio.to_thread(started.wait, 2)
                assert not release.is_set()
                assert (await asyncio.wait_for(api.get('/api/v1/health'), 1)).status_code == 200
            finally:
                release.set()
                response = await upload
            assert response.status_code == 200, response.text
    asyncio.run(check())
