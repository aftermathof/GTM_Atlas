import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zlib

import yaml

from batch_tools import scan_project, validate_batch


def note(source_id, number, author='示例博主'):
    meta = {
        'id': f'research-l{number:02d}', 'title': '示例业务复盘', 'kind': 'learning',
        'source_note_id': f'L{number:02d}', 'source_id': source_id,
        'source_url': 'https://www.xiaohongshu.com/explore/' + source_id,
        'source_author': author, 'source_type': 'original_research_note',
        'permission': 'public_display', 'quality_status': 'unverified',
        'role_tags': ['gtm'], 'industry_tags': [], 'tags': ['渠道'],
        'collected_at': '2026-10-27T10:00:00+08:00', 'displayed_date': None,
        'excerpt': '用独立语言概括业务问题和适用范围。', 'limitations': ['作者自述未独立核实。'],
        'content_notice': '独立研究整理，不是原帖逐字全文。',
    }
    return '---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n# 示例业务复盘\n\n## 内容概述\n\n按情境说明来源支持的判断。\n\n## 来源内容整理\n\n说明具体业务关系，不补造数据。\n\n## 阅读边界与核对说明\n\n作者自述未独立核实。\n'


def png():
    def chunk(tag, data):
        return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b'')


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'atlas'
        self.library = self.project / 'knowledge/learning/research-notes'
        self.library.mkdir(parents=True)
        self.original = self.library / 'research-l07.md'
        self.original.write_text(note('a' * 24, 7), encoding='utf-8')
        self.batch = self.root / 'batch'
        (self.batch / 'notes').mkdir(parents=True)
        (self.batch / 'assets').mkdir()
        image = self.batch / 'assets/pixel.png'
        image.write_bytes(png())
        body = note('b' * 24, 8) + '\n![新增结构图](/xhs-author-assets/pixel.png)\n'
        (self.batch / 'notes/research-l08.md').write_text(body, encoding='utf-8')
        self.manifest = {
            'author': '示例博主', 'asset_url_prefix': '/xhs-author-assets/',
            'posts': [{'source_id': 'b' * 24, 'title': '示例业务复盘',
                       'source_url': 'https://www.xiaohongshu.com/explore/' + 'b' * 24,
                       'status': 'staged', 'source_note_id': 'L08',
                       'note_file': 'notes/research-l08.md',
                       'images': [{'index': 1, 'decision': 'keep', 'reason': '展示正文没有的字段关系。',
                                   'file': 'assets/pixel.png', 'sha256': hashlib.sha256(png()).hexdigest()}]}],
        }
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self):
        (self.batch / 'manifest.json').write_text(json.dumps(self.manifest, ensure_ascii=False), encoding='utf-8')

    def test_scan_accounts_for_deleted_and_reserved_numbers(self):
        reserved = self.root / 'reserved.json'
        reserved.write_text(json.dumps({'posts': [{'source_note_id': 'L102'}]}))
        result = scan_project(self.project, 'L', reserved=reserved, history_text='-source_note_id: L99\n')
        self.assertEqual(result['next_number'], 'L103')
        self.assertEqual(result['existing_xhs_ids'], ['a' * 24])

    def test_scan_uses_last_id_without_emitting_session_parameters(self):
        text = self.original.read_text(encoding='utf-8').replace('source_id: ' + 'a' * 24 + '\n', '')
        text = text.replace('https://www.xiaohongshu.com/explore/' + 'a' * 24,
                            'https://www.xiaohongshu.com/user/profile/' + 'c' * 24 + '/' + 'a' * 24 + '?xsec_token=SECRET')
        self.original.write_text(text, encoding='utf-8')
        result = scan_project(self.project)
        self.assertEqual(result['existing_xhs_ids'], ['a' * 24])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_plain_markdown_inside_knowledge_is_reported(self):
        file = self.project / 'knowledge/site/book/source.md'
        file.parent.mkdir(parents=True)
        file.write_text('# 无 frontmatter 的网页原始稿')
        self.assertTrue(scan_project(self.project)['errors'])

    def test_valid_batch(self):
        result = validate_batch(self.batch, self.project)
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['complete'])
        self.assertEqual(result['notes'], 1)
        self.assertEqual(result['image_references'], 1)

    def test_token_and_existing_source_are_rejected(self):
        self.manifest['posts'][0]['source_id'] = 'a' * 24
        self.manifest['posts'][0]['source_url'] += '?xsec_token=SECRET'
        self.write_manifest()
        result = validate_batch(self.batch, self.project)
        self.assertTrue(result['errors'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_unsafe_asset_and_wrong_checksum_are_rejected(self):
        image = self.manifest['posts'][0]['images'][0]
        image['sha256'] = '0' * 64
        self.write_manifest()
        self.assertTrue(validate_batch(self.batch)['errors'])
        image['file'] = '../outside.png'
        self.write_manifest()
        self.assertTrue(validate_batch(self.batch)['errors'])

    def test_dropped_image_cannot_be_published(self):
        self.manifest['posts'][0]['images'][0]['decision'] = 'duplicate'
        self.write_manifest()
        self.assertTrue(validate_batch(self.batch)['errors'])

    def test_partial_result_is_never_called_complete(self):
        self.manifest['posts'].append({'source_id': 'c' * 24, 'source_url': 'https://www.xiaohongshu.com/explore/' + 'c' * 24,
                                       'title': '尚未读取', 'status': 'pending', 'images': []})
        self.write_manifest()
        result = validate_batch(self.batch, self.project)
        self.assertEqual(result['errors'], [])
        self.assertFalse(result['complete'])

    def test_published_mode_requires_exact_copies(self):
        target = self.library / 'research-l08.md'
        shutil.copyfile(self.batch / 'notes/research-l08.md', target)
        self.assertTrue(validate_batch(self.batch, self.project)['errors'])
        assets = self.project / 'knowledge/site/xhs-author-assets'
        assets.mkdir(parents=True)
        shutil.copyfile(self.batch / 'assets/pixel.png', assets / 'pixel.png')
        self.assertEqual(validate_batch(self.batch, self.project, published=True)['errors'], [])
        target.write_text(target.read_text(encoding='utf-8') + '\n修改过', encoding='utf-8')
        self.assertTrue(validate_batch(self.batch, self.project, published=True)['errors'])

    def test_changed_original_is_detected(self):
        snapshot = self.batch / 'project-scan.json'
        snapshot.write_text(json.dumps(scan_project(self.project)), encoding='utf-8')
        self.manifest['snapshot_file'] = 'project-scan.json'
        self.write_manifest()
        self.original.write_text(self.original.read_text(encoding='utf-8') + '\n变化', encoding='utf-8')
        self.assertTrue(validate_batch(self.batch, self.project)['errors'])

    def test_inventory_must_be_accounted_for(self):
        self.manifest['inventory_file'] = 'inventory.json'
        (self.batch / 'inventory.json').write_text(json.dumps([{'id': 'b' * 24}, {'id': 'c' * 24}]))
        self.write_manifest()
        self.assertTrue(validate_batch(self.batch)['errors'])

    def test_published_mode_checks_asset_copy(self):
        shutil.copyfile(self.batch / 'notes/research-l08.md', self.library / 'research-l08.md')
        self.assertTrue(validate_batch(self.batch, self.project, published=True)['errors'])
        assets = self.project / 'knowledge/site/xhs-author-assets'
        assets.mkdir(parents=True)
        (assets / 'pixel.png').write_bytes(b'wrong image')
        self.assertTrue(validate_batch(self.batch, self.project, published=True)['errors'])

    def test_unknown_kind_is_reported_without_crashing(self):
        self.original.write_text(self.original.read_text(encoding='utf-8').replace('kind: learning', 'kind: other'), encoding='utf-8')
        self.assertTrue(scan_project(self.project)['errors'])

    def test_other_platform_id_is_not_xhs_duplicate(self):
        self.original.write_text(self.original.read_text(encoding='utf-8').replace('https://www.xiaohongshu.com/explore/', 'https://example.org/'), encoding='utf-8')
        self.assertEqual(scan_project(self.project)['existing_xhs_ids'], [])


if __name__ == '__main__':
    unittest.main()
