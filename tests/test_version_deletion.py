import pytest
import json
from fastapi import HTTPException
from packages.career.graph import apply_patches
from services.api.schemas import Patch
from tests.test_workflows import client, login
from packages.agent_core.providers import LLMProvider
from services.api.suggestions import suggest, SuggestRewrite


def test_cleared_authorized_paragraph_is_removed_only_from_new_facts():
    original = [{'id':'f0','text':'教育：本科','locked':True}, {'id':'f1','text':'重复的经历描述','locked':False}]
    result = apply_patches(original, [Patch(fact_id='f1', text='')], ['f1'])
    assert [f['id'] for f in result] == ['f0']
    assert original[1]['text'] == '重复的经历描述'


def test_locked_paragraph_cannot_be_cleared():
    with pytest.raises(HTTPException) as error:
        apply_patches([{'id':'f0','text':'教育：本科','locked':True}], [Patch(fact_id='f0',text='')], ['f0'])
    assert error.value.status_code == 422


def test_cannot_generate_an_empty_resume():
    with pytest.raises(HTTPException) as error:
        apply_patches([{'id':'f0','text':'原文','locked':False}], [Patch(fact_id='f0',text='   ')], ['f0'])
    assert error.value.status_code == 422


def test_user_can_save_new_details_and_numbers_in_an_authorized_paragraph():
    original = [{'id':'f1','text':'参与市场调研','locked':False}]
    text = '参与 DTC 渠道调研，整理 30 个 Kickstarter 项目。'
    result = apply_patches(original, [Patch(fact_id='f1',text=text)], ['f1'])
    assert result[0]['text'] == text
    assert original[0]['text'] == '参与市场调研'


def test_ai_suggestions_cannot_silently_remove_paragraphs(monkeypatch):
    monkeypatch.setattr(LLMProvider, 'complete', lambda *a: json.dumps({'patches':[{'fact_id':'f1','text':''}]}))
    with pytest.raises(HTTPException) as error:
        suggest([{'id':'f1','text':'原始经历','locked':False}], SuggestRewrite(approved_fact_ids=['f1']), '')
    assert error.value.status_code == 502


def test_generation_accepts_cleared_paragraph_and_preserves_original(client):
    headers = login(client)
    original = '姓名：测试同学\n教育：示例大学 本科\n经历：负责培训资料整理\n技能：Excel，英语'
    resume = client.post('/api/v1/career/resumes', files={'file':('resume.txt',original.encode(),'text/plain')},headers=headers).json()
    session = client.post('/api/v1/career/sessions',json={'resume_id':resume['id']},headers=headers).json()
    sid = session['id']
    client.post(f'/api/v1/career/sessions/{sid}/confirm-facts',json={'facts':session['facts']},headers=headers)
    response = client.post(f'/api/v1/career/sessions/{sid}/approve-rewrite',json={'patches':[{'fact_id':'f3','text':''}],'approved_fact_ids':['f3'],'template':'gtm-original'},headers=headers)
    assert response.status_code == 200, response.text
    assert 'f3' not in {f['id'] for f in response.json()['facts']}
    assert client.get(f'/api/v1/career/sessions/{sid}',headers=headers).json()['facts'] == session['facts']
    source = client.get(f'/api/v1/career/versions/{response.json()["id"]}/download/tex',headers=headers)
    assert source.status_code == 200
    assert 'Excel' not in source.text
