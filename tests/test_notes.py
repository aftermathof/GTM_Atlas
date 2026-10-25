import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app
from packages.agent_core.providers import LLMProvider


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def account(client, name):
    response = client.post('/api/v1/auth/register', json={'email': name + '@example.test', 'password': 'test-pass'})
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_notes_crud_is_private_and_conflict_safe(client):
    a, b = account(client, 'notes-a'), account(client, 'notes-b')
    assert client.get('/api/v1/notes').status_code == 401
    note = client.post('/api/v1/notes', json={'title': '渠道复盘', 'body': '# 学习笔记\n- 行动'}, headers=a).json()
    nid = note['id']
    assert client.get('/api/v1/notes', headers=b).json() == []
    for method in ['get', 'put', 'delete']:
        kwargs = {'json': {'title': '偷改', 'body': '', 'revision': 1}} if method == 'put' else {}
        assert getattr(client, method)('/api/v1/notes/' + nid, headers=b, **kwargs).status_code == 404
    cards = client.get('/api/v1/notes', headers=a).json()
    assert cards[0]['title'] == '渠道复盘' and 'body' not in cards[0]
    update = {'title': '最新复盘', 'body': 'CAC 获客成本', 'revision': note['revision']}
    saved = client.put('/api/v1/notes/' + nid, json=update, headers=a)
    assert saved.status_code == 200
    assert saved.json()['revision'] == note['revision'] + 1
    assert client.put('/api/v1/notes/' + nid, json=update, headers=a).status_code == 409
    assert client.get('/api/v1/notes/' + nid, headers=a).json()['body'] == update['body']
    assert client.delete('/api/v1/notes/' + nid, headers=a).status_code == 200
    assert client.get('/api/v1/notes/' + nid, headers=a).status_code == 404


def test_note_input_limits(client):
    headers = account(client, 'notes-validation')
    for payload in [{'title': '   ', 'body': ''}, {'title': 'x' * 161, 'body': ''}, {'title': 'x', 'body': 'x' * 100001}]:
        assert client.post('/api/v1/notes', json=payload, headers=headers).status_code == 422


def test_ai_uses_current_owned_notes_and_never_indexes_publicly(client, monkeypatch):
    a, b = account(client, 'notes-ai-a'), account(client, 'notes-ai-b')
    note = client.post('/api/v1/notes', json={'title': '独家渠道策略', 'body': '北极星试点通过伙伴渠道验证。'}, headers=a).json()
    client.post('/api/v1/notes', json={'title': '北极星私密', 'body': 'OTHER_ACCOUNT_SECRET'}, headers=b)
    payloads = []

    def complete(self, task, payload):
        payloads.append(payload)
        evidence = [e for e in payload['evidence'] if e['kind'] == 'note']
        return '依据笔记 [' + evidence[0]['chunk_id'] + ']' if evidence else '没有相关笔记'

    monkeypatch.setattr(LLMProvider, 'complete', complete)
    response = client.post('/api/v1/ai/chat', json={'message': '北极星试点怎么做', 'scope': 'global'}, headers=a)
    assert response.status_code == 200
    assert response.json()['citations'][0]['url'] == '/notes/' + note['id']
    assert 'OTHER_ACCOUNT_SECRET' not in str(payloads[-1])
    assert all(e['permission'] == 'private' for e in payloads[-1]['evidence'] if e['kind'] == 'note')
    assert all(d['id'] != note['id'] for d in client.get('/api/v1/knowledge/documents').json()['items'])
    selected = {'message': '总结这篇笔记', 'scope': 'notes', 'document_id': note['id']}
    assert client.post('/api/v1/ai/chat', json=selected, headers=b).status_code == 404
    assert client.post('/api/v1/ai/chat', json=selected).status_code == 401
    assert client.post('/api/v1/ai/chat', json=selected, headers=a).json()['citations']
    client.put('/api/v1/notes/' + note['id'], json={'title': '已更新', 'body': 'NEW_CONTENT', 'revision': 1}, headers=a)
    client.post('/api/v1/ai/chat', json=selected, headers=a)
    assert 'NEW_CONTENT' in str(payloads[-1]) and '北极星试点通过' not in str(payloads[-1])
    client.delete('/api/v1/notes/' + note['id'], headers=a)
    assert client.post('/api/v1/ai/chat', json=selected, headers=a).status_code == 404
    client.post('/api/v1/ai/chat', json={'message': '北极星试点', 'scope': 'global'}, headers=a)
    assert not any(e['kind'] == 'note' for e in payloads[-1]['evidence'])
