"""Runtime scan/export regressions, including the runner's real failure trap."""
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'labs/e13e14'))
import member2_evidence as evidence
import member2_export as exporter


class SharedEvidence(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.run = self.root / 'work/run'
        self.run.mkdir(parents=True)
        self.diag = self.run / 'diagnostics'
        self.diag.mkdir()
        (self.diag / 'draft.log').write_text('clean diagnostic\n')
        self.log = self.run / 'jobs/job-12345678/draft/iter-02/build-stderr.log'
        self.log.parent.mkdir(parents=True)
        self.log.write_text('clean build\n')
        self.fake = 'sk-' + 'Q' * 28

    def scan(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = evidence.scan_evidence(self.run)
        self.assertNotIn(self.fake, stream.getvalue())
        return code, stream.getvalue()

    def test_nested_job_log_blocks_clean_diagnostics_then_cleanup_passes(self):
        self.log.write_text(self.fake + '\n')
        self.assertEqual(self.scan()[0], 1)
        self.assertEqual(self.log.read_text(), self.fake + '\n')
        self.log.write_text('clean build\n')
        self.assertEqual(self.scan()[0], 0)

    def test_only_named_private_inputs_are_excluded(self):
        for name in evidence.PRIVATE_FILES:
            (self.run / name).write_text(self.fake)
        self.assertEqual(self.scan()[0], 0)
        nested_private_name = self.log.parent / 'token.secret'
        nested_private_name.write_text(self.fake)
        self.assertEqual(self.scan()[0], 1)
        nested_private_name.unlink()
        (self.run / 'unexpected.env').write_text(self.fake)
        self.assertEqual(self.scan()[0], 1)

    def test_empty_scan_report_and_private_inputs_are_not_evidence(self):
        for f in (self.log, self.diag / 'draft.log'):
            f.unlink()
        (self.run / 'diagnostics-scan.log').write_text('')
        (self.run / 'token.secret').write_text(self.fake)
        self.assertEqual(self.scan()[0], 2)

    def test_unreadable_evidence_is_incomplete_not_clean(self):
        original = Path.open
        def open_file(path, *args, **kwargs):
            if path == self.log:
                raise OSError('simulated read failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', open_file), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.scan()[0], 2)

    def test_export_does_not_archive_detected_secret_from_failed_run(self):
        (self.diag / 'client.exit.txt').write_text('1\n')
        self.log.write_text(self.fake + '\n')
        private = self.run / 'token.secret'
        private.write_text('different-private-runtime-credential')
        config = self.run / 'config.json'
        config.write_text(json.dumps({'run_relative': 'work/run', 'token_file': str(private)}))
        destination = self.root / 'export'
        with patch.object(exporter, 'ROOT', self.root), \
             patch.object(sys, 'argv', ['exporter', '--config', str(config), '--out', str(destination)]), \
             contextlib.redirect_stdout(io.StringIO()), patch.object(exporter.subprocess, 'run') as git:
            with self.assertRaisesRegex(ValueError, 'EVIDENCE_SCAN_REJECTED'):
                exporter.main()
        git.assert_not_called()
        self.assertFalse(destination.exists())
        self.assertEqual(self.log.read_text(), self.fake + '\n')
        self.assertEqual((self.diag / 'client.exit.txt').read_text(), '1\n')

    def test_real_failure_trap_scans_nested_jobs_and_keeps_original_failure(self):
        git = shutil.which('git')
        bash = (Path(git).resolve().parents[1] / 'bin/bash.exe' if git else None) if os.name == 'nt' else shutil.which('bash')
        if not bash or not Path(bash).is_file():
            self.skipTest('Bash required for actual finish-trap check')
        self.log.write_text(self.fake + '\n')
        runner = (ROOT / 'labs/e13e14/run_shared_member2.sh').read_text()
        function = runner[runner.index('finish() {'):runner.index('\ntrap finish EXIT')]
        q = lambda value: shlex.quote(str(value).replace('\\', '/'))
        script = self.root / 'failure.sh'
        script.write_text(
            'set -euo pipefail\n' +
            'M2_E14_RUN=' + q(self.run) + '\ndiag=' + q(self.diag) + '\nmode=normal\ntouched=0\n' +
            'python3() { ' + q(sys.executable) + ' "$@"; }\n' +
            function + '\ntrap finish EXIT\nexit 7\n', encoding='utf-8', newline='\n')
        result = subprocess.run([str(bash), '--noprofile', '--norc', str(script)], cwd=ROOT,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('CLIENT_EXIT=7', result.stdout)
        self.assertIn('DIAGNOSTIC_SCAN_EXIT=1', result.stdout)
        self.assertEqual((self.diag / 'client.exit.txt').read_text().strip(), '7')
        self.assertIn('hits=1', (self.run / 'diagnostics-scan.log').read_text())
        self.assertEqual(self.log.read_text(), self.fake + '\n')


if __name__ == '__main__':
    unittest.main()
