from packages.agent_core.providers import LLMProvider
from packages.learning.graph import answer_question
from services.api.schemas import Chat


def test_greeting_skips_retrieval_and_reaches_model(monkeypatch):
    def unexpected_search(*args, **kwargs):
        raise AssertionError('A greeting should not require a knowledge search')

    monkeypatch.setattr('packages.learning.graph.search', unexpected_search)
    monkeypatch.setattr(LLMProvider, 'complete', lambda self, task, payload: '你好！想聊什么？')
    result = answer_question(None, Chat(message='你好！'))
    assert result['answer'] == '你好！想聊什么？'
    assert result['citations'] == []


def test_general_answer_without_citations_is_not_blocked(monkeypatch):
    monkeypatch.setattr('packages.learning.graph.search', lambda *a, **k: [
        {'chunk_id': 'example:0', 'permission': 'public_display'},
    ])
    monkeypatch.setattr(LLMProvider, 'complete', lambda self, task, payload: '可以先明确目标，再分解行动。')
    result = answer_question(None, Chat(message='我应该怎么开始准备？'))
    assert result['answer'] == '可以先明确目标，再分解行动。'
    assert result['citations'] == []
    assert '一般' in result['limitations']


def test_missing_knowledge_still_allows_general_conversation(monkeypatch):
    monkeypatch.setattr('packages.learning.graph.search', lambda *a, **k: [])
    monkeypatch.setattr(LLMProvider, 'complete', lambda self, task, payload: '我们可以一起梳理你的目标。')
    result = answer_question(None, Chat(message='我有点迷茫，想聊聊职业方向'))
    assert result['answer'] == '我们可以一起梳理你的目标。'


def test_forged_sources_are_still_rejected(monkeypatch):
    monkeypatch.setattr('packages.learning.graph.search', lambda *a, **k: [])
    monkeypatch.setattr(LLMProvider, 'complete', lambda self, task, payload: '参考 [invented:0]')
    result = answer_question(None, Chat(message='介绍一下 GTM'))
    assert '引用校验失败' in result['answer']
    assert not result['citations']
