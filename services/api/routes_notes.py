from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from services.api.auth import current_user
from services.api.db import Record, now
from services.api.store import owned, save, expose

router = APIRouter(prefix='/api/v1/notes')


class NoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default='', max_length=100000)

    @field_validator('title')
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError('请输入笔记标题')
        return value.strip()


class NoteUpdate(NoteInput):
    revision: int = Field(ge=1)


@router.get('')
def notes(request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        rows = db.scalars(select(Record).where(Record.owner == user.id, Record.kind == 'learning_note'))
        cards = [{k: v for k, v in expose(row).items() if k != 'body'} for row in rows]
        return sorted(cards, key=lambda card: card['updated_at'], reverse=True)


@router.post('')
def create_note(body: NoteInput, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = save(db, user.id, 'learning_note', {**body.model_dump(), 'updated_at': now().isoformat(), 'revision': 1})
        db.commit()
        return expose(row)


@router.get('/{nid}')
def note(nid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        return expose(owned(db, nid, user.id, 'learning_note'))


@router.put('/{nid}')
def update_note(nid: str, body: NoteUpdate, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, nid, user.id, 'learning_note', lock=True)
        if row.data['revision'] != body.revision:
            raise HTTPException(409, '笔记已在其他页面修改，请先备份当前内容，再重新打开最新笔记。')
        row.data = {**body.model_dump(), 'updated_at': now().isoformat(), 'revision': body.revision + 1}
        db.commit()
        return expose(row)


@router.delete('/{nid}')
def delete_note(nid: str, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        db.delete(owned(db, nid, user.id, 'learning_note', lock=True))
        db.commit()
        return {'deleted': True}
