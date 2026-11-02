"""Check the effective prompts sent by both resume rewrite entry points."""
import json

import pytest

from packages.agent_core.providers import LLMProvider
from packages.career.graph import diagnose
from services.api.resume_blocks import BlockDialogue, discuss_block
from services.api.suggestions import SuggestRewrite, suggest
from tests.test_rewrite_budget import REAL_COMPLETE, model_response


@pytest.mark.parametrize('entry', ['paragraph', 'block'])
def test_rewrite_requests_share_evidence_based_guidance(monkeypatch, entry):
    response = {'patches': [{'fact_id': 'f1', 'text': '参与客户访谈，整理需求表。'}]} if entry == 'paragraph' else {
        'text': '参与客户访谈，整理需求表。', 'analysis': '突出交付物', 'questions': '', 'source_chunk_ids': []}
    captured = model_response(monkeypatch, json.dumps(response, ensure_ascii=False))
    monkeypatch.setattr(LLMProvider, 'complete', REAL_COMPLETE)
    facts = [{'id': 'f1', 'text': '参与访谈并整理需求', 'section': 'experience'}]
    jd = '负责 DTC 渠道增长，要求独立主导项目'
    if entry == 'paragraph':
        suggest(facts, SuggestRewrite(approved_fact_ids=['f1'], instruction='突出调研能力'), jd)
    else:
        discuss_block(facts, BlockDialogue(fact_ids=['f1'], draft_text=facts[0]['text'], message='突出调研能力'), jd, [], {})

    system = captured['messages'][0]['content']
    task = json.loads(captured['messages'][1]['content'])
    for rule in ['个人边界', '方案测算', '团队结果', '最多 5 个', 'JD 和公共资料不能作为个人经历的证据']:
        assert rule in system
    for obsolete in ['新增方向可提供候选职责', '原文不是内容上限', '新增或推演的部分只在 analysis']:
        assert obsolete not in system + task['task']
    assert task['untrusted_data']['jd'] == jd
    assert facts[0]['text'] == '参与访谈并整理需求'


def test_diagnosis_request_distinguishes_missing_evidence_from_real_gaps(monkeypatch):
    captured = model_response(monkeypatch, '现有调研经历可支持部分要求；渠道经验待确认。')
    monkeypatch.setattr(LLMProvider, 'complete', REAL_COMPLETE)
    result = diagnose([{'id': 'f1', 'text': '参与客户调研'}], '要求渠道运营经验', 'gtm')
    system = captured['messages'][0]['content']
    for status in ['已匹配', '表达缺口', '证据不足', '真实缺口', '待确认', '硬性条件']:
        assert status in system
    assert result['rubric_version'] == 'resume-rubric-1'
    assert result['analysis'] == '现有调研经历可支持部分要求；渠道经验待确认。'
