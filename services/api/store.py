from fastapi import HTTPException
from sqlalchemy import select
from services.api.db import Record, uid


def owned(db, rid, owner, kind=None, lock=False):
    stmt = select(Record).where(Record.id == rid, Record.owner == owner)
    if kind:
        stmt = stmt.where(Record.kind == kind)
    if lock:
        stmt = stmt.with_for_update()
    row = db.scalar(stmt)
    if not row:
        raise HTTPException(404, "记录不存在")
    return row


def save(db, owner, kind, data, parent=None, key=None):
    row = Record(id=uid(), owner=owner, kind=kind, data=data, parent_id=parent, idempotency_key=key)
    db.add(row)
    db.flush()
    return row


def expose(row):
    return {**row.data, "id": row.id, "created_at": row.created_at.isoformat()}


def trace(db, owner, graph, parent, events):
    save(db, owner, "agent_run", {"graph": graph, "events": events}, parent)
