import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from packages.rag.import_notes import import_notes
from packages.career.structure import extract_structure
from packages.document_renderer.render import render_tex
from packages.agent_core.providers import LLMProvider
from tests.test_workflows import client, login


def test_import_notes_preserves_body_and_does_not_invent_jds(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    body = '# 研究笔记\n\n完整内容。\n## 阅读边界\n非官方招聘标准。\n'
    (source/'note.md').write_text(body,encoding='utf-8')
    (source/'知识库.json').write_text(json.dumps({'collected_at':'2026-10-22','content_type':'original_research_notes','notes':[{'id':'I01','title':'面试研究','category':'实习校招面经','file':'note.md','source_url':'https://example.com/source','author':'作者','overview':'研究摘要','tags':['GTM']}]},ensure_ascii=False),encoding='utf-8')
    destination = tmp_path/'knowledge'
    report = import_notes(source,destination)
    assert report['interview'] == 1 and report['jd'] == 0
    target = next(destination.rglob('*.md')).read_text(encoding='utf-8')
    assert target.split('---',2)[2].lstrip('\n') == body
    assert 'original_research_note' in target and 'https://example.com/source' in target
    import_notes(source,destination)
    assert len(list(destination.rglob('*.md'))) == 1


def sample_facts():
    return [{'id':f'f{i}','text':t,'locked':i==2,'page':1,'confidence':1} for i,t in enumerate(['姓名：张同学','邮箱：zhang@example.com','教育背景：示例大学 本科','项目经历：负责用户调研和AI知识库整理','实习经历：协作整理培训材料','技能：Excel与英语'])]


def test_structure_covers_every_fact_and_template_uses_user_design():
    facts = sample_facts()
    structure = extract_structure(facts)
    assert structure['profile']['name']['value'] == '张同学'
    assert structure['assignments']['f3'] == 'projects'
    assert set(structure['assignments']) == {f['id'] for f in facts}
    tex = render_tex('test-user-template',facts,'gtm-original',structure)
    assert r'\definecolor{primary}{RGB}{85,36,139}' in tex
    assert '张同学' in tex and '用户调研' in tex and '示例大学' in tex
    assert '学校名称' not in tex and 'email@example.com' not in tex


def test_structure_rejects_invented_profile_and_missing_facts(monkeypatch):
    monkeypatch.setattr(LLMProvider,'complete',lambda *args: json.dumps({'profile':{'name':{'value':'虚构姓名','source_fact_ids':['f0']}},'assignments':{'f0':'personal'}}))
    with pytest.raises(HTTPException):
        extract_structure(sample_facts())


def test_uploaded_jd_is_private_and_attached_to_career(client):
    a,b=login(client),login(client,'other')
    jd=client.post('/api/v1/career/job-descriptions',files={'file':('target.md','海外GTM实习生\n职责：用户调研、上市策划、渠道分析。'.encode(),'text/markdown')},headers=a)
    assert jd.status_code==200,jd.text
    jid=jd.json()['id']
    assert client.get('/api/v1/knowledge/documents/'+jid,headers=b).status_code==404
    assert client.get('/api/v1/knowledge/documents/'+jid).status_code==404
    assert any(d['id']==jid for d in client.get('/api/v1/knowledge/documents?kind=jd',headers=a).json()['items'])
    reply=client.post('/api/v1/ai/chat',json={'scope':'article','document_id':jid,'message':'这份JD的岗位职责是什么？'},headers=a)
    assert reply.status_code==200 and reply.json()['citations'][0]['permission']=='private'
    assert client.post('/api/v1/ai/chat',json={'scope':'article','document_id':jid,'message':'岗位职责是什么'},headers=b).status_code==404
    assert not any(r['doc_id']==jid for r in client.post('/api/v1/knowledge/search',json={'query':'用户调研'}).json()['items'])
    rid=client.post('/api/v1/career/resumes',files={'file':('r.txt','姓名：张同学\n教育背景：示例大学 本科\n项目经历：参与用户调研和培训资料整理。'.encode(),'text/plain')},headers=a).json()['id']
    session=client.post('/api/v1/career/sessions',json={'resume_id':rid,'jd_id':jid,'role':'gtm'},headers=a)
    assert session.status_code==200,session.text
    assert '渠道分析' in session.json()['context']['jd']
    assert session.json()['structure']['assignments']


def test_rewrite_receives_jd_and_retrieved_evidence(client,monkeypatch):
    a=login(client)
    rid=client.post('/api/v1/career/resumes',files={'file':('r.txt','姓名：张同学\n教育：示例大学\n项目：负责用户调研和培训资料整理'.encode(),'text/plain')},headers=a).json()['id']
    session=client.post('/api/v1/career/sessions',json={'resume_id':rid,'role':'gtm','jd':'目标岗位要求市场调研与渠道分析'},headers=a).json()
    client.post(f'/api/v1/career/sessions/{session["id"]}/confirm-facts',json={'facts':session['facts']},headers=a)
    captured={}
    def response(self,task,payload):
        captured.update(payload)
        return json.dumps({'patches':[{'fact_id':'f2','text':'项目：负责用户调研与培训资料整理。'}]})
    monkeypatch.setattr(LLMProvider,'complete',response)
    r=client.post(f'/api/v1/career/sessions/{session["id"]}/suggest-rewrite',json={'approved_fact_ids':['f2']},headers=a)
    assert r.status_code==200,r.text
    assert captured['evidence'] and '市场调研' in captured['jd']
    assert captured['focus_sections']==['projects','experience']
    assert r.json()['citations']
    assert not any(c.get('demo') for c in r.json()['citations'])
