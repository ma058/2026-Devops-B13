"""Member 1: cross-platform API artifact paths and Windows UTF-8 requests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'course' / 'e11-e12' / 'api_probe.py'
SPEC = importlib.util.spec_from_file_location('member1_e11e12_api_probe', SCRIPT)
api_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api_probe)


class ApiClientBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.downloads = self.root / 'downloads'
        self.downloads.mkdir()

    def assert_rejected(self, paths):
        before = list(self.downloads.iterdir())
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ValueError):
                api_probe.safe_download_target(self.downloads, path)
        self.assertEqual(before, list(self.downloads.iterdir()))

    def link(self, target, link, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest('Host does not permit symlink creation: ' + str(error))

    def test_accepts_normal_nested_and_chinese_paths_without_writing(self):
        self.assertEqual(
            api_probe.safe_download_target(self.downloads, '阶段/修复补丁.diff'),
            self.downloads / '阶段' / '修复补丁.diff')
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_rejects_posix_absolute_paths(self):
        self.assert_rejected(['/tmp/outside.json', '//server/share/file'])

    def test_rejects_windows_drive_unc_and_backslash_paths_on_all_hosts(self):
        self.assert_rejected(['C:/tmp/file', 'C:relative.json', r'C:\tmp\file',
                              r'\\server\share\file', r'..\outside.json',
                              r'nested\file.json', 'file.json:stream'])

    def test_rejects_parent_traversal(self):
        self.assert_rejected(['../outside', 'nested/../../outside', 'nested/../file'])

    def test_rejects_empty_ambiguous_and_git_paths(self):
        self.assert_rejected(['', '.', './file', 'nested//file', 'nested/',
                              '.git/config', 'nested/.git/HEAD', 'bad\x00name'])

    def test_rejects_existing_symlink_leaf_and_preserves_outside_bytes(self):
        outside = self.root / 'outside.json'
        outside.write_bytes(b'original')
        self.link(outside, self.downloads / 'report.json')
        self.assert_rejected(['report.json'])
        self.assertEqual(outside.read_bytes(), b'original')

    def test_rejects_symlink_directory_even_when_it_points_inside_root(self):
        real = self.downloads / 'real'
        real.mkdir()
        self.link(real, self.downloads / 'alias', directory=True)
        self.assert_rejected(['alias/new.json'])
        self.assertFalse((real / 'new.json').exists())

    def test_rejects_symlink_download_root(self):
        alias = self.root / 'alias'
        self.link(self.downloads, alias, directory=True)
        with self.assertRaises(ValueError):
            api_probe.safe_download_target(alias, 'new.json')
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_reads_utf8_bom_and_plain_chinese_json_without_changing_bytes(self):
        for bom in (b'', b'\xef\xbb\xbf'):
            with self.subTest(bom=bool(bom)):
                request = self.root / 'request.json'
                raw = bom + '{"expected_output":"测试"}'.encode('utf-8')
                request.write_bytes(raw)
                self.assertEqual(api_probe.read_request(request), {'expected_output': '测试'})
                self.assertEqual(request.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
