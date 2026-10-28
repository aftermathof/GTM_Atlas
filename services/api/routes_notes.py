from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete
from services.api.auth import current_user
from services.api.db import Record, now
from services.api.store import owned, save, expose

router = APIRouter(prefix='/api/v1/notes')


class FolderInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)

    @field_validator('title')
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError('请输入笔记标题')
        return value.strip()


class NoteInput(FolderInput):
    body: str = Field(default='', max_length=100000)
    folder_id: str | None = Field(default=None, min_length=1, max_length=36)


class NoteUpdate(NoteInput):
    revision: int = Field(ge=1)


@router.get('/folders')
def folders(request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        rows = db.scalars(select(Record).where(Record.owner == user.id, Record.kind == 'note_folder').order_by(Record.created_at, Record.id))
        return [expose(row) for row in rows]


@router.post('/folders')
def create_folder(body: FolderInput, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = save(db, user.id, 'note_folder', body.model_dump())
        db.commit()
        return expose(row)


@router.delete('/folders/{fid}')
def delete_folder(fid: str, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        folder = owned(db, fid, user.id, 'note_folder', lock=True)
        db.execute(delete(Record).where(Record.owner == user.id, Record.kind == 'learning_note', Record.data['folder_id'].as_string() == fid))
        db.delete(folder)
        db.commit()
        return {'deleted': True}


@router.get('')
def notes(request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        rows = db.scalars(select(Record).where(Record.owner == user.id, Record.kind == 'learning_note'))
        cards = [{k: v for k, v in expose(row).items() if k != 'body'} for row in rows]
        return sorted(cards, key=lambda card: card['updated_at'], reverse=True)


@router.post('')
def create_note(body: NoteInput, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        if body.folder_id:
            owned(db, body.folder_id, user.id, 'note_folder')
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
        folder_id = body.folder_id if 'folder_id' in body.model_fields_set else row.data.get('folder_id')
        if folder_id:
            owned(db, folder_id, user.id, 'note_folder')
        row.data = {**body.model_dump(), 'folder_id': folder_id, 'updated_at': now().isoformat(), 'revision': body.revision + 1}
        db.commit()
        return expose(row)


@router.delete('/{nid}')
def delete_note(nid: str, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        db.delete(owned(db, nid, user.id, 'learning_note', lock=True))
        db.commit()
        return {'deleted': True}
