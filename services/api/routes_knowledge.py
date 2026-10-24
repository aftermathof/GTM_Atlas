import os
import time
import re
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import select, delete
from services.api.auth import current_user
from services.api.db import Document, Record, uid
from services.api.schemas import Chat, Search
from services.api.store import owned, save, trace, expose
from packages.rag.knowledge import search, ingest
from packages.learning.graph import answer_question
from packages.agent_core.providers import SpeechToTextProvider

router = APIRouter(prefix="/api/v1")


@router.get("/knowledge/documents")
def documents(request: Request, kind: str = "", role: str = "", industry: str = "", q: str = "", offset: int = 0, limit: int = 30):
    user = current_user(request) if request.headers.get('authorization') else None
    with request.app.state.db() as db:
        docs = db.scalars(select(Document).order_by(Document.id)).all()
        docs = [d for d in docs if d.meta["permission"] == "public_display" and d.meta.get('catalog_visible', True) and (not kind or d.kind == kind) and (not role or role == "custom" or role in d.meta.get("role_tags", [])) and (not industry or industry in d.meta.get("industry_tags", [])) and (not q or q.lower() in (d.title + d.body).lower())]
        docs.sort(key=lambda d: (not d.meta.get('source_note_id'), re.sub(r'\d+', lambda m: m[0].zfill(12), str(d.meta.get('source_note_id'))) if d.meta.get('source_note_id') else d.id, d.id))
        items = [{"id": d.id, "title": d.title, "kind": d.kind, "meta": d.meta, "excerpt": d.meta.get('excerpt') or next((line for line in d.body.splitlines() if line.strip() and not line.startswith(('#','-'))), '')[:180], "minutes": max(3, len(d.body) // 350)} for d in docs]
        if user and kind in {'','jd'}:
            for row in db.scalars(select(Record).where(Record.owner==user.id,Record.kind=='private_jd').order_by(Record.created_at.desc())):
                if not q or q.lower() in (row.data['title']+row.data['body']).lower():
                    items.insert(0,{'id':row.id,'title':row.data['title'],'kind':'jd','private':True,'meta':{'source_type':'user_uploaded','permission':'private','quality_status':'user_provided','source_author':'我的上传'},'excerpt':row.data['body'][:180],'minutes':max(1,len(row.data['body'])//350)})
        start = max(0,offset)
        return {'items':items[start:start+min(max(1,limit),100)],'total':len(items)}


@router.get("/knowledge/documents/{did}")
def document(did: str, request: Request):
    with request.app.state.db() as db:
        doc = db.get(Document, did)
        if not doc or doc.meta["permission"] != "public_display":
            if request.headers.get('authorization'):
                user=current_user(request)
                row=owned(db,did,user.id,'private_jd')
                return {'id':row.id,'title':row.data['title'],'body':row.data['body'],'sha256':row.data['sha256'],'meta':{'kind':'jd','permission':'private','source_type':'user_uploaded','quality_status':'user_provided','source_author':'我的上传'},'private':True}
            raise HTTPException(404, "文档不可用")
        return {"id": doc.id, "title": doc.title, "body": doc.body, "meta": doc.meta, "sha256": doc.sha256}


@router.post("/knowledge/search")
def knowledge_search(body: Search, request: Request):
    with request.app.state.db() as db:
        return {"items": search(db, body.query, body.kind, body.role, body.industry)}


@router.post("/ai/chat")
def chat(body: Chat, request: Request):
    user = current_user(request) if body.scope == "career" or request.headers.get("authorization") else None
    if body.conversation_id and not user:
        raise HTTPException(401, '请先登录后恢复会话')
    with request.app.state.mutation_lock, request.app.state.db() as db:
        thread, history = None, []
        if body.conversation_id:
            thread = owned(db, body.conversation_id, user.id, 'chat_thread', lock=True)
            if any(thread.data.get(k) != getattr(body, k) for k in ('scope', 'document_id', 'session_id')):
                raise HTTPException(409, '会话资料范围已改变，请新建会话')
            turns = conversation_messages(db, thread)
            history = [{'question': m['message'][:500], 'answer': m['response']['answer'][:1000]} for m in turns if m['turn'] > thread.data.get('context_after', 0)][-10:]
        private = None
        if body.scope=='article' and body.document_id:
            selected=db.get(Record,body.document_id)
            if selected and selected.kind=='private_jd':
                if not user or selected.owner!=user.id:
                    raise HTTPException(404,'文档不可用')
                private={'selected_document':{'id':selected.id,**selected.data}}
        if body.scope == "career":
            if not body.session_id:
                raise HTTPException(422, "当前简历范围需要明确选择会话")
            row = owned(db, body.session_id, user.id, "career")
            private = {"facts": row.data["facts"], "role": row.data["context"]["role"], "status": row.data["status"], 'career_context':row.data['context'],'jd':row.data['context'].get('jd',''),'owner_id':user.id}
        result = answer_question(db, body, private, history=history)
        result["request_id"] = uid()
        if user:
            if not thread:
                thread = save(db, user.id, 'chat_thread', {'title': body.message[:80], 'scope': body.scope, 'document_id': body.document_id, 'session_id': body.session_id, 'context_after': 0, 'turn_count': 0}, body.session_id)
            turn = thread.data['turn_count'] + 1
            thread.data = {**thread.data, 'turn_count': turn}
            result['conversation_id'] = thread.id
            save(db, user.id, "conversation", {"message": body.message, "scope": body.scope, "response": result, 'conversation_id': thread.id, 'turn': turn}, thread.id)
            trace(db, user.id, "learning_qa_graph", thread.id, result["trace"])
            db.commit()
        return result


def conversation_messages(db, thread):
    rows = db.scalars(select(Record).where(Record.owner == thread.owner, Record.kind == 'conversation', Record.parent_id == thread.id)).all()
    return sorted([expose(r) for r in rows], key=lambda r: r['turn'])


@router.get('/ai/conversations')
def conversations(request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        rows = db.scalars(select(Record).where(Record.owner == user.id, Record.kind == 'chat_thread').order_by(Record.created_at.desc()).limit(100)).all()
        return [expose(row) for row in rows]


@router.get('/ai/conversations/{cid}')
def conversation(cid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        row = owned(db, cid, user.id)
        if row.kind == 'conversation' and not row.data.get('conversation_id'):
            return {'id': row.id, 'scope': row.data['scope'], 'legacy': True, 'messages': [expose(row)]}
        if row.kind != 'chat_thread':
            raise HTTPException(404, '会话不存在')
        return {**expose(row), 'messages': conversation_messages(db, row)}


@router.post('/ai/conversations/{cid}/reset')
def reset_conversation(cid: str, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, cid, user.id, 'chat_thread', lock=True)
        row.data = {**row.data, 'context_after': row.data['turn_count']}
        db.commit()
        return expose(row)


@router.delete('/ai/conversations/{cid}')
def delete_conversation(cid: str, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, cid, user.id)
        if row.kind not in {'chat_thread', 'conversation'}:
            raise HTTPException(404, '会话不存在')
        db.execute(delete(Record).where(Record.owner == user.id, Record.parent_id == row.id, Record.kind.in_(['conversation', 'agent_run'])))
        db.delete(row)
        db.commit()
        return {'deleted': True}


@router.post("/ai/transcriptions")
async def transcribe(request: Request, file: UploadFile = File(...), language_hint: str = Form(""), consent: bool = Form(False), user=Depends(current_user)):
    if not os.getenv("STT_BASE_URL") or not os.getenv("STT_API_KEY"):
        raise HTTPException(503, "STT 服务未配置，请继续使用键盘输入")
    if not consent:
        raise HTTPException(422, "请先同意将录音发送至配置的 STT 服务")
    mime = (file.content_type or "").split(";")[0]
    if mime not in {"audio/webm", "audio/ogg", "audio/mp4", "audio/wav"}:
        raise HTTPException(415, "不支持的录音格式")
    content = await file.read(8_000_001)
    await file.close()
    if not content or len(content) > 8_000_000:
        raise HTTPException(413, "录音应在8MB以内")
    started = time.monotonic()
    result = SpeechToTextProvider().transcribe(content, mime, language_hint)
    result["request_id"] = uid()
    if result["duration_ms"] > 120_000:
        raise HTTPException(422, "录音不能超过120秒")
    with request.app.state.db() as db:
        save(db, user.id, "voice_event", {"duration_ms": result["duration_ms"], "elapsed_ms": round((time.monotonic() - started) * 1000), "request_id": result["request_id"]})
        db.commit()
    return result


@router.post("/admin/knowledge/reindex")
def reindex(request: Request, user=Depends(current_user)):
    if user.email != os.getenv("ADMIN_EMAIL"):
        raise HTTPException(403, "需要管理员权限")
    with request.app.state.db() as db:
        return ingest(db)
