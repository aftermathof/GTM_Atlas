import os
import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError, TimeoutError
from tests.test_workflows import client


def test_health_checks_the_database_instead_of_only_process_liveness(client):
    queries = []
    engine = client.app.state.db.kw['bind']
    def record_query(connection, cursor, statement, parameters, context, executemany):
        queries.append(statement)
    event.listen(engine, 'before_cursor_execute', record_query)
    try:
        assert client.get('/api/v1/health').status_code == 200
        assert any('SELECT 1' in query.upper() for query in queries)
    finally:
        event.remove(engine, 'before_cursor_execute', record_query)


@pytest.mark.parametrize('failure', [OperationalError('sensitive sql', {'private':'secret'}, Exception('internal connection details')), TimeoutError('internal pool details')])
def test_database_outage_returns_readable_cors_503_and_recovers(client, monkeypatch, failure):
    engine = client.app.state.db.kw['bind']
    origin = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')[0]
    def fail(*args, **kwargs):
        raise failure
    with monkeypatch.context() as patch:
        patch.setattr(engine, 'connect', fail)
        for path in ['/api/v1/health', '/api/v1/knowledge/documents']:
            response = client.get(path, headers={'Origin':origin})
            assert response.status_code == 503
            assert response.json()['code'] == 'database_unavailable'
            assert '数据库' in response.json()['detail']
            assert response.headers['access-control-allow-origin'] == origin
            assert 'internal' not in response.text and 'secret' not in response.text
    assert client.get('/api/v1/health').status_code == 200
