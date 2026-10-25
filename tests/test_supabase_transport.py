import httpx

from services.api import supabase


def test_supabase_requests_reuse_transport_and_close_cleanly(monkeypatch):
    clients = []
    original_client = httpx.Client

    def create_client(**kwargs):
        client = original_client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={'ok': True}),
        ), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(supabase.httpx, 'Client', create_client)
    try:
        for _ in range(2):
            assert supabase.request(httpx.Request('GET', 'https://example.test')).json()['ok']
        assert len(clients) == 1
        assert not clients[0].is_closed
    finally:
        if hasattr(supabase, 'close_client'):
            supabase.close_client()
    assert clients[0].is_closed


import pytest
from fastapi import HTTPException


@pytest.mark.parametrize('status,code,expected', [
    (400,'invalid_credentials','邮箱或密码不正确，请检查后重试。'),
    (401,'invalid_credentials','邮箱或密码不正确，请检查后重试。'),
    (400,'email_not_confirmed','邮箱尚未验证，请先点击注册邮件中的验证链接，再返回登录。'),
    (403,'email_not_confirmed','邮箱尚未验证，请先点击注册邮件中的验证链接，再返回登录。'),
    (422,'weak_password','密码不符合安全要求，请更换密码'),
    (400,'same_password','新密码不能与原密码相同，请更换新密码。'),
    (429,'over_email_send_rate_limit','邮件发送已达到服务限额，请稍后重试或检查 SMTP 发送额度。'),
    (400,'unknown_auth_error','账号操作未完成，请稍后重试。'),
])
def test_auth_errors_are_classified_by_provider_code(monkeypatch,status,code,expected):
    monkeypatch.setenv('SUPABASE_URL','https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY','test-key')
    monkeypatch.setattr(supabase,'request',lambda request:httpx.Response(status,json={'error_code':code,'msg':'private upstream detail'}))
    with pytest.raises(HTTPException) as error:
        supabase.call('POST','/auth/v1/token?grant_type=password',payload={'email':'user@example.test','password':'private-password'})
    assert error.value.detail==expected
    assert 'private' not in str(error.value.detail)
    assert error.value.status_code==(429 if status==429 else 400)


def test_malformed_auth_error_is_not_misreported_as_wrong_password(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY','test-key')
    monkeypatch.setattr(supabase,'request',lambda request:httpx.Response(400,text='not json'))
    with pytest.raises(HTTPException) as error:
        supabase.call('POST','/auth/v1/signup')
    assert error.value.detail=='账号操作未完成，请稍后重试。'


def test_expired_session_and_private_storage_errors_keep_their_original_meaning(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY','test-key')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY','service-test-key')
    monkeypatch.setattr(supabase,'request',lambda request:httpx.Response(401,json={'error_code':'bad_jwt'}))
    with pytest.raises(HTTPException) as session:
        supabase.call('GET','/auth/v1/user',token='expired')
    assert session.value.status_code==401
    assert session.value.detail=='登录凭证无效或已过期'
    with pytest.raises(HTTPException) as private:
        supabase.call('GET','/storage/v1/object/private/file',service=True)
    assert private.value.status_code==503
    assert private.value.detail=='私有存储鉴权失败'
