import os
import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as DatabaseTimeoutError
from services.api.db import Base, User, Token, Record, make_database, uid
from services.api.auth import current_user, password_hash, check_password, issue_token
from services.api.schemas import Credentials, RefreshToken
from services.api import supabase
from services.api.store import expose
from services.api.routes_knowledge import router as knowledge_router
from services.api.routes_mock import router as mock_router
from services.api.routes_career import router as career_router
from packages.rag.knowledge import ingest
from packages.agent_core.registry import catalog, skills
from packages.agent_core.providers import LLMProvider

logger = logging.getLogger(__name__)


def create_app(url=None):
    engine, factory = make_database(url)

    @asynccontextmanager
    async def lifespan(app):
        # PG schema is exclusively managed by Alembic. SQLite is explicit development mode.
        if engine.dialect.name == "sqlite":
            Base.metadata.create_all(engine)
        with factory() as db:
            ingest(db)
        try:
            yield
        finally:
            engine.dispose()
            supabase.close_client()

    app = FastAPI(title="GTM Atlas API", version="0.1.0", lifespan=lifespan)
    app.state.db = factory
    app.state.mutation_lock = threading.RLock()
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])
    rate = defaultdict(deque)
    rate_lock = threading.Lock()

    @app.middleware("http")
    async def limits(request, call_next):
        request_id = uid()
        if int(request.headers.get("content-length", "0") or "0") > 11_000_000:
            return JSONResponse({"detail": "请求超过11MB限制", "code": "payload_too_large"}, status_code=413)
        identity = (request.client.host if request.client else "local") + ("auth" if "/auth/" in request.url.path else "api")
        if request.method != "GET":
            with rate_lock:
                queue = rate[identity]
                clock = time.monotonic()
                while queue and clock - queue[0] > 60:
                    queue.popleft()
                if len(queue) >= (20 if "/auth/" in request.url.path else 60):
                    return JSONResponse({"detail": "请求过于频繁，请稍后重试", "code": "rate_limited"}, status_code=429)
                queue.append(clock)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def error(request, exc):
        return JSONResponse({"detail": exc.detail, "code": f"http_{exc.status_code}"}, status_code=exc.status_code)

    @app.exception_handler(OperationalError)
    @app.exception_handler(DatabaseTimeoutError)
    async def database_unavailable(request, exc):
        logger.warning('database_unavailable exception=%s', type(exc).__name__)
        return JSONResponse({"detail": "数据库连接暂时中断，请稍后重试。", "code": "database_unavailable"}, status_code=503)

    @app.get("/api/v1/health")
    def health():
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return {"status": "ok", "auth_mode": supabase.auth_mode(), "llm_configured": bool(os.getenv("LLM_API_KEY")) and os.getenv("PROVIDER_MODE", "live") == "live", "provider": LLMProvider().mode, "model": LLMProvider().model, "database": engine.dialect.name, "retrieval": "hybrid-rrf" if os.getenv("EMBEDDING_API_KEY") else "lexical-development", "stt_configured": bool(os.getenv("STT_API_KEY") and os.getenv("STT_BASE_URL")), "vision_configured": bool(os.getenv("VISION_API_KEY")), "render_enabled": os.getenv("RENDER_ENABLED") == "true"}

    @app.post("/api/v1/auth/register")
    def register(body: Credentials):
        if supabase.auth_mode() == 'supabase':
            return supabase.credentials('register', body.email, body.password)
        with factory() as db:
            email = body.email.lower().strip()
            user = User(email=email, password_hash=password_hash(body.password))
            db.add(user)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "该邮箱已注册")
            return issue_token(db, user)

    @app.post("/api/v1/auth/login")
    def login(body: Credentials):
        if supabase.auth_mode() == 'supabase':
            return supabase.credentials('login', body.email, body.password)
        with factory() as db:
            user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
            if not user or not check_password(body.password, user.password_hash):
                raise HTTPException(401, "邮箱或密码不正确")
            return issue_token(db, user)

    @app.post("/api/v1/auth/logout")
    def logout(request: Request, user=Depends(current_user)):
        if supabase.auth_mode() == 'supabase':
            supabase.call('POST', '/auth/v1/logout?scope=local', token=request.headers['Authorization'][7:])
            return {'ok': True}
        with factory() as db:
            value = request.headers["Authorization"][7:]
            token = db.get(Token, hashlib.sha256(value.encode()).hexdigest())
            if token:
                db.delete(token)
                db.commit()
        return {"ok": True}

    @app.post('/api/v1/auth/refresh')
    def refresh_auth(body: RefreshToken):
        if supabase.auth_mode() != 'supabase':
            raise HTTPException(400, '本地账号请重新登录')
        return supabase.session(supabase.call('POST', '/auth/v1/token?grant_type=refresh_token', payload=body.model_dump()).json())

    @app.get("/api/v1/auth/me")
    def me(user=Depends(current_user)):
        return {"id": user.id, "email": user.email, "preferences": user.preferences}

    @app.put("/api/v1/preferences")
    def preferences(body: dict, user=Depends(current_user)):
        allowed = {k: str(v)[:200] for k, v in body.items() if k in {"role", "role_raw", "industry", "language", "region", "template", "seniority", "business_model"}}
        with factory() as db:
            row = db.get(User, user.id)
            row.preferences = allowed
            db.commit()
        return allowed

    @app.get("/api/v1/history")
    def history(user=Depends(current_user)):
        with factory() as db:
            rows = db.scalars(select(Record).where(Record.owner == user.id, Record.kind.in_(["mock", "career", "conversation", "chat_thread"])).order_by(Record.created_at.desc())).all()
            rows = [r for r in rows if (r.kind != 'conversation' or not r.data.get('conversation_id')) and (r.kind != 'mock' or r.data.get('answers'))][:100]
            return [{"id": r.id, "kind": r.kind, "created_at": r.created_at.isoformat(), "status": r.data.get("status"), "context": r.data.get("context"), "message": r.data.get('title') or r.data.get("message")} for r in rows]

    @app.get("/api/v1/jobs/{jid}")
    def job(jid: str, user=Depends(current_user)):
        from services.api.store import owned
        with factory() as db:
            return expose(owned(db, jid, user.id, "render_job"))

    @app.get("/api/v1/catalog/roles")
    def roles():
        return catalog()["roles"]

    @app.get("/api/v1/catalog/industries")
    def industries():
        return catalog()["industries"]

    @app.get("/api/v1/catalog/skills")
    def registry():
        return [{k: v for k, v in s.items() if k != "instructions"} for s in skills()]

    for router in [knowledge_router, mock_router, career_router]:
        app.include_router(router)
    from services.api.config import ROOT
    from fastapi.responses import FileResponse
    dist = ROOT / "apps/web/dist"
    @app.get("/{path:path}", include_in_schema=False)
    def web(path: str):
        if path.startswith("api/") or not dist.exists():
            raise HTTPException(404, "页面不存在，请先构建前端")
        target = (dist / path).resolve()
        if not target.is_relative_to(dist.resolve()):
            raise HTTPException(404, "页面不存在")
        if target.is_dir() and (target / "index.html").exists():
            target = target / "index.html"
        return FileResponse(target if target.is_file() else dist / "index.html")
    return app


app = create_app()
