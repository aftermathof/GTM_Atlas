from sqlalchemy import select
from packages.rag.knowledge import terms
from services.api.db import Record


def search_notes(db, owner, query, note_id=None):
    """Private, live lexical retrieval. Never copy notes into the public index."""
    statement = select(Record).where(Record.owner == owner, Record.kind == 'learning_note')
    if note_id:
        statement = statement.where(Record.id == note_id)
    query_terms = set(terms(query))
    matches = []
    for row in db.scalars(statement):
        title, body = row.data['title'], row.data['body']
        title_terms = set(terms(title))
        for index, start in enumerate(range(0, max(1, len(body)), 1600)):
            text = body[start:start + 1800]
            score = len(query_terms & set(terms(text))) + 3 * len(query_terms & title_terms)
            if score or note_id:
                matches.append((score, row.data['updated_at'], {
                    'chunk_id': 'note-' + row.id + ':' + str(index), 'doc_id': row.id,
                    'title': title, 'heading_path': '我的学习笔记', 'text': text,
                    'kind': 'note', 'permission': 'private', 'quality_status': 'user_provided',
                    'url': '/notes/' + row.id,
                }))
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in matches[:6]]
