import yaml

from scripts.validate_knowledge import validate


def note(path, did, number):
    meta = {'id': did, 'title': '岗位', 'kind': 'jd', 'permission': 'public_display',
            'quality_status': 'source_verified', 'source_type': 'job_posting',
            'role_tags': ['gtm'], 'industry_tags': [], 'tags': [], 'source_note_id': number,
            'source_url': 'https://www.zhipin.com/job_detail/' + did + '.html',
            'source_author': '公司', 'excerpt': '岗位职责与范围'}
    path.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True) + '---\n# 岗位\n\n真实职责与任职要求。\n', encoding='utf-8')


def test_validator_reports_duplicate_number_and_wrong_category(tmp_path):
    note(tmp_path / 'a.md', 'job-a', 'J01')
    note(tmp_path / 'b.md', 'job-b', 'J01')
    result = validate(tmp_path)
    assert any('duplicate source_note_id' in error for error in result['errors'])
    note(tmp_path / 'b.md', 'job-b', 'I02')
    assert any('number prefix' in error for error in validate(tmp_path)['errors'])


def test_validator_accepts_number_gaps_and_rejects_token_urls(tmp_path):
    note(tmp_path / 'a.md', 'job-a', 'J01')
    note(tmp_path / 'b.md', 'job-b', 'J100')
    assert validate(tmp_path)['errors'] == []
    p = tmp_path / 'b.md'
    p.write_text(p.read_text(encoding='utf-8').replace('job-b.html', 'job-b.html?securityId=secret'), encoding='utf-8')
    assert any('session parameter' in error for error in validate(tmp_path)['errors'])
