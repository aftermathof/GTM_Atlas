from sqlalchemy import select
from services.api.db import Record
from tests.test_workflows import client, login


def test_empty_mock_is_not_history_but_active_session_can_still_be_answered(client):
    headers = login(client)
    result = client.post('/api/v1/mock/sessions', json={'count':3}, headers=headers)
    sid = result.json()['id']
    assert client.get('/api/v1/history',headers=headers).json() == []
    assert client.get(f'/api/v1/mock/sessions/{sid}',headers=headers).status_code == 200
    answered = client.post(f'/api/v1/mock/sessions/{sid}/answers',json={'question_index':0,'answer':'我先调研用户，再验证渠道假设。','idempotency_key':'first-answer'},headers=headers)
    assert answered.status_code == 200
    assert [item['id'] for item in client.get('/api/v1/history',headers=headers).json()] == [sid]


def test_discard_only_deletes_unanswered_sessions_and_related_records(client):
    headers = login(client)
    sid = client.post('/api/v1/mock/sessions',json={'count':3},headers=headers).json()['id']
    result = client.delete(f'/api/v1/mock/sessions/{sid}?only_if_unanswered=true',headers=headers)
    assert result.json()['deleted'] is True
    assert client.get(f'/api/v1/mock/sessions/{sid}',headers=headers).status_code == 404
    with client.app.state.db() as db:
        assert db.scalar(select(Record.id).where(Record.parent_id == sid)) is None


def test_discard_keeps_answers_saved_by_another_tab(client):
    headers = login(client)
    sid = client.post('/api/v1/mock/sessions',json={'count':3},headers=headers).json()['id']
    client.post(f'/api/v1/mock/sessions/{sid}/answers',json={'question_index':0,'answer':'我会先明确指标口径，再做验证。','idempotency_key':'another-tab'},headers=headers)
    result = client.delete(f'/api/v1/mock/sessions/{sid}?only_if_unanswered=true',headers=headers)
    assert result.json()['deleted'] is False
    assert len(client.get(f'/api/v1/mock/sessions/{sid}/report',headers=headers).json()['answers']) == 1
