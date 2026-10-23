import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from pgvector.sqlalchemy import Vector
from services.api.config import database_url


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)


class Token(Base):
    __tablename__ = "auth_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    body: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON)
    sha256: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)


class Chunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    heading: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Vector(1536).with_variant(JSON(), "sqlite"), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(150), nullable=True)


class Record(Base):
    """Small MVP aggregate store; all private aggregates have an explicit owner."""
    __tablename__ = "business_records"
    __table_args__ = (UniqueConstraint("owner", "kind", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def make_database(url=None):
    url = url or database_url()
    opts = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if url.startswith('postgresql'):
        opts.update(pool_pre_ping=True, pool_size=5, max_overflow=5, connect_args={'options': '-csearch_path=public,extensions'})
    if url == "sqlite://":
        opts["poolclass"] = StaticPool
    engine = create_engine(url, hide_parameters=True, **opts)
    return engine, sessionmaker(engine, expire_on_commit=False)
