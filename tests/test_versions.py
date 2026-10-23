from tests.test_workflows import client, login


def test_version_rollback_and_artifacts_remain_private(client):
    a, b = login(client), login(client, 'other')
    original = "姓名：示例同学\n教育：示例大学 本科\n经历：负责培训资料整理\n技能：Excel，英语"
    rid = client.post('/api/v1/career/resumes', files={'file': ('r.txt', original.encode(), 'text/plain')}, headers=a).json()['id']
    session = client.post('/api/v1/career/sessions', json={'resume_id': rid}, headers=a).json()
    sid = session['id']
    client.post(f'/api/v1/career/sessions/{sid}/confirm-facts', json={'facts': session['facts']}, headers=a)
    v1 = client.post(f'/api/v1/career/sessions/{sid}/approve-rewrite', json={'patches': [{'fact_id':'f2','text':'负责整理培训资料。'}], 'approved_fact_ids':['f2']}, headers=a).json()
    v2 = client.post(f'/api/v1/career/sessions/{sid}/approve-rewrite', json={'patches': [{'fact_id':'f3','text':'技能：Excel；英语。'}], 'approved_fact_ids':['f3'], 'base_version_id':v1['id']}, headers=a).json()
    assert v2['facts'][1] == session['facts'][1]
    assert client.get(f'/api/v1/career/versions/{v1["id"]}/download/tex', headers=a).status_code == 200
    assert client.get(f'/api/v1/career/versions/{v1["id"]}/download/tex', headers=b).status_code == 404
    assert client.get(f'/api/v1/career/versions/{v1["id"]}/download/pdf', headers=a).status_code == 409
    rollback = client.post(f'/api/v1/career/sessions/{sid}/rollback', json={'version_id':v1['id']}, headers=a).json()
    assert rollback['active_version_id'] == v1['id']
    assert len(client.get(f'/api/v1/career/sessions/{sid}/versions',headers=a).json()) == 2


def test_custom_role_keeps_original_name(client):
    a = login(client)
    r = client.post('/api/v1/mock/sessions', json={'role':'custom', 'role_raw':'QB / QC 原始岗位', 'count':3}, headers=a)
    assert r.status_code == 200
    assert r.json()['context']['role_raw'] == 'QB / QC 原始岗位'
