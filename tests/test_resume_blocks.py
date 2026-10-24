import json
import os
import pytest
from fastapi import HTTPException
from packages.agent_core.providers import LLMProvider
from services.api.resume_blocks import group_blocks, apply_block_patches, BlockPatch, BlockDialogue, discuss_block

FACTS = [
    {'id':'f0','text':'教育：示例大学','section':'education','locked':True},
    {'id':'f1','text':'甲公司 2025 实习','section':'experience'},
    {'id':'f2','text':'调研 20 家客户','section':'experience'},
    {'id':'f3','text':'乙公司 2026 实习','section':'experience'},
]

def test_grouping_preserves_source_order_and_separates_experiences(monkeypatch):
    blocks=[{'title':'教育背景','fact_ids':['f0']},{'title':'实习经历 1','fact_ids':['f1','f2']},{'title':'实习经历 2','fact_ids':['f3']}]
    monkeypatch.setattr(LLMProvider,'complete',lambda *args: json.dumps({'blocks':blocks}))
    result=group_blocks(FACTS,{})
    assert result[1]['fact_ids']==['f1','f2']
    assert result[0]['locked'] is True
    assert result[1]['section']=='experience'

def test_grouping_is_local_lossless_and_keeps_locked_sections_separate(monkeypatch):
    monkeypatch.setattr(LLMProvider,'complete',lambda *args: (_ for _ in ()).throw(AssertionError('must not call model')))
    result=group_blocks(FACTS,{})
    assert [fid for block in result for fid in block['fact_ids']]==[f['id'] for f in FACTS]
    assert result[0]['fact_ids']==['f0']
    assert result[0]['locked'] is True
    assert result[1]['fact_ids']==['f1','f2']
    assert result[2]['fact_ids']==['f3']

def test_whole_block_rewrite_can_reorder_existing_numbers_and_keeps_other_experience():
    result=apply_block_patches(FACTS,[BlockPatch(fact_ids=['f1','f2'],text='2025 年在甲公司实习，调研 20 家客户。')],['f1','f2'])
    assert [f['id'] for f in result]==['f0','f1','f3']
    assert result[1]['section']=='experience'
    assert result[-1]==FACTS[-1]

@pytest.mark.parametrize('ids,text,approved', [(['f0'],'教育背景',['f0']),(['f1','f2'],'整理调研',['f1']),(['f1','f3'],'合并',['f1','f3'])])
def test_block_rewrite_requires_unlocked_contiguous_authorized_facts(ids,text,approved):
    with pytest.raises(HTTPException): apply_block_patches(FACTS,[BlockPatch(fact_ids=ids,text=text)],approved)

def test_block_dialogue_uses_current_draft_history_jd_and_retrieved_evidence(monkeypatch):
    captured={}
    def complete(self,task,payload):
        captured.update(payload)
        return json.dumps({'text':'调研 20 家客户。','analysis':'突出调研对象','questions':'','source_chunk_ids':['jd:0']})
    monkeypatch.setattr(LLMProvider,'complete',complete)
    body=BlockDialogue(fact_ids=['f1','f2'],draft_text='调研客户',message='突出调研',history=[{'message':'先梳理职责','text':'调研客户','analysis':'初稿','questions':''}])
    result=discuss_block(FACTS,body,'目标 JD',[{'chunk_id':'jd:0'}],{})
    assert captured['draft_text']=='调研客户'
    assert captured['history'][0]['message']=='先梳理职责'
    assert captured['jd']=='目标 JD'
    assert result['citations']==[{'chunk_id':'jd:0'}]
    assert FACTS[1]['text']=='甲公司 2025 实习'


@pytest.mark.parametrize('response', [
    {'analysis':'建议你精简内容并突出岗位能力'},
])
def test_rewrite_does_not_present_unchanged_draft_or_analysis_only_as_a_result(monkeypatch, response):
    monkeypatch.setattr(LLMProvider, 'complete', lambda *args: json.dumps(response))
    with pytest.raises(HTTPException) as error:
        discuss_block(FACTS, BlockDialogue(fact_ids=['f1','f2'], draft_text='调研 20 家客户', message='改为更精简的简历表达'), '', [], {})
    assert error.value.status_code == 502
    assert '改写' in error.value.detail


def test_rewrite_cleans_model_inputs_and_returns_replaceable_text(monkeypatch):
    captured = {}
    def complete(self, task, payload):
        captured.update(task=task, payload=payload)
        return json.dumps({'text':'• ϻ访谈并整理 20 家客户需求。', 'analysis':'精简句式，突出需求整理。'})
    monkeypatch.setattr(LLMProvider, 'complete', complete)
    facts = [{**f, 'text':'ϻ '+f['text']} for f in FACTS]
    result = discuss_block(facts, BlockDialogue(fact_ids=['f1','f2'], draft_text='• ϻ调研 20 家客户', message='用行动开头'), '', [], {})
    assert captured['payload']['draft_text'] == '调研 20 家客户'
    assert captured['payload']['facts'][0]['text'] == '甲公司 2025 实习'
    assert '可直接替换' in captured['task']
    assert '不要复述' in captured['task']
    assert result['text'] == '访谈并整理 20 家客户需求。'
    assert facts[1]['text'].startswith('ϻ ')


def test_unchanged_model_draft_is_corrected_once_before_returning_a_result(monkeypatch):
    calls = []
    def complete(self, task, payload):
        calls.append(task)
        text = '调研 20 家客户。' if len(calls) == 1 else '面向 20 家客户开展调研。'
        return json.dumps({'text':text,'analysis':'调整句式以突出调研对象'})
    monkeypatch.setattr(LLMProvider, 'complete', complete)
    result = discuss_block(FACTS, BlockDialogue(fact_ids=['f1','f2'],draft_text='调研 20 家客户',message='让表达更专业'), '', [], {})
    assert result['text'] == '面向 20 家客户开展调研。'
    assert len(calls) == 2
    assert '上次未提供实际改写' in calls[1]
    assert FACTS[2]['text'] == '调研 20 家客户'


def test_unchanged_model_correction_has_a_strict_retry_limit(monkeypatch):
    calls = []
    def complete(self, *args):
        calls.append(1)
        return json.dumps({'text':'调研 20 家客户','analysis':'保留事实'})
    monkeypatch.setattr(LLMProvider, 'complete', complete)
    result = discuss_block(FACTS, BlockDialogue(fact_ids=['f1','f2'],draft_text='调研 20 家客户',message='优化表达'), '', [], {})
    assert result['text'] == ''
    assert result['questions']
    assert len(calls) == 2


def test_requested_dtc_and_kickstarter_content_is_drafted_instead_of_blocked(monkeypatch):
    calls = []
    def complete(self, task, payload):
        calls.append(task)
        return json.dumps({'text':'围绕 DTC 渠道与 Kickstarter 众筹开展竞品调研，整理 30 个项目的定位、定价及卖点，形成市场分析表。','analysis':'补充平台研究方向；新增职责表述请核对后采用。','questions':''})
    monkeypatch.setattr(LLMProvider, 'complete', complete)
    result = discuss_block(FACTS, BlockDialogue(fact_ids=['f1','f2'],draft_text='调研 20 家客户',message='确实需要添加一些比如像DTC还有Kickstarter这样的一些经验更贴合GTM岗位'), '', [], {})
    assert 'Kickstarter' in result['text']
    assert 'DTC' in result['text']
    assert '30' in result['text']
    assert '候选草稿' in calls[0]
    assert '先询问其实际参与' not in calls[0]
    assert len(calls) == 1


def test_dialogue_still_rejects_unknown_citations_and_tex_commands(monkeypatch):
    for response in [{'text':r'\input{secret}','analysis':'','questions':'','source_chunk_ids':[]},{'text':'调研','analysis':'','questions':'','source_chunk_ids':['fake:0']}]:
        monkeypatch.setattr(LLMProvider,'complete',lambda *args: json.dumps(response))
        with pytest.raises(HTTPException): discuss_block(FACTS,BlockDialogue(fact_ids=['f1','f2'],draft_text='调研',message='优化'),'',[],{})


def test_user_confirmed_additions_can_be_saved_without_reentering_fact_screen():
    text = '围绕 DTC 与 Kickstarter 调研 30 个项目，形成竞品对比表。'
    result = apply_block_patches(FACTS, [BlockPatch(fact_ids=['f1','f2'], text=text)], ['f1','f2'])
    assert result[1]['text'] == text
    assert FACTS[2]['text'] == '调研 20 家客户'


def test_empty_block_can_be_drafted_from_requested_job_direction(monkeypatch):
    monkeypatch.setattr(LLMProvider, 'complete', lambda *args: json.dumps({'text':'围绕 DTC 独立站与 Kickstarter 众筹整理竞品定位、渠道打法和卖点，形成上市研究简报。','analysis':'按要求起草，平台研究方向可继续调整。','questions':''}))
    result = discuss_block(FACTS, BlockDialogue(fact_ids=['f1','f2'],draft_text='',message='起草 DTC 与 Kickstarter 相关的 GTM 项目经历'), '', [], {})
    assert result['text']
    assert not result['questions']


from tests.test_workflows import client, login

def test_block_routes_cache_groups_enforce_privacy_and_generate_only_on_confirmation(client, monkeypatch):
    owner, other = login(client), login(client,'bob')
    resume = client.post('/api/v1/career/resumes',files={'file':('resume.txt','姓名：示例\n教育：示例大学\n实习：甲公司\n调研 20 家客户'.encode(),'text/plain')},headers=owner).json()
    session = client.post('/api/v1/career/sessions',json={'resume_id':resume['id'],'jd':'海外 GTM 调研与上市'},headers=owner).json()
    sid=session['id']
    assert client.get(f'/api/v1/career/sessions/{sid}/editing-blocks',headers=owner).status_code==409
    assert client.post(f'/api/v1/career/sessions/{sid}/confirm-facts',json={'facts':FACTS},headers=owner).status_code==200
    calls=[]
    def complete(self,task,payload):
        calls.append((task,payload))
        if '简历经历分块' in task:
            return json.dumps({'blocks':[{'title':'教育背景','fact_ids':['f0']},{'title':'实习经历 1','fact_ids':['f1','f2']},{'title':'实习经历 2','fact_ids':['f3']}]})
        return json.dumps({'text':'甲公司 2025 年实习，围绕 DTC 与 Kickstarter 调研 30 个项目。','analysis':'结合岗位要求补充平台调研内容','questions':'','source_chunk_ids':[]})
    monkeypatch.setattr(LLMProvider,'complete',complete)
    first=client.get(f'/api/v1/career/sessions/{sid}/editing-blocks',headers=owner)
    assert first.status_code==200,first.text
    assert len(first.json()['blocks'])==3
    assert client.get(f'/api/v1/career/sessions/{sid}/editing-blocks',headers=owner).status_code==200
    assert len(calls)==0
    assert client.get(f'/api/v1/career/sessions/{sid}/editing-blocks',headers=other).status_code==404
    body={'fact_ids':['f1','f2'],'draft_text':'甲公司实习，调研客户','message':'与岗位职能联系','history':[]}
    assert client.post(f'/api/v1/career/sessions/{sid}/block-dialogue',json=body,headers=other).status_code==404
    reply=client.post(f'/api/v1/career/sessions/{sid}/block-dialogue',json=body,headers=owner)
    assert reply.status_code==200,reply.text
    assert '30' in reply.json()['text'] and 'Kickstarter' in reply.json()['text']
    assert calls[-1][1]['jd']=='海外 GTM 调研与上市'
    assert calls[-1][1]['evidence']
    assert client.get(f'/api/v1/career/sessions/{sid}/versions',headers=owner).json()==[]
    assert client.get(f'/api/v1/career/sessions/{sid}',headers=owner).json()['facts'][1]['text']==FACTS[1]['text']
    saved=client.post(f'/api/v1/career/sessions/{sid}/approve-rewrite',json={'blocks':[{'fact_ids':['f1','f2'],'text':reply.json()['text']}],'approved_fact_ids':['f1','f2'],'template':'classic-cn'},headers=owner)
    assert saved.status_code==200,saved.text
    assert saved.json()['facts'][1]['text']==reply.json()['text']
    assert saved.json()['facts'][0]['locked'] is True
    assert saved.json()['facts'][2]['text']==FACTS[3]['text']
    assert client.post(f'/api/v1/career/sessions/{sid}/block-dialogue',json={**body,'base_version_id':saved.json()['id']},headers=other).status_code==404
    assert client.get(f'/api/v1/career/sessions/{sid}',headers=owner).json()['facts'][1]['text']==FACTS[1]['text']


def test_empty_draft_can_ask_questions_without_inventing_a_resume(monkeypatch):
    monkeypatch.setattr(LLMProvider,'complete',lambda *args: json.dumps({'text':'','analysis':'先梳理真实经历','questions':'你在实习中具体负责什么？','source_chunk_ids':[]}))
    result=discuss_block(FACTS,BlockDialogue(fact_ids=['f1','f2'],draft_text='',message='和 AI 聊聊'),'',[],{})
    assert result['text']==''
    assert '负责什么' in result['questions']


@pytest.mark.parametrize('stage', ['retrieval','rewrite'])
def test_rewrite_failure_logs_stage_and_preserves_readable_cors_response(client, monkeypatch, caplog, stage):
    origin = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')[0]
    owner = login(client)
    resume = client.post('/api/v1/career/resumes', files={'file':('test.txt','姓名：示例\n教育：示例大学\n项目经历：调研客户并整理需求表'.encode(),'text/plain')}, headers=owner).json()
    session = client.post('/api/v1/career/sessions', json={'resume_id':resume['id']}, headers=owner).json()
    sid = session['id']
    client.post(f'/api/v1/career/sessions/{sid}/confirm-facts', json={'facts':FACTS}, headers=owner)
    def fail(*args, **kwargs):
        raise HTTPException(502, '测试服务暂不可用')
    monkeypatch.setattr('services.api.routes_career.career_evidence', fail if stage == 'retrieval' else lambda *a, **k: [])
    if stage == 'rewrite':
        monkeypatch.setattr('services.api.routes_career.discuss_block', fail)
    response = client.post(f'/api/v1/career/sessions/{sid}/block-dialogue', json={'fact_ids':['f1','f2'],'draft_text':'私有草稿不得写入日志','message':'私有输入不得写入日志'}, headers={**owner,'Origin':origin})
    assert response.status_code == 502
    assert response.json()['detail'] == '测试服务暂不可用'
    assert response.headers['access-control-allow-origin'] == origin
    assert 'stage='+stage in caplog.text
    assert '私有' not in caplog.text


def test_block_route_services_with_sqlite_preserve_private_sources_and_version_boundary(monkeypatch):
    # Exercise service logic without a socket-based TestClient.
    from types import SimpleNamespace
    import threading
    from sqlalchemy import select
    from services.api.db import Base, Record, make_database
    from services.api.store import save, owned
    from services.api.routes_career import editing_blocks, block_dialogue, rewrite
    from services.api.schemas import Rewrite
    engine, factory=make_database('sqlite://')
    Base.metadata.create_all(engine)
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=factory,mutation_lock=threading.RLock())))
    user=SimpleNamespace(id='owner')
    with factory() as db:
        record=save(db,user.id,'career',{'facts':FACTS,'confirmed':True,'context':{'jd':'目标岗位调研','role':'overseas_channel_sales'},'structure':{'assignments':{f['id']:f['section'] for f in FACTS}},'editing_blocks':[]})
        sid=record.id
        db.commit()
    calls=[]
    def complete(self,task,payload):
        calls.append(payload)
        if '简历经历分块' in task:
            return json.dumps({'blocks':[{'title':'教育背景','fact_ids':['f0']},{'title':'实习经历 1','fact_ids':['f1','f2']},{'title':'实习经历 2','fact_ids':['f3']}]})
        return json.dumps({'text':'甲公司 2025 实习，调研 20 家客户。','analysis':'对应岗位调研要求','questions':'','source_chunk_ids':['jd:0']})
    monkeypatch.setattr(LLMProvider,'complete',complete)
    monkeypatch.setattr('services.api.routes_career.career_evidence',lambda *args,**kwargs:[{'chunk_id':'jd:0','text':'岗位需要调研能力'}])
    assert len(editing_blocks(sid,request,user=user)['blocks'])==3
    assert len(editing_blocks(sid,request,user=user)['blocks'])==3
    assert len(calls)==0
    with pytest.raises(HTTPException) as denied:
        editing_blocks(sid,request,user=SimpleNamespace(id='other'))
    assert denied.value.status_code==404
    response=block_dialogue(sid,BlockDialogue(fact_ids=['f1','f2'],draft_text='甲公司实习',message='突出调研'),request,user=user)
    assert calls[-1]['jd']=='目标岗位调研'
    assert response['citations'][0]['chunk_id']=='jd:0'
    with factory() as db:
        assert not list(db.scalars(select(Record).where(Record.kind=='resume_version')))
        assert owned(db,sid,user.id,'career').data['facts']==FACTS
    saved=rewrite(sid,Rewrite(blocks=[BlockPatch(fact_ids=['f1','f2'],text=response['text'])],approved_fact_ids=['f1','f2']),request,user=user)
    assert saved['facts'][1]['text']==response['text']
    assert saved['facts'][0]['locked'] is True
    with factory() as db:
        assert owned(db,sid,user.id,'career').data['facts']==FACTS
        assert len(list(db.scalars(select(Record).where(Record.kind=='resume_version'))))==1
    # Selecting someone else's version and a version from another resume must fail.
    with factory() as db:
        unrelated=save(db,user.id,'resume_version',{'facts':FACTS},'different-resume')
        unrelated_id=unrelated.id
        db.commit()
    with pytest.raises(HTTPException) as wrong_version:
        block_dialogue(sid,BlockDialogue(fact_ids=['f1'],message='优化',base_version_id=unrelated_id),request,user=user)
    assert wrong_version.value.status_code==422
    engine.dispose()


@pytest.mark.parametrize('value', [[], {}, {'text':42}, {'text':'建议','source_chunk_ids':['unknown:0']}])
def test_invalid_dialogue_output_has_readable_error(monkeypatch,value):
    monkeypatch.setattr(LLMProvider,'complete',lambda *args:json.dumps(value))
    with pytest.raises(HTTPException) as error:
        discuss_block(FACTS,BlockDialogue(fact_ids=['f1','f2'],message='优化'),'',[],{})
    assert error.value.status_code==502


def test_long_dialogue_retains_recent_turns_within_model_budget(monkeypatch):
    captured={}
    def complete(self,task,payload):
        captured.update(payload)
        return json.dumps({'text':'调研客户','analysis':'精简表达','questions':'','source_chunk_ids':[]})
    monkeypatch.setattr(LLMProvider,'complete',complete)
    body=BlockDialogue(fact_ids=['f1','f2'],message='继续调整',history=[{'message':f'第 {i} 轮','text':'长'*10000} for i in range(12)])
    discuss_block(FACTS,body,'',[],{})
    assert len(captured['history'])<12
    assert captured['history'][-1]['message']=='第 11 轮'
    assert len(json.dumps(captured,ensure_ascii=False))<=55000
    assert len(body.history)==12


def test_company_and_date_on_separate_lines_stay_in_the_same_experience():
    texts=['实习经历','甲科技有限公司','2024.09 - 2025.06','与乙公司合作调研','乙科技有限公司','2025.07 - 2026.06','负责用户分析']
    facts=[{'id':f'f{i}','text':text,'section':'experience'} for i,text in enumerate(texts)]
    groups=group_blocks(facts,{})
    assert [group['fact_ids'] for group in groups]==[['f0','f1','f2','f3'],['f4','f5','f6']]


def test_education_module_merges_mixed_locks_without_unlocking_source_facts():
    facts=[{'id':'f0','text':'ŵ教育背景','section':'education','locked':True},
           {'id':'f1','text':'示例大学 硕士','section':'education','locked':True},
           {'id':'f2','text':'2026.09–2028.06','section':'education','locked':False},
           {'id':'f3','text':'专业：数据科学','section':'education','locked':False},
           {'id':'f4','text':'另一大学 本科','section':'education','locked':True}]
    result=group_blocks(facts,{})
    assert len(result)==1
    assert result[0]['fact_ids']==['f0','f1','f2','f3','f4']
    assert result[0]['locked'] is True
    assert facts[2]['locked'] is False
