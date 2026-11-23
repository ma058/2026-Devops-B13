"""Check the UUID false positive without weakening literal/history detection."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCANNERS = [ROOT / 'scripts/secret_scan.py',
            ROOT / 'labs/B-draft/scripts/secret_scan.py']


def load(path):
    spec = importlib.util.spec_from_file_location('scanner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecretScanTests(unittest.TestCase):
    def test_runtime_expression_and_diff_are_not_credentials(self):
        for path in SCANNERS:
            scan = load(path).scan_text
            for prefix in ('', '    ', '+    ', '-    '):
                with self.subTest(scanner=str(path), prefix=prefix):
                    self.assertEqual(scan(prefix + 'token = ' + 'uuid.uuid4().hex', 'source'), [])

    def test_literal_and_extended_values_remain_detected(self):
        for path in SCANNERS:
            scan = load(path).scan_text
            for value in ('"uuid.uuid4().hex"', "'uuid.uuid4().hex'",
                          'uuid.uuid4().hex_suffix', 'uuid.uuid4().hex + "suffix"',
                          'a' * 32, '"' + 'b' * 32 + '"'):
                with self.subTest(scanner=str(path), value=value):
                    self.assertTrue(scan('token = ' + value, 'source'))

    def test_other_secrets_on_same_line_are_not_hidden(self):
        samples = ['sk-' + 'A' * 24, 'ghp_' + 'B' * 32,
                   '-----BEGIN ' + 'OPENSSH PRIVATE KEY-----',
                   'api_key=' + 'c' * 32]
        for path in SCANNERS:
            for sample in samples:
                with self.subTest(scanner=str(path), sample=sample[:8]):
                    self.assertTrue(load(path).scan_text('token = ' + 'uuid.uuid4().hex # ' + sample, 'diff'))

    def test_dynamic_file_env_and_semicolon_assignments(self):
        samples = [
            "secret=" + "Path(config['token_file']).read_bytes().strip()",
            "token=" + "os.environ.get('E14_TOKEN','')",
            "token=" + "uuid.uuid4().hex; number=0",
            "envfile.write_text('E14_TOKEN=" + "'+token.read_text()+'\\n')",
        ]
        for path in SCANNERS:
            for sample in samples:
                for prefix in ('', '+    ', '-    '):
                    with self.subTest(scanner=str(path), sample=sample, prefix=prefix):
                        self.assertEqual(load(path).scan_text(prefix+sample, 'diff'), [])

    def test_dynamic_exemptions_do_not_hide_literals_or_suffixes(self):
        exprs = ["Path(config['token_file']).read_bytes().strip()",
                 "os.environ.get('E14_TOKEN','')"]
        for path in SCANNERS:
            scan = load(path).scan_text
            for expr in exprs:
                self.assertTrue(scan('secret = '+repr(expr), 'source'))
                self.assertTrue(scan('secret = '+expr+' + '+repr('z'*24), 'source'))
                self.assertTrue(scan('secret = '+expr+'; api_key='+repr('q'*24), 'source'))
            self.assertTrue(scan("envfile.write_text('E14_TOKEN="+'z'*24+"')", 'source'))

    def test_deleted_literal_is_detected_in_actual_git_history(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def git(*args):
                return subprocess.run(['git', '-C', td, *args], check=True,
                                      capture_output=True, text=True).stdout
            git('init', '-q')
            git('config', 'user.name', 'Scanner test')
            git('config', 'user.email', 'scanner-test@invalid.local')
            source = root / 'runtime.py'
            source.write_text('token = ' + '"' + 'd' * 32 + '"\n', encoding='utf-8')
            git('add', 'runtime.py')
            git('commit', '-qm', 'literal fixture')
            source.write_text('token = ' + 'uuid.uuid4().hex\n', encoding='utf-8')
            git('add', 'runtime.py')
            git('commit', '-qm', 'runtime expression')
            for path in SCANNERS:
                scanner = load(path)
                self.assertEqual(scanner.scan_text(source.read_text(), 'current'), [])
                hits = scanner.scan_text(git('log', '--all', '-p', '--no-color'), 'git-history')
                self.assertTrue(hits)
                self.assertTrue(all('d' * 32 not in hit for hit in hits))


if __name__ == '__main__':
    unittest.main()
