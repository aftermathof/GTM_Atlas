import uuid
import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app


def account(client):
    result = client.post('/api/v1/auth/register', json={'email': f'{uuid.uuid4()}@example.test', 'password': 'safe-test-password-123'}).json()
    return {'Authorization': 'Bearer ' + result['token']}


def test_chat_restores_resets_context_and_isolates_owners(monkeypatch):
    captured = []
    def answer(db, body, private=None, history=None):
        captured.append(history or [])
        return {'answer': 'answer', 'citations': [], 'trace': [], 'provider': 'mock', 'model': 'test'}
    monkeypatch.setattr('services.api.routes_knowledge.answer_question', answer)
    with TestClient(create_app('sqlite://')) as client:
        first, other = account(client), account(client)
        r = client.post('/api/v1/ai/chat', headers=first, json={'message': 'GTM first'})
        assert r.status_code == 200
        thread = r.json()['conversation_id']
        r = client.post('/api/v1/ai/chat', headers=first, json={'message': 'follow up', 'conversation_id': thread})
        assert r.status_code == 200
        assert captured[-1][0]['question'] == 'GTM first'
        restored = client.get(f'/api/v1/ai/conversations/{thread}', headers=first).json()
        assert len(restored['messages']) == 2
        assert client.get(f'/api/v1/ai/conversations/{thread}', headers=other).status_code == 404
        assert client.post('/api/v1/ai/chat', headers=other, json={'message': 'steal', 'conversation_id': thread}).status_code == 404
        assert client.post('/api/v1/ai/chat', headers=first, json={'message': 'wrong scope', 'scope': 'article', 'conversation_id': thread}).status_code == 409
        assert client.post(f'/api/v1/ai/conversations/{thread}/reset', headers=first).status_code == 200
        client.post('/api/v1/ai/chat', headers=first, json={'message': 'after reset', 'conversation_id': thread})
        assert captured[-1] == []
        assert len(client.get(f'/api/v1/ai/conversations/{thread}', headers=first).json()['messages']) == 3
        second = client.post('/api/v1/ai/chat', headers=first, json={'message': 'new chat'}).json()['conversation_id']
        assert second != thread
        assert client.delete(f'/api/v1/ai/conversations/{thread}', headers=other).status_code == 404
        assert client.delete(f'/api/v1/ai/conversations/{thread}', headers=first).status_code == 200
        assert client.get(f'/api/v1/ai/conversations/{thread}', headers=first).status_code == 404
        assert client.get(f'/api/v1/ai/conversations/{second}', headers=first).status_code == 200


def test_supabase_tokens_are_validated_and_password_is_not_locally_saved(monkeypatch):
    import httpx
    from services.api.db import User
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-test-key')
    owner = str(uuid.uuid4())
    def remote(request):
        if request.url.path == '/auth/v1/user' and request.headers.get('authorization') == 'Bearer valid':
            return httpx.Response(200, json={'id': owner, 'email': 'supabase@example.test'})
        return httpx.Response(401, json={'message': 'invalid'})
    # Only the network boundary is mocked; real route and owner checks run.
    monkeypatch.setattr('services.api.supabase.request', remote)
    app = create_app('sqlite://')
    with TestClient(app) as client:
        with app.state.db() as db:
            db.add(User(id=owner, email='supabase@example.test', password_hash=''))
            db.commit()
        assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer forged'}).status_code == 401
        r = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer valid'})
        assert r.status_code == 200 and r.json()['id'] == owner
        assert client.post('/api/v1/auth/login', json={'email': 'supabase@example.test', 'password': 'safe-test-password-123'}).status_code == 401


def test_private_storage_roundtrip_and_failure(monkeypatch):
    import httpx
    from services.api.storage import put_private, get_private, delete_private
    monkeypatch.setenv('STORAGE_MODE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'secret-test-key')
    objects = {}
    def remote(request):
        assert request.headers['authorization'] == 'Bearer secret-test-key'
        key = request.url.path
        if request.method == 'POST':
            objects[key] = request.content
            return httpx.Response(200, json={})
        if request.method == 'DELETE':
            import json
            assert key == '/storage/v1/object/gtm-private'
            for prefix in json.loads(request.content)['prefixes']:
                objects.pop(key + '/' + prefix, None)
            return httpx.Response(200, json={})
        return httpx.Response(200, content=objects[key]) if key in objects else httpx.Response(404)
    monkeypatch.setattr('services.api.supabase.request', remote)
    key = 'owner/uploads/resume-id'
    put_private(key, b'resume')
    assert get_private(key) == b'resume'
    delete_private(key)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        get_private(key)
    assert error.value.status_code == 404


def test_chat_survives_restart_and_bounds_model_history(tmp_path, monkeypatch):
    captured = []
    def answer(db, body, private=None, history=None):
        captured.append(history or [])
        return {'answer': 'a' * 4000, 'citations': [], 'trace': []}
    monkeypatch.setattr('services.api.routes_knowledge.answer_question', answer)
    url = 'sqlite:///' + (tmp_path / 'chat.db').as_posix()
    with TestClient(create_app(url)) as client:
        headers = account(client)
        conversation = None
        for n in range(12):
            result = client.post('/api/v1/ai/chat', headers=headers, json={'message': 'q' * 2000, 'conversation_id': conversation})
            assert result.status_code == 200
            conversation = result.json()['conversation_id']
        assert len(captured[-1]) == 10
        assert all(len(m['question']) <= 500 and len(m['answer']) <= 1000 for m in captured[-1])
    with TestClient(create_app(url)) as client:
        row = client.get('/api/v1/ai/conversations/' + conversation, headers=headers).json()
        assert len(row['messages']) == 12
        assert len(row['messages'][0]['response']['answer']) == 4000
        assert len(client.get('/api/v1/history', headers=headers).json()) == 1


def test_private_resume_storage_and_delete_are_owner_checked(monkeypatch):
    from services.api import storage
    objects = {}
    monkeypatch.setattr(storage, 'enabled', lambda: True)
    monkeypatch.setattr(storage, 'put_private', lambda key, content, *args: objects.update({key: content}))
    monkeypatch.setattr(storage, 'get_private', lambda key: objects[key])
    monkeypatch.setattr(storage, 'delete_private', lambda key: objects.pop(key, None))
    with TestClient(create_app('sqlite://')) as client:
        a, b = account(client), account(client)
        body = '姓名：测试同学\n教育：示例大学\n项目：协作完成AI培训资料整理'
        resume = client.post('/api/v1/career/resumes', headers=a, files={'file': ('resume.txt', body.encode(), 'text/plain')}).json()
        rid = resume['id']
        assert client.get(f'/api/v1/career/resumes/{rid}/original', headers=b).status_code == 404
        assert client.get(f'/api/v1/career/resumes/{rid}/original', headers=a).content == body.encode()
        session = client.post('/api/v1/career/sessions', headers=a, json={'resume_id': rid}).json()
        sid = session['id']
        chat = client.post('/api/v1/ai/chat', headers=a, json={'message': '项目如何表达', 'scope': 'career', 'session_id': sid}).json()
        assert 'conversation_id' in chat
        assert client.delete(f'/api/v1/career/sessions/{sid}', headers=b).status_code == 404
        assert objects
        assert client.delete(f'/api/v1/career/sessions/{sid}', headers=a).status_code == 200
        assert not objects
        assert client.get('/api/v1/ai/conversations/' + chat['conversation_id'], headers=a).status_code == 404
        from services.api.db import Record
        from sqlalchemy import select
        with client.app.state.db() as db:
            assert not list(db.scalars(select(Record).where(Record.kind == 'conversation')))


def test_mock_delete_preserves_other_users_records():
    with TestClient(create_app('sqlite://')) as client:
        a, b = account(client), account(client)
        sid = client.post('/api/v1/mock/sessions', headers=a, json={'count': 3}).json()['id']
        assert client.delete(f'/api/v1/mock/sessions/{sid}', headers=b).status_code == 404
        assert client.delete(f'/api/v1/mock/sessions/{sid}', headers=a).status_code == 200
        assert client.get(f'/api/v1/mock/sessions/{sid}', headers=a).status_code == 404


def test_resume_delete_removes_failed_worker_payloads():
    from services.api.config import data_dir
    from services.api.store import save
    with TestClient(create_app('sqlite://')) as client:
        headers = account(client)
        owner = client.get('/api/v1/auth/me', headers=headers).json()['id']
        with client.app.state.db() as db:
            original = save(db, owner, 'resume', {})
            career = save(db, owner, 'career', {'context': {'resume_id': original.id}})
            version = save(db, owner, 'resume_version', {}, career.id)
            db.commit()
        queue = data_dir() / 'render-queue'
        queue.mkdir(exist_ok=True)
        files = [queue / (version.id + suffix) for suffix in ('.request.failed', '.request.result.tmp')]
        for file in files:
            file.write_text('private resume facts', encoding='utf-8')
        assert client.delete(f'/api/v1/career/sessions/{career.id}', headers=headers).status_code == 200
        assert not any(file.exists() for file in files)


def test_supabase_signup_confirmation_login_refresh_and_logout(monkeypatch):
    import json
    import httpx
    from services.api.db import User, Token
    from sqlalchemy import select
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-test-key')
    owner = str(uuid.uuid4())
    def remote(request):
        assert request.headers['apikey'] == 'public-test-key'
        if request.url.path.endswith('/signup'):
            return httpx.Response(200, json={'user': {'id': owner}})
        if request.url.path.endswith('/token'):
            payload = json.loads(request.content)
            if request.url.params['grant_type'] == 'refresh_token':
                assert payload['refresh_token'] == 'refresh-1'
            else:
                assert payload['email'] == 'supabase@example.test'
                assert payload['password'] == 'safe-test-password-123'
            return httpx.Response(200, json={'access_token':'access-1','refresh_token':'refresh-1','expires_in':3600})
        if request.url.path.endswith('/user'):
            assert request.headers['authorization'] == 'Bearer access-1'
            return httpx.Response(200, json={'id':owner})
        assert request.url.path.endswith('/logout')
        return httpx.Response(204)
    monkeypatch.setattr('services.api.supabase.request', remote)
    app = create_app('sqlite://')
    with TestClient(app) as client:
        credentials = {'email':'supabase@example.test','password':'safe-test-password-123'}
        assert client.post('/api/v1/auth/register', json=credentials).json()['confirmation_required']
        with app.state.db() as db:
            assert not list(db.scalars(select(User)))
            # Simulate SQL Auth trigger, which is executed by the remote database.
            db.add(User(id=owner,email=credentials['email'],password_hash=''))
            db.commit()
        assert client.post('/api/v1/auth/login', json=credentials).json()['token'] == 'access-1'
        assert client.post('/api/v1/auth/refresh', json={'refresh_token':'refresh-1'}).json()['refresh_token'] == 'refresh-1'
        assert client.post('/api/v1/auth/logout', headers={'Authorization':'Bearer access-1'}).status_code == 200
        with app.state.db() as db:
            assert db.get(User, owner).password_hash == ''
            assert not list(db.scalars(select(Token)))
