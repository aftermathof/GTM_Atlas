import httpx

from services.api import supabase


def test_supabase_requests_reuse_transport_and_close_cleanly(monkeypatch):
    clients = []
    original_client = httpx.Client

    def create_client(**kwargs):
        client = original_client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={'ok': True}),
        ), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(supabase.httpx, 'Client', create_client)
    try:
        for _ in range(2):
            assert supabase.request(httpx.Request('GET', 'https://example.test')).json()['ok']
        assert len(clients) == 1
        assert not clients[0].is_closed
    finally:
        if hasattr(supabase, 'close_client'):
            supabase.close_client()
    assert clients[0].is_closed
