"""Email recovery is delegated to Supabase; no password reset by email alone."""
import os
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from services.api import supabase

router = APIRouter(prefix='/api/v1/auth')


class RecoveryEmail(BaseModel):
    email: str = Field(pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class RecoveryPassword(BaseModel):
    recovery_token: str = Field(min_length=1)
    password: str = Field(min_length=1)


def require_email_auth():
    if supabase.auth_mode() != 'supabase':
        raise HTTPException(503, '当前环境未启用邮件找回密码，请联系管理员。')


@router.post('/request-password-reset')
def request_password_reset(body: RecoveryEmail, request: Request):
    require_email_auth()
    allowed = [value.strip().rstrip('/') for value in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')]
    origin = (request.headers.get('origin') or allowed[0]).rstrip('/')
    if origin not in allowed or not origin.startswith(('https://', 'http://')):
        raise HTTPException(403, '重置链接的返回地址不受信任')
    redirect = quote(origin + '/login?reset=1', safe='')
    supabase.call('POST', '/auth/v1/recover?redirect_to=' + redirect, payload={'email': body.email.strip().lower()})
    return {'message': '如果该邮箱已注册，重置链接已发送，请检查收件箱和垃圾邮件。'}


@router.post('/reset-password')
def reset_password(body: RecoveryPassword):
    require_email_auth()
    try:
        supabase.call('PUT', '/auth/v1/user', token=body.recovery_token, payload={'password': body.password})
    except HTTPException as error:
        if error.status_code == 401:
            raise HTTPException(400, '重置链接已失效，请重新申请找回密码。') from None
        raise
    return {'message': '密码已更新，请使用新密码登录。'}
