from packages.career.text import clean_resume_text
from packages.career.graph import parse_resume
import pytest
import pymupdf


def test_resume_text_removes_bullets_and_decorative_icons_only():
    assert clean_resume_text('• 提升 20%')=='提升 20%'
    assert clean_resume_text('\ue123📞 13800000000')=='13800000000'
    assert clean_resume_text('2024–2025 -5% a@example.com')=='2024–2025 -5% a@example.com'


def test_parse_skips_icon_only_lines_and_keeps_fact_ids_contiguous(tmp_path):
    path=tmp_path/'resume.txt'
    path.write_text('张同学\n\ue001\n• 调研 20 家企业\n📧 a@example.com',encoding='utf-8')
    result=parse_resume(path.read_bytes(),path.name)
    assert [f['text'] for f in result['facts']]==['张同学','调研 20 家企业','a@example.com']
    assert [f['id'] for f in result['facts']]==['f0','f1','f2']


def test_misdecoded_heading_icons_are_removed_but_names_are_preserved():
    assert clean_resume_text('ŵ教育背景\nǼ 实习经历\nǼvar Andersen')=='教育背景\n实习经历\nǼvar Andersen'


def test_mixed_heading_glyphs_and_bullets_are_cleaned_without_removing_real_letters():
    assert clean_resume_text('• ϻ教育背景\nϻ • 实习经历\nϻ\nϻvar Andersen\nμ = 20\nϻ = 3') == '教育背景\n实习经历\n\nϻvar Andersen\nμ = 20\nϻ = 3'


@pytest.mark.parametrize('prefix', ['ˌ ', 'ë ', 'Ӝ ', '¤ ', '• ë ', 'ˌ\të ', '\ufffd '])
@pytest.mark.parametrize('heading', ['项目经历', '实习经历', '教育背景', '工作经历', '技能特长'])
def test_decorative_heading_prefixes_do_not_need_a_character_allowlist(prefix, heading):
    assert clean_resume_text(prefix + heading) == heading


def test_cleaner_preserves_names_foreign_languages_and_scientific_notation():
    text = 'Zoë Müller\në 是荷兰语变音字母\nˌ 是音标\nμ = 20\nGTM 项目经历\nC++ / C# / R&D\n-5% ± 2%\n•ë 实习经历：'
    assert clean_resume_text(text) == text.replace('•ë 实习经历：', '实习经历：')


def test_unreadable_body_characters_are_marked_instead_of_silently_deleted():
    result = parse_resume('姓名：张\ufffd\n项目经历：整理客户需求并完成报告，结果需要核对。'.encode('utf-8'), 'resume.txt')
    assert result['facts'][0]['text'] == '姓名：张[待确认]'
    assert result['facts'][0]['confidence'] < 0.9
    assert result['facts'][1]['confidence'] == 1
    assert '待确认' in result['warning']


def test_pdf_icon_font_is_removed_at_extraction_even_when_it_maps_to_ascii():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 70), 'n', fontname='ZapfDingbats')
        page.insert_text((75, 70), 'Project Experience', fontname='helv')
        page.insert_text((50, 100), 'Research and customer interviews, completed a report.', fontname='helv')
        content = doc.tobytes()
    result = parse_resume(content, 'resume.pdf')
    assert result['method'] == 'pdf-text'
    assert [f['text'] for f in result['facts']] == ['Project Experience', 'Research and customer interviews, completed a report.']


def test_pdf_normal_text_is_preserved_across_font_changes():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 70), 'Zoë Müller - Research Analyst', fontname='helv')
        page.insert_text((50, 100), 'Education and Project Experience', fontname='hebo')
        content = doc.tobytes()
    result = parse_resume(content, 'resume.pdf')
    assert [f['text'] for f in result['facts']] == ['Zoë Müller - Research Analyst', 'Education and Project Experience']


def test_scan_transcription_cleans_headings_and_requests_no_icon_transcription(monkeypatch):
    captured = {}
    for key in ['BASE_URL','API_KEY','MODEL']:
        monkeypatch.setenv('VISION_'+key, 'offline-test')
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'choices':[{'message':{'content':'ˌ 项目经历\n完成调研并整理需求表\në 实习经历\n协助整理客户信息'}}]}
    def post(*args, **kwargs):
        captured.update(kwargs['json'])
        return Response()
    monkeypatch.setattr('packages.career.graph.httpx.post', post)
    result = parse_resume(b'\x89PNG', 'scan.png')
    assert result['method'] == 'vision-ocr'
    assert result['facts'][0]['text'] == '项目经历'
    assert result['facts'][2]['text'] == '实习经历'
    assert all(f['confidence'] < 0.9 for f in result['facts'])
    assert '忽略图标' in captured['messages'][0]['content'][0]['text']
