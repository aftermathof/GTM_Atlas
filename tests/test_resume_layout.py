import pytest
from packages.document_renderer import render
from packages.document_renderer.layout import build_layout
from packages.career.structure import local_structure, editable_facts
from tests.test_workflows import client


def facts_for_layout():
    rows = [
        ("personal", "个人信息"), ("personal", "姓名：示例同学"),
        ("education", "教育背景"), ("education", "2022.09–2026.06"),
        ("education", "示例大学 本科"), ("education", "专业：市场营销"),
        ("projects", "ˌ 项目经历"), ("experience", "实习经历"),
        ("experience", "甲公司 GTM实习生 2025.03–2025.08"),
        ("experience", "工作内容：开展渠道调研。\n整理竞品定位，形成市场分析表。"),
        ("experience", "乙公司 运营实习生 2024.07–2024.12"),
        ("experience", "维护客户资料，支持活动执行。"),
        ("skills", "技能特长"),
        ("skills", "办公工具：Excel、PowerPoint；语言能力：英语写作；AI工具：ChatGPT、Claude"),
        ("summary", "自我评价"),
    ]
    return [{"id": f"f{i}", "text": text, "section": section} for i, (section, text) in enumerate(rows)]


def test_layout_separates_headers_and_items_without_duplicate_section_titles():
    facts = facts_for_layout()
    layout = build_layout(facts, local_structure(facts))
    assert layout["personal"] == ["姓名：示例同学"]
    assert layout["education"][0]["organization"] == "示例大学 本科"
    assert layout["education"][0]["date"] == "2022.09–2026.06"
    assert len(layout["experience"]) == 2
    first = layout["experience"][0]
    assert first["organization"] == "甲公司"
    assert first["role"] == "GTM实习生"
    assert first["date"] == "2025.03–2025.08"
    assert len(first["items"]) == 2
    assert len(layout["skills"]) == 3
    assert not layout["projects"] and not layout["summary"]


@pytest.mark.parametrize("template", ["gtm-original", "classic-cn", "classic-en", "modern-onepage"])
def test_templates_keep_entry_headers_outside_bullets_and_render_each_skill(monkeypatch, tmp_path, template):
    monkeypatch.setattr(render, "data_dir", lambda: tmp_path)
    facts = facts_for_layout()
    source = render.render_tex("layout-"+template, facts, template)
    assert source.count("教育背景") == 1
    assert source.count("实习与工作经历") == 1
    assert r"\resumeentry{甲公司}{GTM实习生}{2025.03–2025.08}" in source
    assert r"\resumeentry{示例大学 本科}{}{2022.09–2026.06}" in source
    assert r"\item 甲公司" not in source
    assert r"\item 办公工具：" in source
    assert r"\item 语言能力：" in source
    assert r"\item AI工具：" in source
    assert "\n项目经历\n" not in source


def test_missing_and_heading_only_sections_remain_blank_and_editable():
    facts = facts_for_layout()
    result = editable_facts(facts, local_structure(facts))
    assert next(f for f in result if f["id"] == "f6")["text"] == ""
    assert next(f for f in result if f["section"] == "summary")["text"] == ""
    missing = editable_facts([{"id":"f0","text":"姓名：示例同学","section":"personal"}])
    assert {f["section"] for f in missing if not f["text"]} == {"projects", "summary"}
    assert len({f["id"] for f in missing}) == len(missing)
    assert editable_facts(missing) == missing
    assert facts[6]["text"] == "ˌ 项目经历"


def test_blank_sections_can_be_confirmed_and_filled_without_new_source_facts(client):
    from tests.test_workflows import login
    auth = login(client)
    resume = client.post('/api/v1/career/resumes', files={'file': ('sample.txt', '姓名：示例同学\n教育背景：示例大学 本科\n工作经历：负责整理客户资料'.encode(), 'text/plain')}, headers=auth).json()
    session = client.post('/api/v1/career/sessions', json={'resume_id': resume['id']}, headers=auth).json()
    empty = {f['section']: f for f in session['facts'] if f['text'] == ''}
    assert set(empty) == {'projects', 'summary'}
    sid = session['id']
    confirmed = client.post(f'/api/v1/career/sessions/{sid}/confirm-facts', json={'facts': session['facts']}, headers=auth)
    assert confirmed.status_code == 200, confirmed.text
    blocks = client.get(f'/api/v1/career/sessions/{sid}/editing-blocks', headers=auth).json()['blocks']
    assert any(b['fact_ids'] == [empty['projects']['id']] for b in blocks)
    new = client.post(f'/api/v1/career/sessions/{sid}/approve-rewrite', json={'blocks': [{'fact_ids': [empty['projects']['id']], 'text': 'GTM项目\n完成竞品定位分析。'}], 'approved_fact_ids': [empty['projects']['id']]}, headers=auth)
    assert new.status_code == 200, new.text
    assert any('竞品定位' in f['text'] for f in new.json()['facts'])
    assert any(f['section']=='summary' and f['text']=='' for f in new.json()['facts'])


def test_organization_without_company_suffix_and_labeled_work_content_stay_in_one_entry():
    facts = [
        {'id':'f0','section':'experience','text':'示例资本 | 私募股权实习生'},
        {'id':'f1','section':'experience','text':'2024.03–2024.06'},
        {'id':'f2','section':'experience','text':'公司研究：针对目标企业开展研究，形成分析报告。'},
        {'id':'f3','section':'experience','text':'行业研究：整理可比公司估值。'},
    ]
    layout=build_layout(facts,local_structure(facts))
    assert len(layout['experience'])==1
    entry=layout['experience'][0]
    assert entry['organization']=='示例资本'
    assert entry['role']=='私募股权实习生'
    assert len(entry['items'])==2
    assert entry['items'][0].startswith('公司研究：')
    from services.api.resume_blocks import group_blocks
    assert len(group_blocks(facts,local_structure(facts)))==1


def test_wrapped_source_lines_are_joined_inside_the_same_work_bullet():
    rows=['甲公司 | GTM实习生 2025.03–2025.08','流程优化：梳理用户需','求，建立标准化流程。','线上运营：监测用户','体验；完成测试与反馈。']
    facts=[{'id':f'f{i}','section':'experience','text':text} for i,text in enumerate(rows)]
    entry=build_layout(facts,local_structure(facts))['experience'][0]
    assert entry['items']==['流程优化：梳理用户需求，建立标准化流程。','线上运营：监测用户体验；完成测试与反馈。']
