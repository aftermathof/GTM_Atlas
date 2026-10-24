import hashlib
import math
import os
import re
from collections import Counter
from pathlib import Path
import yaml
from sqlalchemy import select, delete, text
from sqlalchemy.orm import load_only, defer
from services.api.db import Document, Chunk
from services.api.config import ROOT
from packages.agent_core.providers import EmbeddingProvider
from packages.rag.reference_sources import reference_documents

# MVP deliberately indexes only public_display. Other licenses require separate grants.
PUBLIC = "public_display"


def terms(value):
    english = re.findall(r"[a-z0-9&]+", value.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]+", value)
    return english + [word[i:i + 2] for word in chinese for i in range(max(1, len(word) - 1))]


def ingest(db, root=None, reference_root=None):
    if root is None and reference_root is None:
        reference_root = ROOT
    root = Path(root or ROOT / "knowledge").resolve()
    found, hashes = set(), set()
    report = {"indexed": 0, "skipped": 0, "deleted": 0}
    provider = EmbeddingProvider()
    sources = []
    for file in sorted(root.rglob("*.md")):
        if file.is_symlink() or not file.resolve().is_relative_to(root) or file.stat().st_size > 2_000_000:
            raise ValueError("Unsafe knowledge file")
        sources.append((file.relative_to(root).as_posix(), file.read_text(encoding="utf-8")))
    if reference_root is not None:
        sources.extend(reference_documents(reference_root))
    for path, raw in sources:
        pieces = raw.split("---", 2)
        if len(pieces) != 3 or pieces[0].strip():
            raise ValueError(f"Missing frontmatter: {path}")
        meta = yaml.safe_load(pieces[1])
        required = {"id", "title", "kind", "permission", "quality_status", "source_type", "role_tags", "industry_tags"}
        if not isinstance(meta, dict) or not required.issubset(meta) or meta["kind"] not in {"learning", "interview", "jd"}:
            raise ValueError(f"Invalid knowledge metadata: {path}")
        did = str(meta["id"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", did):
            raise ValueError("Invalid document id")
        if did in found:
            raise ValueError("Duplicate document id: " + did)
        found.add(did)
        if meta["permission"] != PUBLIC or meta["quality_status"] == "deprecated":
            db.execute(delete(Chunk).where(Chunk.doc_id == did))
            db.execute(delete(Document).where(Document.id == did))
            report["skipped"] += 1
            continue
        body = pieces[2].strip()
        digest = hashlib.sha256(raw.encode()).hexdigest()
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        if body_hash in hashes:
            raise ValueError("Duplicate document content")
        hashes.add(body_hash)
        old = db.get(Document, did)
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small") if provider.enabled else None
        old_chunk = db.scalar(select(Chunk).where(Chunk.doc_id == did).limit(1))
        if old and old.sha256 == digest and old_chunk and old_chunk.embedding_model == embedding_model:
            continue
        db.execute(delete(Chunk).where(Chunk.doc_id == did))
        # Convert YAML date scalars to JSON-safe values.
        meta = {k: str(v) if hasattr(v, "isoformat") else v for k, v in meta.items()}
        document = old or Document(id=did)
        document.title, document.kind, document.body = str(meta["title"]), meta["kind"], body
        document.meta, document.sha256, document.path = meta, digest, path
        db.add(document)
        db.flush()
        sections = re.split(r"(?m)^(?=#{1,3} )", body)
        units = []
        for section in sections:
            if not section.strip():
                continue
            heading = section.splitlines()[0].lstrip("# ")
            for start in range(0, len(section), 1800):
                units.append((heading, section[start:start + 1800]))
        embeddings = provider.embed([u[1] for u in units]) if provider.enabled else [None] * len(units)
        for index, ((heading, content), vector) in enumerate(zip(units, embeddings)):
            db.add(Chunk(id=f"{did}:{index}", doc_id=did, heading=heading, body=content, embedding=vector, embedding_model=embedding_model))
        report["indexed"] += 1
    for old in db.scalars(select(Document)).all():
        if old.id not in found:
            db.execute(delete(Chunk).where(Chunk.doc_id == old.id))
            db.delete(old)
            report["deleted"] += 1
    db.commit()
    return report


def search(db, query, kind=None, role="", industry="", document_id=None, top_k=6, include_demo=True):
    statement = select(Chunk, Document).join(Document, Chunk.doc_id == Document.id).options(
        load_only(Document.id, Document.title, Document.kind, Document.meta))
    if db.bind.dialect.name == 'postgresql':
        statement = statement.options(defer(Chunk.embedding))
    if kind:
        statement = statement.where(Document.kind == kind)
    if document_id:
        statement = statement.where(Document.id == document_id)
    candidates = []
    query_terms = set(terms(query))
    for chunk, doc in db.execute(statement):
        if doc.meta.get("permission") != PUBLIC or doc.meta.get("quality_status") == "deprecated":
            continue
        if not include_demo and doc.meta.get('demo'):
            continue
        if role and role != "custom" and role not in doc.meta.get("role_tags", []) and not doc.meta.get('universal_reference'):
            continue
        if industry and industry not in doc.meta.get("industry_tags", []) and not doc.meta.get('universal_reference'):
            continue
        tokens = Counter(terms(doc.title + " " + chunk.heading + " " + chunk.body))
        lexical = sum(min(tokens[t], 3) for t in query_terms)
        if len(query_terms) >= 4 and sum(t in tokens for t in query_terms) < 2:
            lexical = 0
        if not query.strip():
            lexical = 1
        candidates.append({"chunk": chunk, "doc": doc, "lexical": lexical})
    if not candidates:
        return []
    # Native PostgreSQL FTS is an additional lexical signal, not BM25.
    if db.bind.dialect.name == "postgresql" and query.strip():
        ranks = dict(db.execute(text("SELECT id, ts_rank_cd(to_tsvector('simple', body), plainto_tsquery('simple', :q)) FROM knowledge_chunks"), {"q": " ".join(terms(query))}).all())
        for item in candidates:
            item["lexical"] += ranks.get(item["chunk"].id, 0)
    lexical = sorted([c for c in candidates if c["lexical"] > 0], key=lambda c: c["lexical"], reverse=True)[:20]
    fused = {c["chunk"].id: 1 / (60 + i + 1) for i, c in enumerate(lexical)}
    vector_enabled = EmbeddingProvider().enabled
    if vector_enabled and query.strip():
        vector = EmbeddingProvider().embed([query])[0]
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        eligible = {c["chunk"].id for c in candidates if c["chunk"].embedding_model == model}
        if db.bind.dialect.name == "postgresql" and eligible:
            ranked_ids = db.scalars(select(Chunk.id).where(Chunk.id.in_(eligible)).order_by(Chunk.embedding.cosine_distance(vector)).limit(20)).all()
            by_chunk_id = {c['chunk'].id: c['chunk'] for c in candidates}
            ranked = [by_chunk_id[cid] for cid in ranked_ids]
        else:
            def cosine(c):
                v = c["chunk"].embedding
                return sum(a * b for a, b in zip(v, vector)) / (math.sqrt(sum(a*a for a in v)) * math.sqrt(sum(a*a for a in vector)) or 1)
            ranked = [c["chunk"] for c in sorted([c for c in candidates if c["chunk"].id in eligible], key=cosine, reverse=True)[:20]]
        for i, chunk in enumerate(ranked):
            fused[chunk.id] = fused.get(chunk.id, 0) + 1 / (61 + i)
    by_id = {c["chunk"].id: c for c in candidates}
    output = []
    for cid in sorted(fused, key=fused.get, reverse=True)[:top_k]:
        c, d = by_id[cid]["chunk"], by_id[cid]["doc"]
        output.append({"chunk_id": cid, "doc_id": d.id, "title": d.title, "heading_path": c.heading, "text": c.body, "kind": d.kind, "source_url": d.meta.get("source_url"), 'source_type':d.meta.get('source_type'), 'source_author':d.meta.get('source_author'), 'demo':bool(d.meta.get('demo')), "quality_status": d.meta["quality_status"], "permission": d.meta["permission"], "score": round(fused[cid], 5), "url": f"/{'interviews' if d.kind == 'interview' else 'learn'}/{d.id}", "cross_role_reference": role == "custom", "retrieval_mode": "hybrid-rrf" if vector_enabled else "lexical-development"})
    return output
