import json
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

@pytest.mark.parametrize('ids,text,approved', [(['f0'],'教育背景',['f0']),(['f1'],'提升 99%',['f1']),(['f1','f2'],'整理调研',['f1']),(['f1','f3'],'合并',['f1','f3'])])
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


def test_dialogue_rejects_fabricated_citations_and_numbers(monkeypatch):
    for response in [{'text':'提升 99%','analysis':'','questions':'','source_chunk_ids':[]},{'text':'调研','analysis':'','questions':'','source_chunk_ids':['fake:0']}]:
        monkeypatch.setattr(LLMProvider,'complete',lambda *args: json.dumps(response))
        with pytest.raises(HTTPException): discuss_block(FACTS,BlockDialogue(fact_ids=['f1','f2'],draft_text='调研',message='优化'),'',[],{})


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
        return json.dumps({'text':'甲公司 2025 年实习，调研 20 家客户。','analysis':'结合岗位要求明确调研行动','questions':'','source_chunk_ids':[]})
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
