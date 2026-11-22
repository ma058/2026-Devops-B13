"""Member 1: byte, identity and provenance boundaries for A-to-B handoff."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handoff_a_to_b import make_handoff
from consume_report import verify_received, verify_received_bytes
from pipeline import Failure


def encoded(value):
    return (json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8')


class StrictHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = 'a' * 40
        self.job = 'job-local-test'
        self.trace = 'trace-local-test'
        self.payload_path = self.root / 'incremental-report.json'
        self.stage_path = self.root / 'incremental-check.json'
        self.result_path = self.root / 'result.json'
        self.payload = {'schema_version': 'e8e10-1', 'commit': self.target,
                        'findings': [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]}
        self.stage = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
                      'status': 'SUCCEEDED', 'commit': self.target,
                      'job_id': self.job, 'trace_id': self.trace}
        self.result = {'schema_version': 'e11e12-1', 'status': 'SUCCEEDED',
                       'target_commit': self.target, 'job_id': self.job,
                       'trace_id': self.trace, 'stages': [{'name': 'incremental-check'}]}
        self.save_payload()

    def ref(self, path):
        data = path.read_bytes()
        return {'uri': f'artifact://{self.job}/{path.relative_to(self.root).as_posix()}',
                'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

    def save_payload(self):
        self.payload_path.write_bytes(encoded(self.payload))
        self.stage['data'] = copy.deepcopy(self.payload)
        self.stage['artifacts'] = [self.ref(self.payload_path)]
        self.save_stage()

    def save_stage(self):
        self.stage_path.write_bytes(encoded(self.stage))
        self.result['stages'][0]['artifact'] = self.ref(self.stage_path)
        self.save_result()

    def save_result(self):
        self.result_path.write_bytes(encoded(self.result))

    def rejected(self, code, **kwargs):
        with self.assertRaises(Failure) as caught:
            make_handoff(self.result_path, self.target, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_verified_exchange_records_all_sources_and_preserves_originals(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        expected_sha = hashlib.sha256(before['result.json']).hexdigest()
        output = make_handoff(self.result_path, self.target, result_sha256=expected_sha,
                              expected_job_id=self.job, expected_trace_id=self.trace)
        source = output['source_report']
        self.assertEqual(source['result_sha256'], expected_sha)
        self.assertEqual(source['payload_sha256'], self.ref(self.payload_path)['sha256'])
        self.assertTrue(all(source[name] for name in (
            'exchanged_result_sha256_verified', 'exchanged_job_id_verified', 'exchanged_trace_id_verified')))
        self.assertEqual(output['data'], self.payload)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_legacy_call_does_not_claim_exchanged_metadata(self):
        source = make_handoff(self.result_path, self.target)['source_report']
        self.assertFalse(source['exchanged_result_sha256_verified'])
        self.assertFalse(source['exchanged_job_id_verified'])
        self.assertFalse(source['exchanged_trace_id_verified'])

    def test_wrong_independent_result_hash_is_rejected(self):
        self.rejected('ARTIFACT_HASH_MISMATCH', result_sha256='0' * 64)

    def test_invalid_hash_and_target_types_are_rejected(self):
        for value in (True, [], 7, 'A' * 64, 'abc'):
            with self.subTest(value=value):
                self.rejected('INVALID_REQUEST', result_sha256=value)
        for target in (None, [], True, 'abc', 'A' * 40):
            with self.subTest(target=target), self.assertRaises(Failure) as caught:
                make_handoff(self.result_path, target)
            self.assertEqual(caught.exception.code, 'INVALID_REQUEST')

    def test_exchanged_job_and_trace_must_match(self):
        self.rejected('JOB_ID_MISMATCH', expected_job_id='job-other')
        self.rejected('TRACE_ID_MISMATCH', expected_trace_id='trace-other')

    def test_unsafe_source_task_identifier_is_rejected(self):
        self.result['job_id'] = '../other-job'
        self.save_result()
        self.rejected('INVALID_REQUEST')

    def test_stage_identity_and_target_must_match(self):
        for field, bad, code in (
            ('job_id', 'job-other', 'JOB_ID_MISMATCH'),
            ('trace_id', 'trace-other', 'TRACE_ID_MISMATCH'),
            ('commit', 'b' * 40, 'STALE_REPORT'),
            ('kind', 'full-check', 'ARTIFACT_TYPE_MISMATCH'),
            ('status', 'FAILED', 'UPSTREAM_FAILED'),
        ):
            with self.subTest(field=field):
                old = self.stage[field]
                self.stage[field] = bad
                self.save_stage()
                self.rejected(code)
                self.stage[field] = old
        self.save_stage()

    def test_missing_and_duplicate_payload_reference_are_rejected(self):
        ref = self.stage['artifacts'][0]
        for refs in ([], [ref, ref]):
            with self.subTest(refs=refs):
                self.stage['artifacts'] = refs
                self.save_stage()
                self.rejected('ARTIFACT_REFERENCE_MISMATCH')

    def test_envelope_data_cannot_disagree_with_payload(self):
        self.stage['data']['findings'] = []
        self.save_stage()
        self.rejected('REPORT_DATA_MISMATCH')

    def test_boolean_and_integer_data_are_not_equal(self):
        self.payload['metadata'] = {'flag': True}
        self.save_payload()
        self.stage['data']['metadata']['flag'] = 1
        self.save_stage()
        self.rejected('REPORT_DATA_MISMATCH')

    def test_payload_schema_and_typed_findings_are_checked(self):
        original = copy.deepcopy(self.payload)
        for field, bad, code in (
            ('schema_version', 'other', 'SCHEMA_MISMATCH'),
            ('commit', 'b' * 40, 'STALE_REPORT'),
            ('findings', [{'type': 'MISSING', 'target': 7, 'dependency': 'a.h'}], 'INVALID_REPORT'),
        ):
            with self.subTest(field=field):
                self.payload = copy.deepcopy(original)
                self.payload[field] = bad
                self.save_payload()
                self.rejected(code)

    def test_duplicate_keys_and_nonfinite_numbers_are_rejected(self):
        original = self.result_path.read_bytes()
        suffixes = (b',"status":"SUCCEEDED"', b',"number":NaN',
                    b',"number":Infinity', b',"number":1e999')
        for suffix in suffixes:
            with self.subTest(suffix=suffix):
                self.result_path.write_bytes(original.rstrip()[:-1] + suffix + b'}')
                self.rejected('INVALID_REPORT')
        self.result_path.write_bytes(original)

    def test_duplicate_payload_keys_are_rejected_even_with_matching_hash(self):
        data = self.payload_path.read_bytes().rstrip()[:-1] + b',"findings":[]}'
        self.payload_path.write_bytes(data)
        self.stage['artifacts'] = [self.ref(self.payload_path)]
        self.save_stage()
        self.rejected('INVALID_REPORT')

    def test_profile_binding_is_preserved_and_must_match_all_layers(self):
        profile_hash = 'c' * 64
        self.payload['profile_sha256'] = profile_hash
        self.stage['profile_sha256'] = profile_hash
        self.result['profile_sha256'] = profile_hash
        self.save_payload()
        report = make_handoff(self.result_path, self.target)
        self.assertEqual(report['profile_sha256'], profile_hash)
        self.assertEqual(report['data']['profile_sha256'], profile_hash)
        self.result['profile_sha256'] = 'd' * 64
        self.save_result()
        self.rejected('PROFILE_HASH_MISMATCH')
        del self.result['profile_sha256']
        self.save_result()
        self.rejected('PROFILE_HASH_MISMATCH')

    def test_duplicate_stages_and_malformed_stage_list_are_rejected(self):
        original = copy.deepcopy(self.result['stages'])
        for value, code in ((original * 2, 'ARTIFACT_REFERENCE_MISMATCH'),
                            ({}, 'INVALID_REPORT'), ([None], 'INVALID_REPORT')):
            with self.subTest(value=value):
                self.result['stages'] = value
                self.save_result()
                self.rejected(code)

    def test_reference_path_escape_foreign_job_and_bool_size_are_rejected(self):
        original = copy.deepcopy(self.stage['artifacts'][0])
        for uri in (f'artifact://{self.job}/../outside.json',
                    f'artifact://{self.job}//absolute',
                    f'artifact://{self.job}/C:/file',
                    f'artifact://{self.job}/sub\\file',
                    f'artifact://{self.job}/./incremental-report.json'):
            with self.subTest(uri=uri):
                self.stage['artifacts'] = [dict(original, uri=uri)]
                self.save_stage()
                self.rejected('UNSAFE_PATH')
        self.stage['artifacts'] = [dict(original, uri='artifact://job-other/incremental-report.json')]
        self.save_stage()
        self.rejected('ARTIFACT_REFERENCE_MISMATCH')
        self.stage['artifacts'] = [dict(original, bytes=True)]
        self.save_stage()
        self.rejected('INVALID_REPORT')

    @unittest.skipUnless(os.name == 'posix', 'Real symlink creation is validated on Linux')
    def test_symlink_artifact_even_inside_run_is_rejected(self):
        alias = self.root / 'alias.json'
        alias.write_bytes(self.payload_path.read_bytes())
        self.payload_path.unlink()
        self.payload_path.symlink_to(alias.name)
        self.rejected('UNSAFE_PATH')

    def test_all_declared_result_references_are_checked(self):
        self.result['artifacts'] = [dict(self.ref(self.payload_path), sha256='0' * 64)]
        self.save_result()
        self.rejected('ARTIFACT_HASH_MISMATCH')

    def test_each_file_is_consumed_from_the_same_single_read(self):
        # Simulate a concurrent writer after read_bytes returned the trusted
        # bytes. Derived data must come from those bytes, not a second read.
        read_bytes = Path.read_bytes
        counts = {}
        initial = self.payload_path.read_bytes()
        def observed(path):
            data = read_bytes(path)
            counts[path] = counts.get(path, 0) + 1
            if path == self.payload_path:
                path.write_bytes(b'{"changed_after_read":true}')
            return data
        with mock.patch.object(Path, 'read_bytes', observed):
            output = make_handoff(self.result_path, self.target)
        self.assertEqual(output['data'], json.loads(initial))
        self.assertEqual(counts, {self.result_path: 1, self.stage_path: 1, self.payload_path: 1})

    def test_byte_verifier_matches_file_api_and_performs_no_io(self):
        env_sha, pay_sha = self.ref(self.stage_path)['sha256'], self.ref(self.payload_path)['sha256']
        old = verify_received(self.stage_path, env_sha, self.payload_path, pay_sha,
                              self.target, self.job, self.trace)
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected reread')):
            new = verify_received_bytes(old.envelope_bytes, env_sha, old.payload_bytes,
                                        pay_sha, self.target, self.job, self.trace)
        self.assertEqual(old, new)
        with self.assertRaises(Failure) as caught:
            verify_received_bytes(old.envelope_bytes, env_sha, b'{}', pay_sha,
                                  self.target, self.job, self.trace)
        self.assertEqual(caught.exception.code, 'ARTIFACT_HASH_MISMATCH')


if __name__ == '__main__':
    unittest.main()
