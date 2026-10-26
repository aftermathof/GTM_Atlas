import httpx
from services.api import supabase
from services.api.db import User
from tests.test_workflows import client


def test_supabase_login_returns_profile_without_second_remote_validation(client, monkeypatch):
    with client.app.state.db() as db:
        db.add(User(id='fast-user', email='fast@example.test', password_hash='', preferences={'role': 'pmm'}))
        db.commit()
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    calls = []
    def remote(method, path, **kwargs):
        calls.append(path)
        assert path == '/auth/v1/token?grant_type=password'
        return httpx.Response(200, json={'access_token': 'access', 'refresh_token': 'refresh',
                                       'user': {'id': 'fast-user', 'email': 'fast@example.test'}})
    monkeypatch.setattr(supabase, 'call', remote)
    response = client.post('/api/v1/auth/login', json={'email': 'fast@example.test', 'password': 'test'})
    assert response.status_code == 200
    assert response.json()['user'] == {'id': 'fast-user', 'email': 'fast@example.test', 'preferences': {'role': 'pmm'}}
    assert calls == ['/auth/v1/token?grant_type=password']


def test_supabase_logout_only_calls_revocation_not_user_lookup(client, monkeypatch):
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    calls = []
    def remote(method, path, **kwargs):
        calls.append((method, path, kwargs['token']))
        assert path == '/auth/v1/logout?scope=local'
        return httpx.Response(204)
    monkeypatch.setattr(supabase, 'call', remote)
    response = client.post('/api/v1/auth/logout', headers={'Authorization': 'Bearer access'})
    assert response.status_code == 200
    assert calls == [('POST', '/auth/v1/logout?scope=local', 'access')]
    assert client.post('/api/v1/auth/logout').status_code == 401
