"""Initial schema, vector extension and FTS index."""
from alembic import op
from services.api.db import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX knowledge_chunks_fts ON knowledge_chunks USING gin(to_tsvector('simple', body))")
        op.execute("CREATE INDEX knowledge_embeddings_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)")


def downgrade():
    Base.metadata.drop_all(op.get_bind())
