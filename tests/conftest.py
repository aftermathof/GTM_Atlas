"""Offline tests must never inherit real provider keys from a developer's .env."""
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["PROVIDER_MODE"] = "live"
os.environ["DATA_DIR"] = str(Path('.data/tests').resolve())
for prefix in ["LLM", "STT", "VISION", "EMBEDDING"]:
    os.environ[prefix + "_API_KEY"] = ""
for prefix in ["STT", "VISION", "EMBEDDING"]:
    os.environ[prefix + "_BASE_URL"] = ""
os.environ["RENDER_ENABLED"] = "false"
os.environ['AUTH_MODE'] = 'local'
os.environ['STORAGE_MODE'] = 'local'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = ''
os.environ['SUPABASE_ANON_KEY'] = ''

import json
import shutil
import pytest
from packages.agent_core.providers import LLMProvider
from packages.career.structure import local_structure
from services.api.config import ROOT


def offline_complete(self, task, payload):
    """Only tests can return fixed responses; production has no fallback path."""
    if '提取简历' in task:
        return json.dumps(local_structure(payload['facts']), ensure_ascii=False)
    if '题目规划' in task:
        return json.dumps({'questions': payload['blueprint']}, ensure_ascii=False)
    if 'dimensions' in task:
        answer = payload['confirmed_answer']
        return json.dumps({'dimensions': {name: 2 for name in ['相关性','结构性','专业准确性','可验证经历','商业逻辑','沟通表达']}, 'feedback':'请说明个人行动及验证方式。', 'evidence':answer[:240], 'followup':'如何验证个人行动的结果？' if len(answer)<100 else None}, ensure_ascii=False)
    if 'patches' in task:
        return json.dumps({'patches':[{'fact_id':f['id'],'text':f['text'].rstrip('。；;')+'。','reason':'测试表达调整','source_chunk_ids':[]} for f in payload['facts']]}, ensure_ascii=False)
    if '诊断' in task:
        return '请核对个人职责、行动与可验证结果。'
    return '\n\n'.join(e['text'][:700] + '\n[' + e['chunk_id'] + ']' for e in payload.get('evidence',[])[:3]) or '请核对当前简历事实。'


@pytest.fixture(scope='session')
def regression_knowledge(tmp_path_factory):
    root = tmp_path_factory.mktemp('regression-knowledge')
    shutil.copytree(ROOT/'knowledge', root/'knowledge')
    shutil.copytree(ROOT/'tests/fixtures/knowledge', root/'knowledge', dirs_exist_ok=True)
    return root


@pytest.fixture(autouse=True)
def isolate_model_and_knowledge(monkeypatch, regression_knowledge):
    monkeypatch.setattr(LLMProvider, 'complete', offline_complete)
    monkeypatch.setattr('packages.rag.knowledge.ROOT', regression_knowledge)
