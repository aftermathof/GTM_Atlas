import pytest
from fastapi import HTTPException
from packages.agent_core.providers import LLMProvider

# Keep the real boundary available even when other tests replace network calls.
REAL_COMPLETE = LLMProvider.complete


def test_default_provider_is_live_and_missing_key_is_an_error(monkeypatch):
    monkeypatch.delenv('PROVIDER_MODE', raising=False)
    monkeypatch.setenv('LLM_API_KEY', '')
    provider = LLMProvider()
    assert provider.mode == 'live'
    with pytest.raises(HTTPException) as error:
        REAL_COMPLETE(provider, '测试任务', {})
    assert error.value.status_code == 503


def test_legacy_mock_configuration_cannot_return_fake_output(monkeypatch):
    monkeypatch.setenv('PROVIDER_MODE', 'mock')
    with pytest.raises(HTTPException) as error:
        REAL_COMPLETE(LLMProvider(), '测试任务', {})
    assert error.value.status_code == 503


def test_global_chat_searches_all_public_knowledge_despite_page_filters():
    from fastapi.testclient import TestClient
    from services.api.main import create_app
    with TestClient(create_app('sqlite://')) as client:
        body = {'message':'海外渠道销售与KOL营销','role':'unknown-role','industry':'unknown-industry'}
        result = client.post('/api/v1/ai/chat', json={**body, 'scope':'global'})
        assert result.status_code == 200
        assert result.json()['citations']
        scoped = client.post('/api/v1/ai/chat', json={**body, 'scope':'learning'})
        assert scoped.status_code == 200
        # Universal overview/glossary references are available across role filters.
        assert all(c['source_type'] == 'site_reference' and c['doc_id'].startswith('gtm-reference-') for c in scoped.json()['citations'])
