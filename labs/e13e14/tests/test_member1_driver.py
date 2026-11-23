"""Portable artifact-verifier tests; these do not claim Linux experiment runs."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import member1_run as driver
from member1_run import cleanup_server_group, verify_c8_downloads, verify_manifest


class Member1EvidenceVerifierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.file = self.root / '.gitignore'
        self.file.write_bytes(b'*.o\napp\n')
        self.reference = {'uri': 'artifact://job-test/.gitignore',
                          'bytes': self.file.stat().st_size,
                          'sha256': hashlib.sha256(self.file.read_bytes()).hexdigest()}

    def result(self, refs=None):
        return {'job_id': 'job-test', 'artifacts': refs if refs is not None else [self.reference]}

    def test_legal_hidden_file_is_verified_not_silently_skipped(self):
        verified = verify_manifest(self.result(), self.root)
        self.assertEqual(verified, [{'path': '.gitignore', 'bytes': self.reference['bytes'],
                                    'sha256': self.reference['sha256']}])

    def test_tampered_download_is_rejected(self):
        self.file.write_bytes(b'*.x\napp\n')
        with self.assertRaisesRegex(AssertionError, 'hash mismatch'):
            verify_manifest(self.result(), self.root)

    def test_foreign_and_duplicate_artifacts_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Foreign'):
            verify_manifest(self.result([dict(self.reference, uri='artifact://job-other/.gitignore')]), self.root)
        with self.assertRaisesRegex(AssertionError, 'Duplicate'):
            verify_manifest(self.result([self.reference, self.reference]), self.root)

    def test_unsafe_relative_path_is_rejected_before_file_access(self):
        for suffix in ('../.gitignore', '.git/config', 'C:/outside', r'folder\escape'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                verify_manifest(self.result([dict(self.reference, uri='artifact://job-test/' + suffix)]), self.root)


class C8DownloadedStageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = {'base': 'a' * 40, 'target': 'b' * 40}

    def build_result(self, stage_override=None):
        result = {'schema_version': 'e11e12-1', 'status': 'SUCCEEDED',
                  'base_commit': self.request['base'], 'target_commit': self.request['target'],
                  'job_id': 'job-test', 'trace_id': 'trace-test', 'stages': [], 'artifacts': []}
        for name in ('full-check', 'incremental-check'):
            envelope = {'schema_version': 'e11e12-1', 'status': 'SUCCEEDED', 'kind': name,
                        'commit': self.request['base' if name == 'full-check' else 'target'],
                        'job_id': result['job_id'], 'trace_id': result['trace_id'], 'artifacts': []}
            if name == 'incremental-check' and stage_override:
                envelope.update(stage_override)
            content = json.dumps(envelope).encode()
            (self.root / (name + '.json')).write_bytes(content)
            ref = {'uri': 'artifact://job-test/' + name + '.json',
                   'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
            result['artifacts'].append(dict(ref))
            result['stages'].append({'name': name, 'artifact': dict(ref)})
        return result

    def test_both_downloaded_stages_are_verified(self):
        verified = verify_c8_downloads(self.build_result(), self.request, self.root)
        self.assertEqual(verified['files_verified'], 2)
        self.assertEqual([item['name'] for item in verified['stages_verified']],
                         ['full-check', 'incremental-check'])

    def test_empty_or_nonlist_artifacts_cannot_pass(self):
        for artifacts in ([], {}, None, 'not-an-array'):
            result = self.build_result()
            result['artifacts'] = artifacts
            with self.subTest(artifacts=artifacts), self.assertRaisesRegex(AssertionError, 'nonempty artifact list'):
                verify_c8_downloads(result, self.request, self.root)

    def test_stage_reference_must_exist_in_download_manifest(self):
        result = self.build_result()
        result['artifacts'].pop()
        with self.assertRaisesRegex(AssertionError, 'Stage artifact missing'):
            verify_c8_downloads(result, self.request, self.root)

    def test_stage_reference_hash_must_match_download_manifest(self):
        result = self.build_result()
        result['stages'][1]['artifact']['sha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'Stage artifact missing or different'):
            verify_c8_downloads(result, self.request, self.root)

    def test_semantically_wrong_stage_rejected_even_with_matching_hash(self):
        for field, value in (('job_id', 'job-other'), ('trace_id', 'trace-other'),
                             ('commit', 'c' * 40), ('schema_version', 'e14-compose-1'),
                             ('status', 'FAILED'), ('kind', 'full-check')):
            result = self.build_result({field: value})
            with self.subTest(field=field), self.assertRaises((AssertionError, ValueError)):
                verify_c8_downloads(result, self.request, self.root)

    def test_nested_artifact_reference_must_also_be_downloaded(self):
        result = self.build_result({'artifacts': [{'uri': 'artifact://job-test/missing.json',
                                                  'sha256': 'a' * 64, 'bytes': 17}]})
        with self.assertRaisesRegex(AssertionError, 'Stage artifact missing'):
            verify_c8_downloads(result, self.request, self.root)


class PrivateProcessGroupCleanupTests(unittest.TestCase):
    def test_parent_already_exited_still_signals_surviving_private_group(self):
        process = mock.Mock(pid=424242, returncode=0)
        process.poll.return_value = 0
        alive, calls = [True], []

        def killpg(group, sig):
            self.assertEqual(group, process.pid)
            calls.append(sig)
            if not alive[0]:
                raise ProcessLookupError()
            if sig:
                alive[0] = False

        with mock.patch.object(driver.os, 'killpg', side_effect=killpg, create=True), \
                mock.patch.object(driver.os, 'getpgrp', return_value=999, create=True):
            report = cleanup_server_group(process, timeout=0)
        self.assertTrue(report['parent_exited_before_cleanup'])
        self.assertIn(driver.signal.SIGTERM, calls)
        self.assertTrue(report['parent_stopped'])
        self.assertTrue(report['process_group_absent_at_observation'])

    def test_parent_exit_does_not_prove_group_gone(self):
        process = mock.Mock(pid=424242, returncode=0)
        process.poll.return_value = 0
        with mock.patch.object(driver.os, 'killpg', create=True) as signal_group, \
                mock.patch.object(driver.os, 'getpgrp', return_value=999, create=True):
            report = cleanup_server_group(process, timeout=0)
        self.assertTrue(report['parent_stopped'])
        self.assertFalse(report['process_group_absent_at_observation'])
        self.assertIn(mock.call(process.pid, driver.signal.SIGTERM), signal_group.call_args_list)
        self.assertIn(mock.call(process.pid, getattr(driver.signal, 'SIGKILL', 9)), signal_group.call_args_list)

    def test_refuses_own_process_group(self):
        process = mock.Mock(pid=424242, returncode=None)
        with mock.patch.object(driver.os, 'getpgrp', return_value=process.pid, create=True), \
                mock.patch.object(driver.os, 'killpg', create=True) as signal_group:
            with self.assertRaisesRegex(AssertionError, 'caller process group'):
                cleanup_server_group(process)
            signal_group.assert_not_called()


if __name__ == '__main__':
    unittest.main()
