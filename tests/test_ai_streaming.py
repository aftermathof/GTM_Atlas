import asyncio
import json
import threading

import httpx
import pytest
from fastapi import APIRouter, FastAPI, HTTPException

from packages.agent_core.providers import LLMProvider
from tests.test_workflows import client, login

REAL_COMPLETE = LLMProvider.complete


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


def test_structured_preview_decodes_partial_escapes_and_preserves_literal_backslashes():
    from packages.agent_core.streaming import json_preview
    assert json_preview('{"text":"正文\\u4e') == '正文'
    assert json_preview('{"text":"正文\\u4e2d') == '正文中'
    assert json_preview('{"text":"正文\\ud83d') == '正文'
    assert json_preview('{"text":"正文\\ud83d\\ude80') == '正文🚀'
    assert json_preview(json.dumps({'text': '目录 C:\\', 'source_chunk_ids': ['secret:0']})) == '目录 C:\\'


def test_provider_uses_real_stream_and_emits_readable_structured_fields(monkeypatch):
    from packages.agent_core.streaming import stream_sink
    observed, requests = [], []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_lines(self):
            for part in ['{"text":"候选', '稿\\n第二行","analysis":"说明","source_chunk_ids":["private:0"]}']:
                yield 'data: ' + json.dumps({'choices': [{'delta': {'content': part}}]})
                yield ''
                assert any(event['type'] == 'delta' for event in observed)
            yield 'data: [DONE]'
            yield ''

    def stream(*args, **kwargs):
        requests.append(kwargs)
        return Response()

    monkeypatch.setenv('LLM_API_KEY', 'not-a-real-key')
    monkeypatch.setattr(httpx, 'stream', stream)
    token = stream_sink.set(observed.append)
    try:
        result = REAL_COMPLETE(LLMProvider(), '简历分块多轮改写，只返回JSON', {})
    finally:
        stream_sink.reset(token)
    assert json.loads(result)['text'] == '候选稿\n第二行'
    assert requests[0]['json']['stream'] is True
    preview = ''.join(event['text'] for event in observed if event['type'] == 'delta')
    assert '候选稿\n第二行' in preview and '说明' in preview
    assert 'source_chunk_ids' not in preview and 'private:0' not in preview


def test_provider_rejects_truncated_stream(monkeypatch):
    from packages.agent_core.streaming import stream_sink

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_lines(self):
            yield 'data: ' + json.dumps({'choices': [{'delta': {'content': '部分回答'}}]})
            yield ''

    monkeypatch.setenv('LLM_API_KEY', 'not-a-real-key')
    monkeypatch.setattr(httpx, 'stream', lambda *a, **kw: Response())
    token = stream_sink.set(lambda event: None)
    try:
        with pytest.raises(HTTPException) as error:
            REAL_COMPLETE(LLMProvider(), '普通问答', {})
        assert error.value.status_code == 502
    finally:
        stream_sink.reset(token)


def test_chat_stream_keeps_final_validation_and_owned_history(client, monkeypatch):
    from packages.agent_core.streaming import emit_stream
    headers = login(client)

    def complete(self, task, payload):
        emit_stream({'type': 'start', 'label': '正在回答', 'model': self.model})
        emit_stream({'type': 'delta', 'text': '你好'})
        emit_stream({'type': 'delta', 'text': '，继续交流。'})
        return '你好，继续交流。'

    monkeypatch.setattr(LLMProvider, 'complete', complete)
    response = client.post('/api/v1/ai/chat', headers={**headers, 'Accept': 'text/event-stream'}, json={'message': '你好', 'scope': 'global'})
    assert response.headers['content-type'].startswith('text/event-stream')
    items = events(response)
    assert ''.join(e['text'] for e in items if e['type'] == 'delta') == '你好，继续交流。'
    final = next(e['value'] for e in items if e['type'] == 'result')
    history = client.get('/api/v1/ai/conversations/' + final['conversation_id'], headers=headers).json()
    assert history['messages'][0]['response']['answer'] == final['answer']
    other = login(client, 'other')
    assert client.get('/api/v1/ai/conversations/' + final['conversation_id'], headers=other).status_code == 404


def test_failed_stream_does_not_save_partial_chat_and_auth_stays_http(client, monkeypatch):
    from packages.agent_core.streaming import emit_stream
    headers = login(client)

    def complete(*args):
        emit_stream({'type': 'delta', 'text': '未完成'})
        raise HTTPException(502, '模型连接中断')

    monkeypatch.setattr(LLMProvider, 'complete', complete)
    response = client.post('/api/v1/ai/chat', headers={**headers, 'Accept': 'text/event-stream'}, json={'message': '你好'})
    items = events(response)
    assert any(e['type'] == 'error' for e in items)
    assert not any(e['type'] == 'result' for e in items)
    assert client.get('/api/v1/ai/conversations', headers=headers).json() == []
    assert client.post('/api/v1/ai/chat', headers={'Authorization': 'Bearer invalid', 'Accept': 'text/event-stream'}, json={'message': '你好'}).status_code == 401


def test_streamed_mock_feedback_is_applied_only_after_structured_validation(client, monkeypatch):
    from packages.agent_core.streaming import emit_stream
    from tests.conftest import offline_complete
    headers = login(client)
    session = client.post('/api/v1/mock/sessions', headers=headers, json={'count': 3}).json()
    sid = session['id']
    body = {'answer': '我负责验证渠道需求并跟踪实验指标。' * 12, 'question_index': 0, 'idempotency_key': 'stream-answer'}

    def invalid(*args):
        emit_stream({'type': 'delta', 'text': '未经校验的反馈'})
        return '{invalid json'

    monkeypatch.setattr(LLMProvider, 'complete', invalid)
    response = client.post(f'/api/v1/mock/sessions/{sid}/answers', headers={**headers, 'Accept': 'text/event-stream'}, json=body)
    assert any(e['type'] == 'error' for e in events(response))
    saved = client.get(f'/api/v1/mock/sessions/{sid}', headers=headers).json()
    assert saved['current_question_index'] == 0 and saved['answers'] == []

    def valid(self, task, payload):
        emit_stream({'type': 'start', 'label': '正在分析回答', 'model': self.model})
        emit_stream({'type': 'delta', 'text': '完整的反馈'})
        return offline_complete(self, task, payload)

    monkeypatch.setattr(LLMProvider, 'complete', valid)
    response = client.post(f'/api/v1/mock/sessions/{sid}/answers', headers={**headers, 'Accept': 'text/event-stream'}, json=body)
    final = next(e['value'] for e in events(response) if e['type'] == 'result')
    assert final['current_question_index'] == 1
    assert len(final['answers']) == 1


def test_route_delivers_delta_before_operation_finishes():
    from packages.agent_core.streaming import emit_stream
    from services.api.streaming import AIStreamingRoute
    released = threading.Event()
    router = APIRouter(route_class=AIStreamingRoute)

    @router.post('/generate')
    def generate():
        emit_stream({'type': 'delta', 'text': '先显示'})
        assert released.wait(3), 'stream was buffered until completion'
        return {'answer': '已完成'}

    app = FastAPI()
    app.include_router(router)

    async def check():
        sent = []
        received = False
        async def receive():
            nonlocal received
            if not received:
                received = True
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            await asyncio.Event().wait()
        async def send(message):
            sent.append(message)
            if b'"type": "delta"' in message.get('body', b''):
                released.set()
        await app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'POST', 'scheme': 'http', 'path': '/generate', 'raw_path': b'/generate', 'query_string': b'', 'root_path': '', 'headers': [(b'accept', b'text/event-stream')], 'client': ('test', 1), 'server': ('test', 80)}, receive, send)
        assert released.is_set()
        assert b'"type": "result"' in b''.join(m.get('body', b'') for m in sent)
    asyncio.run(check())
