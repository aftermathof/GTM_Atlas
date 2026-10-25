from fastapi.testclient import TestClient
from services.api.main import create_app


def make_client(monkeypatch):
    monkeypatch.setenv('ALLOWED_ORIGINS', 'https://frontend.example.test')
    app = create_app('sqlite://')

    @app.post('/api/v1/test-write')
    def write():
        return {'ok': True}

    return TestClient(app)


def test_preloads_preflight_does_not_exhaust_write_budget(monkeypatch):
    client = make_client(monkeypatch)
    headers = {'Origin': 'https://frontend.example.test',
               'Access-Control-Request-Method': 'GET',
               'Access-Control-Request-Headers': 'authorization'}
    for _ in range(160):
        response = client.options('/api/v1/knowledge/documents/example', headers=headers)
        assert response.status_code == 200
    response = client.post('/api/v1/test-write', headers={'Origin': headers['Origin']})
    assert response.status_code == 200


def test_rate_limit_error_remains_readable_cross_origin(monkeypatch):
    client = make_client(monkeypatch)
    headers = {'Origin': 'https://frontend.example.test'}
    for _ in range(60):
        assert client.post('/api/v1/test-write', headers=headers).status_code == 200
    response = client.post('/api/v1/test-write', headers=headers)
    assert response.status_code == 429
    assert response.headers.get('access-control-allow-origin') == headers['Origin']
    assert response.json()['code'] == 'rate_limited'
