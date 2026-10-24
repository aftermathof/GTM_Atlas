from packages.career.text import clean_resume_text
from packages.career.graph import parse_resume


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
