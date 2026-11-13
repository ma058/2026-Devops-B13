"""Member 1 independent handoff-contract tests; no compiler or Docker required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from consume_report import Failure, consume, verify_received


class Member1HandoffContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.sentinel = self.repo / 'Makefile'
        self.original = b'main.o: main.c unused.h\n'
        self.sentinel.write_bytes(self.original)
        self.out = self.root / 'output-must-not-exist'
        self.target = '1' * 40
        self.job = 'job-independent-handoff'
        self.trace = 'trace-independent-handoff'
        self.payload = {'schema_version': 'e8e10-1', 'commit': self.target,
            'findings': [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'},
                         {'type': 'REDUNDANT', 'target': 'main.o', 'dependency': 'unused.h'}]}
        self.envelope = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
            'status': 'SUCCEEDED', 'commit': self.target, 'job_id': self.job,
            'trace_id': self.trace, 'data': self.payload}
        self.envelope_path = self.root / 'received-envelope.json'
        self.payload_path = self.root / 'received-payload.json'
        self.write_input()

    def write_input(self):
        self.payload_bytes = json.dumps(self.payload, sort_keys=True).encode()
        self.payload_path.write_bytes(self.payload_bytes)
        self.payload_sha = hashlib.sha256(self.payload_bytes).hexdigest()
        self.envelope['artifacts'] = [{
            'uri': f'artifact://{self.job}/incremental-report.json',
            'sha256': self.payload_sha, 'bytes': len(self.payload_bytes)}]
        self.write_envelope()

    def write_envelope(self):
        self.envelope_path.write_text(json.dumps(self.envelope), encoding='utf-8')
        self.envelope_sha = hashlib.sha256(self.envelope_path.read_bytes()).hexdigest()

    def reject_without_output(self, code):
        with self.assertRaises(Failure) as caught:
            consume(self.envelope_path, self.envelope_sha, self.payload_path, self.payload_sha,
                    self.repo, self.target, self.job, self.trace, self.out)
        self.assertEqual(code, caught.exception.code)
        self.assertEqual(self.original, self.sentinel.read_bytes())
        self.assertFalse(self.out.exists(), 'Invalid input must not create a repair workspace')

    def test_matching_bytes_and_task_accepted_without_execution(self):
        result = verify_received(self.envelope_path, self.envelope_sha,
                                 self.payload_path, self.payload_sha, self.target, self.job, self.trace)
        self.assertEqual(self.payload, result.payload)
        self.assertEqual(self.payload_bytes, result.payload_bytes)
        self.assertEqual(self.envelope_path.read_bytes(), result.envelope_bytes)
        self.assertFalse(self.out.exists())

    def test_correct_outer_commit_cannot_hide_stale_inner_commit(self):
        self.payload['commit'] = '2' * 40
        self.write_input()
        self.assertEqual(self.target, self.envelope['commit'])
        self.reject_without_output('STALE_REPORT')

    def test_payload_byte_tampering_rejected_before_workspace(self):
        self.payload_path.write_bytes(self.payload_bytes + b' ')
        self.reject_without_output('ARTIFACT_HASH_MISMATCH')

    def test_envelope_byte_tampering_rejected_before_workspace(self):
        self.envelope_path.write_bytes(self.envelope_path.read_bytes() + b' ')
        self.reject_without_output('ARTIFACT_HASH_MISMATCH')

    def test_job_id_mismatch_rejected(self):
        self.envelope['job_id'] = 'job-different'
        self.write_envelope()
        self.reject_without_output('JOB_ID_MISMATCH')

    def test_trace_id_mismatch_rejected(self):
        self.envelope['trace_id'] = 'trace-different'
        self.write_envelope()
        self.reject_without_output('TRACE_ID_MISMATCH')

    def test_embedded_data_must_equal_received_payload(self):
        self.envelope['data'] = dict(self.payload, findings=[])
        self.write_envelope()
        self.reject_without_output('REPORT_DATA_MISMATCH')

    def test_payload_reference_hash_must_match_exchanged_hash(self):
        self.envelope['artifacts'][0]['sha256'] = '0' * 64
        self.write_envelope()
        self.reject_without_output('ARTIFACT_HASH_MISMATCH')

    def test_reference_cannot_point_to_a_different_job(self):
        self.envelope['artifacts'][0]['uri'] = 'artifact://job-other/incremental-report.json'
        self.write_envelope()
        self.reject_without_output('ARTIFACT_REFERENCE_MISMATCH')

    def test_duplicate_payload_reference_is_ambiguous(self):
        self.envelope['artifacts'].append(dict(self.envelope['artifacts'][0]))
        self.write_envelope()
        self.reject_without_output('ARTIFACT_REFERENCE_MISMATCH')

    def test_reference_byte_count_must_match(self):
        self.envelope['artifacts'][0]['bytes'] += 1
        self.write_envelope()
        self.reject_without_output('ARTIFACT_SIZE_MISMATCH')

    def test_fixed_report_cannot_impersonate_incremental_handoff(self):
        self.envelope['kind'] = 'fixed-md'
        self.write_envelope()
        self.reject_without_output('ARTIFACT_TYPE_MISMATCH')

    def test_failed_upstream_cannot_be_consumed(self):
        self.envelope['status'] = 'FAILED'
        self.write_envelope()
        self.reject_without_output('UPSTREAM_FAILED')

    def test_outer_schema_must_be_supported(self):
        self.envelope['schema_version'] = 'e2'
        self.write_envelope()
        self.reject_without_output('SCHEMA_MISMATCH')


if __name__ == '__main__':
    unittest.main()
