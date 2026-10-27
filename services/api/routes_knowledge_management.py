"""Administrator maintenance of shared work-experience documents."""
import logging
import os
import re
from uuid import uuid5, NAMESPACE_URL
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete
from packages.rag.knowledge import index_document
from packages.rag.managed_knowledge import editable_learning, managed_source
from services.api.auth import current_user
from services.api.db import Document, Chunk, Record, now

router = APIRouter(prefix='/api/v1/knowledge')
logger = logging.getLogger(__name__)


def can_manage(user):
    address = os.getenv('ADMIN_EMAIL', '').strip().lower()
    return bool(address) and user.email.strip().lower() == address


class KnowledgeEdit(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=1000)
    body: str = Field(min_length=10, max_length=100000)
    expected_sha256: str = Field(min_length=1, max_length=64)

    @field_validator('title', 'excerpt', 'body')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('内容不能为空')
        return value.strip()


@router.get('/capabilities')
def capabilities(user=Depends(current_user)):
    return {'can_manage_learning': can_manage(user)}


def target_document(db, did, expected):
    doc = db.get(Document, did, with_for_update=True)
    if not doc:
        raise HTTPException(404, '资料不存在或已删除')
    if not editable_learning(doc.meta):
        raise HTTPException(403, '只能维护公开的在职经验资料')
    if doc.sha256 != expected:
        raise HTTPException(409, '资料已被其他页面修改，请先备份当前内容，再重新加载最新版本。')
    return doc


def override_record(db, doc, user):
    rid = str(uuid5(NAMESPACE_URL, 'gtm-atlas:knowledge:' + doc.id))
    row = db.get(Record, rid)
    if row is None:
        row = Record(id=rid, owner=user.id, kind='knowledge_override', data={
            'document_id': doc.id, 'revision': 0,
            'original': {'title': doc.title, 'body': doc.body, 'meta': doc.meta, 'sha256': doc.sha256}})
        db.add(row)
    return row


@router.put('/documents/{did}')
def edit_document(did: str, body: KnowledgeEdit, request: Request, user=Depends(current_user)):
    if not can_manage(user):
        raise HTTPException(403, '需要管理员权限')
    if '\n' in body.title or '\r' in body.title or len(re.findall(r'^# ', body.body, re.M)) > 1:
        raise HTTPException(422, '标题不能换行，正文最多保留一个一级标题')
    content = re.sub(r'^# [^\n]*(?:\n|$)', '', body.body, count=1).strip()
    content = '# ' + body.title + '\n\n' + content
    try:
        with request.app.state.mutation_lock, request.app.state.db() as db:
            doc = target_document(db, did, body.expected_sha256)
            row = override_record(db, doc, user)
            row.data = {**row.data, 'title': body.title, 'body': content, 'excerpt': body.excerpt,
                        'deleted': False, 'revision': row.data['revision'] + 1, 'updated_at': now().isoformat()}
            meta, content, digest = managed_source(doc.meta, row.data)
            updated = index_document(db, did, meta, content, doc.path, digest)
            db.commit()
            return {'id': updated.id, 'title': updated.title, 'body': updated.body, 'meta': updated.meta, 'sha256': updated.sha256}
    except HTTPException:
        raise
    except Exception as error:
        logger.warning('knowledge_edit_failed exception=%s', type(error).__name__)
        raise HTTPException(503, '保存与索引更新未完成，原资料未更改，请稍后重试。') from None


@router.delete('/documents/{did}')
def remove_document(did: str, expected_sha256: str, request: Request, user=Depends(current_user)):
    if not can_manage(user):
        raise HTTPException(403, '需要管理员权限')
    with request.app.state.mutation_lock, request.app.state.db() as db:
        doc = target_document(db, did, expected_sha256)
        row = override_record(db, doc, user)
        row.data = {**row.data, 'deleted': True, 'revision': row.data['revision'] + 1, 'updated_at': now().isoformat()}
        db.execute(delete(Chunk).where(Chunk.doc_id == did))
        db.delete(doc)
        db.commit()
        return {'deleted': True}
