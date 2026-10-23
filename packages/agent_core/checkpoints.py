"""SQLAlchemy-backed LangGraph checkpoints; JSON-compatible business state only."""
import base64
import threading
from functools import wraps
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple
from sqlalchemy import select, delete
from services.api.db import Record
from services.api.store import save


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return call


class SQLCheckpointer(BaseCheckpointSaver):
    def __init__(self, factory, owner):
        super().__init__()
        self.factory, self.owner = factory, owner
        self.lock = threading.RLock()

    def packed(self, value):
        kind, raw = self.serde.dumps_typed(value)
        return [kind, base64.b64encode(raw).decode()]

    def unpacked(self, value):
        return self.serde.loads_typed((value[0], base64.b64decode(value[1])))

    @serialized
    def get_tuple(self, config):
        conf = config["configurable"]
        with self.factory() as db:
            rows = db.scalars(select(Record).where(Record.owner == self.owner, Record.kind == "checkpoint", Record.parent_id == conf["thread_id"])).all()
            rows = [r for r in rows if r.data["namespace"] == conf.get("checkpoint_ns", "") and (not conf.get("checkpoint_id") or r.data["checkpoint_id"] == conf["checkpoint_id"])]
            if not rows:
                return None
            row = max(rows, key=lambda r: r.data["checkpoint_id"])
            data = row.data
            writes = db.scalars(select(Record).where(Record.owner == self.owner, Record.kind == "checkpoint_write", Record.parent_id == row.id)).all()
            pending = [(r.data["task_id"], c, self.unpacked(v)) for r in writes for c, v in r.data["writes"]]
            return CheckpointTuple(config={"configurable": {"thread_id": conf["thread_id"], "checkpoint_ns": data["namespace"], "checkpoint_id": data["checkpoint_id"]}}, checkpoint=self.unpacked(data["checkpoint"]), metadata=self.unpacked(data["metadata"]), parent_config=data["parent_config"], pending_writes=pending)

    @serialized
    def put(self, config, checkpoint, metadata, new_versions):
        conf = config["configurable"]
        namespace = conf.get("checkpoint_ns", "")
        with self.factory() as db:
            key = f"{conf['thread_id']}:{namespace}:{checkpoint['id']}"
            if not db.scalar(select(Record).where(Record.owner == self.owner, Record.kind == "checkpoint", Record.idempotency_key == key)):
                parent = {"configurable": {"thread_id": conf["thread_id"], "checkpoint_ns": namespace, "checkpoint_id": conf["checkpoint_id"]}} if conf.get("checkpoint_id") else None
                save(db, self.owner, "checkpoint", {"namespace": namespace, "checkpoint_id": checkpoint["id"], "checkpoint": self.packed(checkpoint), "metadata": self.packed(metadata), "parent_config": parent}, conf["thread_id"], key)
                db.commit()
        return {"configurable": {"thread_id": conf["thread_id"], "checkpoint_ns": namespace, "checkpoint_id": checkpoint["id"]}}

    @serialized
    def put_writes(self, config, writes, task_id, task_path=""):
        current = self.get_tuple(config)
        if not current:
            return
        conf = config["configurable"]
        with self.factory() as db:
            rows = db.scalars(select(Record).where(Record.owner == self.owner, Record.kind == "checkpoint", Record.parent_id == conf["thread_id"])).all()
            row = next(r for r in rows if r.data["checkpoint_id"] == conf["checkpoint_id"] and r.data["namespace"] == conf.get("checkpoint_ns", ""))
            save(db, self.owner, "checkpoint_write", {"task_id": task_id, "writes": [[c, self.packed(v)] for c, v in writes]}, row.id)
            db.commit()

    def list(self, config, *, filter=None, before=None, limit=None):
        value = self.get_tuple(config) if config else None
        if value:
            yield value

    def delete_thread(self, thread_id):
        with self.factory() as db:
            ids = list(db.scalars(select(Record.id).where(Record.owner == self.owner, Record.kind == "checkpoint", Record.parent_id == thread_id)))
            db.execute(delete(Record).where(Record.owner == self.owner, Record.kind == "checkpoint_write", Record.parent_id.in_(ids)))
            db.execute(delete(Record).where(Record.id.in_(ids)))
            db.commit()
