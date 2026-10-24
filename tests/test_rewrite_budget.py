import httpx
import pytest
from fastapi import HTTPException
from packages.agent_core.providers import LLMProvider

REAL_COMPLETE = LLMProvider.complete


def model_response(monkeypatch, content='{"patches": []}', finish_reason='stop'):
    monkeypatch.setenv('LLM_API_KEY', 'test-key')
    monkeypatch.setenv('LLM_MODEL', 'deepseek-flash')
    captured = {}

    def post(url, **kwargs):
        captured.update(kwargs['json'])
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'choices': [{'finish_reason': finish_reason, 'message': {'content': content}}]
        })

    monkeypatch.setattr(httpx, 'post', post)
    return captured


@pytest.mark.parametrize('task', ['只返回JSON {patches:[]}', '题目规划：返回JSON {questions:[]}'])
def test_structured_tasks_reserve_output_for_answer(monkeypatch, task):
    captured = model_response(monkeypatch)
    assert REAL_COMPLETE(LLMProvider(), task, {}) == '{"patches": []}'
    assert captured['max_tokens'] == 8192
    assert captured['thinking'] == {'type': 'disabled'}


def test_other_tasks_keep_existing_budget(monkeypatch):
    captured = model_response(monkeypatch, '回答')
    assert REAL_COMPLETE(LLMProvider(), '学习问答', {}) == '回答'
    assert captured['max_tokens'] == 2400
    assert 'thinking' not in captured


@pytest.mark.parametrize('content,finish_reason', [('', 'length'), ('{"patches":[', 'length'), ('', 'stop')])
def test_incomplete_answer_has_actionable_error(monkeypatch, content, finish_reason):
    model_response(monkeypatch, content, finish_reason)
    with pytest.raises(HTTPException) as error:
        REAL_COMPLETE(LLMProvider(), '只返回JSON {patches:[]}', {})
    assert error.value.status_code == 503
    assert '未返回完整正文' in error.value.detail
