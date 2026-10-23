import uuid

from fastapi.testclient import TestClient

from services.api.main import create_app


def test_nonempty_password_lengths_can_register_and_login():
    with TestClient(create_app('sqlite://')) as client:
        for password in ('x', 'a' * 129):
            credentials = {'email': f'{uuid.uuid4()}@example.test', 'password': password}
            registered = client.post('/api/v1/auth/register', json=credentials)
            assert registered.status_code == 200
            logged_in = client.post('/api/v1/auth/login', json=credentials)
            assert logged_in.status_code == 200
            assert logged_in.json()['token']


def test_empty_password_is_rejected_for_register_and_login():
    with TestClient(create_app('sqlite://')) as client:
        for action in ('register', 'login'):
            response = client.post(f'/api/v1/auth/{action}', json={
                'email': 'empty@example.test', 'password': '',
            })
            assert response.status_code == 422
