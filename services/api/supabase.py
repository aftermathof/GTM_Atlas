"""Small server-side Supabase HTTP boundary; credentials never enter responses."""
import os
from functools import lru_cache
import httpx
from fastapi import HTTPException


def auth_mode():
    return os.getenv('AUTH_MODE', 'local')


@lru_cache(maxsize=1)
def http_client():
    return httpx.Client(timeout=30, follow_redirects=False)


def close_client():
    if http_client.cache_info().currsize:
        http_client().close()
        http_client.cache_clear()


def request(value):
    return http_client().send(value)


def call(method, path, *, token=None, service=False, payload=None, content=None, headers=None):
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY' if service else 'SUPABASE_ANON_KEY', '')
    if not url.startswith('https://') or not key:
        raise HTTPException(503, 'Supabase 服务配置不完整')
    values = {'apikey': key, 'Authorization': 'Bearer ' + (token or key), **(headers or {})}
    try:
        response = request(httpx.Request(method, url + path, headers=values, json=payload, content=content))
    except httpx.HTTPError:
        raise HTTPException(503, 'Supabase 暂时无法连接，请稍后重试')
    if response.is_error:
        if path.startswith('/auth/') and not service and response.status_code in {400, 401, 403, 422, 429}:
            try:
                details = response.json()
            except ValueError:
                details = {}
            code = (details.get('error_code') or details.get('code')) if isinstance(details, dict) else None
            messages = {
                'invalid_credentials': '邮箱或密码不正确，请检查后重试。',
                'email_not_confirmed': '邮箱尚未验证，请先点击注册邮件中的验证链接，再返回登录。',
                'weak_password': '密码不符合安全要求，请更换密码',
                'same_password': '新密码不能与原密码相同，请更换新密码。',
                'over_email_send_rate_limit': '邮件发送已达到服务限额，请稍后重试或检查 SMTP 发送额度。',
            }
            if isinstance(code, str) and code in messages:
                raise HTTPException(429 if response.status_code == 429 else 400, messages[code])
        if response.status_code in {401, 403}:
            raise HTTPException(401 if not service else 503, '登录凭证无效或已过期' if not service else '私有存储鉴权失败')
        if response.status_code == 404:
            raise HTTPException(404, '文件或记录不存在')
        if response.status_code == 429:
            raise HTTPException(429, '请求过于频繁，请稍后重试')
        if path.startswith('/auth/') and response.status_code in {400, 422}:
            raise HTTPException(400, '账号操作未完成，请稍后重试。')
        raise HTTPException(503, 'Supabase 操作失败，请检查服务配置')
    return response


def credentials(action, email, password):
    path = '/auth/v1/signup' if action == 'register' else '/auth/v1/token?grant_type=password'
    data = call('POST', path, payload={'email': email.strip().lower(), 'password': password}).json()
    if not data.get('access_token'):
        return {'confirmation_required': True, 'message': '请到邮箱完成验证，再返回登录。'}
    return session(data)


def session(data):
    return {'token': data['access_token'], 'refresh_token': data.get('refresh_token'), 'expires_in': data.get('expires_in', 3600)}
