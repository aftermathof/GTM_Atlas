from types import SimpleNamespace
from fastapi import HTTPException
from tests.test_workflows import client


def test_reset_request_uses_only_trusted_frontend_and_does_not_return_tokens(client, monkeypatch):
    monkeypatch.setenv('AUTH_MODE','supabase')
    monkeypatch.setenv('ALLOWED_ORIGINS','https://atlas.example')
    calls=[]
    monkeypatch.setattr('services.api.supabase.call', lambda method,path,**kwargs: calls.append((method,path,kwargs)) or SimpleNamespace(json=lambda:{}))
    response=client.post('/api/v1/auth/request-password-reset',json={'email':'USER@example.test'},headers={'Origin':'https://atlas.example'})
    assert response.status_code==200
    assert '重置' in response.json()['message']
    assert calls[0][0]=='POST'
    assert calls[0][1].startswith('/auth/v1/recover?redirect_to=')
    assert 'https%3A%2F%2Fatlas.example%2Flogin' in calls[0][1]
    assert calls[0][2]['payload']=={'email':'user@example.test'}
    assert set(response.json())=={'message'}
    denied=client.post('/api/v1/auth/request-password-reset',json={'email':'user@example.test'},headers={'Origin':'https://evil.example'})
    assert denied.status_code==403
    assert len(calls)==1


def test_reset_password_requires_valid_recovery_token_and_handles_expiry(client,monkeypatch):
    monkeypatch.setenv('AUTH_MODE','supabase')
    calls=[]
    monkeypatch.setattr('services.api.supabase.call', lambda method,path,**kwargs: calls.append((method,path,kwargs)) or SimpleNamespace(json=lambda:{}))
    result=client.post('/api/v1/auth/reset-password',json={'recovery_token':'recovery-access','password':'new-password'})
    assert result.status_code==200
    assert calls==[('PUT','/auth/v1/user',{'token':'recovery-access','payload':{'password':'new-password'}})]
    assert 'new-password' not in result.text and 'recovery-access' not in result.text
    def expired(*args,**kwargs): raise HTTPException(401,'expired')
    monkeypatch.setattr('services.api.supabase.call',expired)
    result=client.post('/api/v1/auth/reset-password',json={'recovery_token':'expired','password':'new-password'})
    assert result.status_code==400
    assert '重新' in result.json()['detail']
    assert client.post('/api/v1/auth/reset-password',json={'password':'new-password'}).status_code==422


def test_local_auth_cannot_reset_password_by_email_alone(client):
    response=client.post('/api/v1/auth/request-password-reset',json={'email':'user@example.test'})
    assert response.status_code==503
