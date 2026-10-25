from tests.test_workflows import client, login


def test_bulk_documents_match_readable_documents(client):
    headers = login(client)
    response = client.get('/api/v1/knowledge/preload', headers=headers)
    assert response.status_code == 200
    documents = response.json()['items']
    assert documents
    for document in documents[:3]:
        assert document == client.get('/api/v1/knowledge/documents/' + document['id'], headers=headers).json()


def test_mock_prefetch_includes_report_and_is_account_private(client):
    headers = login(client)
    sid = client.post('/api/v1/mock/sessions', json={'count': 3}, headers=headers).json()['id']
    client.post(f'/api/v1/mock/sessions/{sid}/answers', headers=headers,
                json={'answer': '先明确客户与渠道假设。', 'question_index': 0, 'idempotency_key': 'prefetch'})
    rows = client.get('/api/v1/history?prefetch=true', headers=headers).json()
    row = next(row for row in rows if row['id'] == sid)
    assert row['snapshot'] == client.get(f'/api/v1/mock/sessions/{sid}/report', headers=headers).json()
    assert client.get('/api/v1/history?prefetch=true', headers=login(client, 'other')).json() == []


def test_mock_allows_multiple_followups_then_advances(client, monkeypatch):
    headers = login(client)
    sid = client.post('/api/v1/mock/sessions', json={'count': 3}, headers=headers).json()['id']
    def evaluate(*args):
        return {'followup': '请继续解释你的依据。', 'score': 50, 'feedback': '继续说明。', 'model': 'test'}
    monkeypatch.setattr('services.api.routes_mock.evaluate_answer', evaluate)
    for index in range(3):
        result = client.post(f'/api/v1/mock/sessions/{sid}/answers', headers=headers,
                             json={'answer': '我的依据。', 'question_index': 0, 'idempotency_key': str(index)})
        assert result.status_code == 200
        assert result.json()['current_question_index'] == 0
        assert result.json()['followup_counts']['0'] == index + 1
    monkeypatch.setattr('services.api.routes_mock.evaluate_answer', lambda *args: {**evaluate(), 'followup': None})
    result = client.post(f'/api/v1/mock/sessions/{sid}/answers', headers=headers,
                         json={'answer': '最后补充。', 'question_index': 0, 'idempotency_key': 'done'})
    assert result.json()['current_question_index'] == 1
