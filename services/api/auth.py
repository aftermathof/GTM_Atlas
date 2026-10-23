import hashlib
import hmac
import secrets
from datetime import timedelta, timezone
from fastapi import HTTPException, Request
from sqlalchemy import select
from services.api.db import Token, User, now


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return salt + ":" + value


def check_password(password, saved):
    return hmac.compare_digest(password_hash(password, saved.split(":")[0]), saved)


def issue_token(db, user):
    raw = secrets.token_urlsafe(40)
    db.add(Token(digest=hashlib.sha256(raw.encode()).hexdigest(), user_id=user.id, expires_at=now() + timedelta(days=7)))
    db.commit()
    return {"token": raw, "user": {"id": user.id, "email": user.email, "preferences": user.preferences}}


def current_user(request: Request):
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    from services.api import supabase
    if supabase.auth_mode() == 'supabase':
        identity = supabase.call('GET', '/auth/v1/user', token=value[7:]).json()
        with request.app.state.db() as db:
            user = db.get(User, identity['id'])
            if not user:
                raise HTTPException(503, '用户资料尚未同步，请确认已执行 Supabase 初始化 SQL')
            return user
    with request.app.state.db() as db:
        token = db.get(Token, hashlib.sha256(value[7:].encode()).hexdigest())
        if not token or token.expires_at.replace(tzinfo=timezone.utc) < now():
            raise HTTPException(401, "登录已过期，请重新登录")
        return db.get(User, token.user_id)
