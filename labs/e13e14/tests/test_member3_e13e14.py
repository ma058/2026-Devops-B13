import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrate import DEFAULT_PORTS, ROOT, container_path, execute, host_path, ports_from_env
import scan_runtime_logs


class PortParameterizationTests(unittest.TestCase):
    def test_defaults_keep_teaching_template_ports(self):
        self.assertEqual(ports_from_env({}), DEFAULT_PORTS)
        self.assertEqual(DEFAULT_PORTS, {
            'buildchecker': 18081, 'echecker': 18082, 'draft': 18083, 'mdfixer': 18084,
        })

    def test_member3_isolated_ports_via_env(self):
        env = {
            'E14_PORT_BUILDCHECKER': '18281',
            'E14_PORT_ECHECKER': '18282',
            'E14_PORT_DRAFT': '18283',
            'E14_PORT_MDFIXER': '18284',
        }
        self.assertEqual(ports_from_env(env), {
            'buildchecker': 18281, 'echecker': 18282, 'draft': 18283, 'mdfixer': 18284,
        })

    def test_partial_override_keeps_other_defaults(self):
        ports = ports_from_env({'E14_PORT_DRAFT': '19083'})
        self.assertEqual(ports['buildchecker'], 18081)
        self.assertEqual(ports['mdfixer'], 18084)

    def test_invalid_port_values_are_rejected(self):
        for bad in ('', 'nope', '80', '70000', '-1', '18081.0'):
            with self.assertRaises(ValueError):
                ports_from_env({'E14_PORT_DRAFT': bad})


class PathMappingTests(unittest.TestCase):
    def test_container_path_round_trip(self):
        here = Path(__file__).resolve()
        inner = container_path(here)
        self.assertTrue(inner.startswith('/course/'))
        self.assertEqual(host_path(inner), here)

    def test_host_path_rejects_escape_and_foreign_prefix(self):
        with self.assertRaises(ValueError):
            host_path('/course/../../../etc/passwd')
        with self.assertRaises(ValueError):
            host_path('/not-course/anything')

    def test_container_path_rejects_outside_repository(self):
        with self.assertRaises(ValueError):
            container_path(Path(tempfile.gettempdir()) / 'outside.txt')


class ScanRuntimeLogsTests(unittest.TestCase):
    # Fake credential values are assembled at runtime so that no
    # credential-shaped literal is ever committed to the shared repository.
    FAKE_KEY = 'sk-' + 'demo1234567890abcdefghijk'
    FAKE_TOKEN = 'ghp_' + 'abcdefghijklmnopqrstuvwxyz123456'

    def run_scan(self, *paths):
        argv = [str(p) for p in paths]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = scan_runtime_logs.main(argv)
        return code, out.getvalue()

    def test_fake_key_hits_then_clean_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / 'probe.log'
            # The probe line is assembled at runtime so the committed source
            # itself never contains a credential-shaped literal.
            probe.write_text('api' + '_key = "' + self.FAKE_KEY + '"\n', encoding='utf-8')
            code, out = self.run_scan(probe)
            self.assertEqual(code, 1)
            self.assertIn('FOUND', out)
            self.assertIn('***', out)
            self.assertNotIn(self.FAKE_KEY, out)
            probe.write_text('probe completed; clean content\n', encoding='utf-8')
            code, out = self.run_scan(probe)
            self.assertEqual(code, 0)
            self.assertIn('hits=0', out)

    def test_directory_scan_reports_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'run.log').write_text(
                'to' + 'ken = "' + self.FAKE_TOKEN + '"\n', encoding='utf-8')
            code, out = self.run_scan(root)
            self.assertEqual(code, 1)

    def test_missing_path_is_exit_two_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self.run_scan(Path(tmp) / 'does-not-exist')
            self.assertEqual(code, 2)

    def test_quoted_password_literals_with_code_punctuation_are_not_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / 'fake.log'
            for suffix in ('(alpha123456789', '[alpha123456789', '&alpha123456789'):
                value = 'synthetic' + suffix
                probe.write_text('pass' + 'word = "' + value + '"\n', encoding='utf-8')
                completed = subprocess.run(
                    [sys.executable, str(Path(scan_runtime_logs.__file__)), str(probe)],
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(completed.returncode, 1, completed.stdout)
                self.assertIn('FOUND', completed.stdout)
                self.assertNotIn(value, completed.stdout)

    def test_quoted_password_with_leading_ampersand_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / 'fake.log'
            value = '&' + 'syntheticAlpha123456789'
            probe.write_text('pass' + 'word = "' + value + '"\n', encoding='utf-8')
            code, output = self.run_scan(probe)
            self.assertEqual(code, 1)
            self.assertNotIn(value, output)


class ComposeTemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(__file__).resolve().parents[1] / 'compose.yaml').read_text(encoding='utf-8')

    def test_all_four_ports_are_parameterized_with_defaults(self):
        for role, default in DEFAULT_PORTS.items():
            self.assertIn(f'${{E14_PORT_{role.upper()}:-{default}}}', self.text)

    def test_ports_bind_loopback_only(self):
        self.assertEqual(self.text.count('"127.0.0.1:${E14_PORT'), 4)

    def test_only_draft_mounts_the_docker_socket(self):
        self.assertEqual(self.text.count('source: /var/run/docker.sock'), 1)

    def test_source_tree_is_read_only_for_every_role(self):
        self.assertEqual(self.text.count('read_only: true'), 4)

    def test_writable_area_is_limited_to_the_work_directory(self):
        self.assertEqual(self.text.count('target: /course/work'), 4)

    def test_container_identity_is_parameterized_to_owner(self):
        self.assertIn('user: "${E14_UID:-0}:${E14_GID:-0}"', self.text)
        self.assertIn('HOME: /tmp', self.text)

    def test_draft_joins_docker_socket_group(self):
        self.assertIn('"${E14_DOCKER_GID:-0}"', self.text)


class WorkflowEvidenceCollectionTests(unittest.TestCase):
    def setUp(self):
        repo = Path(__file__).resolve().parents[3]
        self.text = (repo / '.github' / 'workflows' / 'e13e14.yml').read_text(encoding='utf-8')

    def test_orchestrate_failure_is_captured_not_aborting_collection(self):
        # Collection is an independent always() step, before project cleanup.
        start = self.text.index('- name: Preserve service diagnostics')
        end = self.text.index('- name: Scan all captured runtime evidence')
        self.assertIn('if: always()', self.text[start:end])
        self.assertIn('ci-service-diagnostics/ps.log', self.text[start:end])
        self.assertIn('ci-service-diagnostics/services.log', self.text[start:end])
        self.assertLess(end, self.text.index('- name: Stop only this Compose project'))

    def test_failure_codes_are_propagated_at_the_end(self):
        self.assertIn('DIAGNOSTIC_CAPTURE_FINAL_EXIT', self.text)
        self.assertIn('exit "$FINAL_EXIT"', self.text)

    def test_real_shell_capture_errors_fail_without_docker_execution(self):
        # Exercise the exact workflow block with local shell functions instead
        # of Docker; collecting stderr alone must not convert failure to green.
        if os.name == 'nt':
            git = shutil.which('git')
            bash = Path(git).resolve().parents[1] / 'bin/bash.exe' if git else None
        else:
            bash = shutil.which('bash')
        if not bash or not Path(bash).is_file():
            self.skipTest('Bash required for workflow failure propagation check')
        lines = self.text.splitlines()
        start = next(i for i, line in enumerate(lines)
                     if '- name: Preserve service diagnostics' in line)
        start = next(i for i in range(start, len(lines)) if lines[i].strip() == 'run: |') + 1
        end = next(i for i in range(start, len(lines)) if lines[i].startswith('      - name:'))
        block = '\n'.join(line[10:] for line in lines[start:end])
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'capture.sh'
            script.write_text('''docker() {
  case "$*" in
    *" ps -a") return 7;;
    *" logs --no-color") return 8;;
    *) return 0;;
  esac
}
''' + block + '\n', encoding='utf-8', newline='\n')
            completed = subprocess.run([str(bash), '--noprofile', '--norc', str(script)],
                                       cwd=tmp, capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 8, completed.stdout + completed.stderr)
            self.assertEqual((Path(tmp) / 'work/ci-service-diagnostics/capture-status.txt')
                             .read_text().splitlines(), ['ps_exit=7', 'logs_exit=8'])

    def test_evidence_upload_always_runs(self):
        self.assertIn('if: always()', self.text)
        self.assertIn('retention-days: 14', self.text)

    def test_upload_keeps_hidden_files_but_excludes_secrets(self):
        self.assertIn('include-hidden-files: true', self.text)
        self.assertIn('!work/**/.git/**', self.text)
        self.assertIn('!work/**/.env', self.text)

    def test_source_scan_covers_workspace_and_history(self):
        self.assertIn('scripts/secret_scan.py . --history', self.text)

    def test_container_identity_is_exported_from_runner(self):
        self.assertIn('E14_UID=$(id -u)', self.text)
        self.assertIn('E14_DOCKER_GID=$(stat -c %g /var/run/docker.sock)', self.text)


class OrchestratorEvidenceTests(unittest.TestCase):
    def _work_path(self):
        out = ROOT / 'work' / ('e13e14-utest-' + uuid.uuid4().hex)
        self.addCleanup(self._remove, out)
        return out

    def _remove(self, path):
        if path.exists():
            for item in sorted(path.rglob('*'), reverse=True):
                if item.is_file():
                    item.unlink()
            path.rmdir()

    def test_existing_output_directory_is_rejected(self):
        out = self._work_path()
        out.mkdir(parents=True)
        request = {'repo': '/course/data/x', 'candidate': '/course/data/y'}
        with self.assertRaises(ValueError):
            execute(request, out)

    def test_inputs_outside_data_are_rejected_without_output_directory(self):
        out = self._work_path()
        request = {
            'repo': '/course/labs/e11e12',
            'candidate': '/course/labs/e11e12',
            'base': '0' * 40,
            'target': '1' * 40,
        }
        with self.assertRaises(ValueError):
            execute(request, out)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
