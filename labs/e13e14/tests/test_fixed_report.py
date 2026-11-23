"""Member 1 E11-B input-boundary regression tests.

Git resolution/clones and input byte validation are real. The two successful
pipeline tests stub Docker/validation to test input caching and legacy routing;
they are NOT evidence of a real Docker or A13 end-to-end experiment.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'labs/e11e12'))
import pipeline
import project_profile as pp


class FixedReportPreflight(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'project'
        self.repo.mkdir()
        for name, contents in {
            'Makefile': 'main.o: main.c unused.h\n\tcc -c main.c -o main.o\n',
            'main.c': '#include "config.h"\nint main(void) { return 0; }\n',
            'helper.c': 'int helper(void) { return 1; }\n',
            'config.h': '#define VALUE 1\n',
            'unused.h': '#define UNUSED 1\n',
        }.items():
            (self.repo / name).write_bytes(contents.encode())
        self.git('init', '-q')
        self.git('config', 'core.autocrlf', 'false')
        self.git('add', '.')
        self.git('-c', 'user.name=member1-contract-test', '-c',
                 'user.email=member1-contract-test@example.invalid', 'commit', '-qm', 'fixture')
        self.target = self.git('rev-parse', 'HEAD')
        self.envelope = {
            'schema_version': 'e11e12-1', 'kind': 'fixed-md', 'status': 'SUCCEEDED',
            'commit': self.target,
            'data': {'schema_version': 'e8e10-1', 'commit': self.target,
                     'findings': [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]},
        }
        self.fixed = self.root / 'fixed-md.json'
        self.write_report(self.envelope)
        self.request = {'mode': 'e11-b', 'repo': str(self.repo),
                        'base': self.target, 'target': self.target,
                        'candidate': str(self.root / 'candidate.Dockerfile'),
                        'fixed_report': str(self.fixed),
                        'fixed_report_sha256': hashlib.sha256(self.fixed.read_bytes()).hexdigest()}
        self.counter = 0

    def git(self, *args):
        p = subprocess.run(['git', *args], cwd=self.repo, capture_output=True, text=True, timeout=30)
        if p.returncode:
            raise AssertionError(p.stderr)
        return p.stdout.strip()

    def write_report(self, envelope):
        self.fixed.write_bytes((json.dumps(envelope, indent=3) + '\n\n').encode())

    def digest(self):
        return hashlib.sha256(self.fixed.read_bytes()).hexdigest()

    def before(self):
        return {p.relative_to(self.repo).as_posix(): p.read_bytes()
                for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts}

    def out(self):
        self.counter += 1
        return self.root / ('run-' + str(self.counter))

    def assert_rejected(self, request, code):
        before = self.before()
        before_git = self.git('status', '--porcelain')
        out = self.out()
        with patch.object(pipeline, 'snapshot') as snapshot, \
                patch('draft.autobuild.auto_build') as docker, \
                patch.object(pipeline, 'patch') as repair, \
                patch.object(pipeline, 'ImageRuntime') as runtime:
            result = pipeline.execute(request, out)
        self.assertEqual(result['status'], 'FAILED', result)
        self.assertEqual(result['error']['code'], code, result)
        snapshot.assert_not_called()
        docker.assert_not_called()
        repair.assert_not_called()
        runtime.assert_not_called()
        self.assertFalse((out / 'target-project').exists())
        self.assertFalse((out / 'base-project').exists())
        self.assertEqual(self.before(), before)
        self.assertEqual(self.git('status', '--porcelain'), before_git)
        self.assertEqual(json.loads((out / 'result.json').read_bytes()), result)

    def test_valid_hash_retains_exact_bytes_and_marks_verification(self):
        raw = self.fixed.read_bytes()
        received, envelope, binding = pipeline.read_fixed_report(self.request, self.target)
        self.assertEqual(received, raw)
        self.assertEqual(envelope, self.envelope)
        self.assertEqual(binding, {'sha256': self.digest(), 'bytes': len(raw),
                                   'exchanged_hash_verified': True})

    def test_omitted_hash_keeps_legacy_compatibility_without_claiming_verification(self):
        request = dict(self.request)
        del request['fixed_report_sha256']
        received, envelope, binding = pipeline.read_fixed_report(request, self.target)
        self.assertEqual(received, self.fixed.read_bytes())
        self.assertEqual(envelope, self.envelope)
        self.assertFalse(binding['exchanged_hash_verified'])
        self.assertEqual(binding['sha256'], self.digest())

    def test_present_invalid_hash_never_disables_verification(self):
        for value in (None, '', False, 17, [], {}, 'A' * 64, 'a' * 63, 'g' * 64):
            with self.subTest(value=value):
                self.assert_rejected(dict(self.request, fixed_report_sha256=value), 'INVALID_REQUEST')

    def test_semantically_equal_changed_bytes_rejected_before_any_project_execution(self):
        self.fixed.write_bytes(json.dumps(self.envelope, separators=(',', ':')).encode())
        self.assert_rejected(self.request, 'ARTIFACT_HASH_MISMATCH')

    def test_old_envelope_rejected_before_snapshot_or_draft(self):
        stale = copy.deepcopy(self.envelope)
        stale['commit'] = 'a' * 40
        self.write_report(stale)
        self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'STALE_REPORT')

    def test_old_payload_rejected_before_snapshot_or_draft(self):
        stale = copy.deepcopy(self.envelope)
        stale['data']['commit'] = 'a' * 40
        self.write_report(stale)
        self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'STALE_REPORT')

    def test_wrong_schema_kind_and_failed_upstream_rejected(self):
        for field, value, code in (
            ('schema_version', 'e14-compose-1', 'SCHEMA_MISMATCH'),
            ('kind', 'incremental-check', 'ARTIFACT_TYPE_MISMATCH'),
            ('status', 'FAILED', 'UPSTREAM_FAILED'),
        ):
            with self.subTest(field=field):
                self.write_report(dict(self.envelope, **{field: value}))
                self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), code)

    def test_duplicate_keys_non_json_numbers_and_non_object_root_rejected(self):
        valid = json.dumps(self.envelope)
        for raw in (b'[]', b'null', b'{', b'{"x":1,"x":2}',
                    valid[:-1].encode() + b',"extra":NaN}',
                    valid[:-1].encode() + b',"extra":Infinity}',
                    valid[:-1].encode() + b',"extra":1e999}'):
            with self.subTest(raw=raw[:50]):
                self.fixed.write_bytes(raw)
                self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'INVALID_REPORT')

    def test_bad_data_and_findings_types_rejected_before_draft(self):
        for data in (None, [], True, {'commit': self.target, 'schema_version': 'e8e10-1', 'findings': True},
                     {'commit': self.target, 'schema_version': 'e8e10-1', 'findings': [True]},
                     {'commit': self.target, 'schema_version': 'e8e10-1', 'findings': [
                         {'type': 'MISSING', 'target': True, 'dependency': 'config.h'}]}):
            with self.subTest(data=data):
                self.write_report(dict(self.envelope, data=data))
                self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'INVALID_REPORT')

    def test_profile_report_without_explicit_profile_rejected(self):
        for where in ('envelope', 'payload'):
            with self.subTest(where=where):
                report = copy.deepcopy(self.envelope)
                (report if where == 'envelope' else report['data'])['profile_sha256'] = 'a' * 64
                self.write_report(report)
                self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'PROFILE_REQUIRED')

    def test_profile_binding_checked_before_snapshot(self):
        report = copy.deepcopy(self.envelope)
        report['profile_sha256'] = 'a' * 64
        self.write_report(report)
        request = dict(self.request, fixed_report_sha256=self.digest(),
                       profile=copy.deepcopy(pp.PROFILE), profile_sha256=pp.profile_hash(pp.PROFILE))
        self.assert_rejected(request, 'PROFILE_HASH_MISMATCH')

    def test_valid_real_profile_keeps_binding_and_scoped_findings(self):
        report = copy.deepcopy(self.envelope)
        digest = pp.profile_hash(pp.PROFILE)
        report['profile_sha256'] = digest
        report['data']['profile_sha256'] = digest
        report['data']['findings'] = [
            {'type': 'MISSING', 'target': 'toml.o', 'dependency': 'toml.h'}]
        self.write_report(report)
        request = dict(self.request, fixed_report_sha256=self.digest())
        received, parsed, _ = pipeline.read_fixed_report(request, self.target, pp.PROFILE)
        self.assertEqual(received, self.fixed.read_bytes())
        self.assertEqual(parsed, report)

    def test_reader_requires_resolved_complete_target(self):
        for target in (None, False, self.target[:7], 'HEAD', 'A' * 40):
            with self.subTest(target=target), self.assertRaises(pipeline.Failure) as raised:
                pipeline.read_fixed_report(self.request, target)
            self.assertEqual(raised.exception.code, 'INVALID_REQUEST')

    def test_safe_upstream_provenance_preserved_and_mixed_job_uri_rejected(self):
        report = copy.deepcopy(self.envelope)
        source = {'job_id': 'job-a13', 'trace_id': 'trace-a13',
                  'uri': 'artifact://job-a13/incremental-check.json', 'sha256': 'b' * 64,
                  'result_sha256': 'c' * 64}
        report['source_report'] = source
        self.write_report(report)
        request = dict(self.request, fixed_report_sha256=self.digest())
        _, parsed, binding = pipeline.read_fixed_report(request, self.target)
        self.assertEqual(parsed['source_report'], source)
        self.assertEqual(binding['source_report'], source)
        report['source_report']['uri'] = 'artifact://other-job/incremental-check.json'
        self.write_report(report)
        self.assert_rejected(dict(self.request, fixed_report_sha256=self.digest()), 'ARTIFACT_REFERENCE_MISMATCH')

    def successful_unit_run(self, request, mutate_input=False):
        before = self.before()
        raw = self.fixed.read_bytes()
        out = self.out()
        image_id = 'sha256:' + 'd' * 64
        runtime = Mock()
        runtime.image_id = image_id
        runtime.operations = []

        def docker(project, candidate, folder, expected, timeout):
            if mutate_input:
                self.fixed.write_bytes(b'NOT JSON -- changed after successful preflight')
            result = {'status': 'SUCCEEDED', 'attempts': [{'image_id': image_id}]}
            pipeline.save(folder / 'result.json', result)
            return result

        def validate(project, patchfile, folder):
            runtime.operations.append({'operation': 'validate', 'unit_test_stub': True})
            result = {'accepted': True, 'checks': {'unit_test_stub': True}}
            pipeline.save(folder / 'validation.json', result)
            return result

        def full(project, folder):
            runtime.operations.append({'operation': 'full', 'unit_test_stub': True})
            pipeline.save(folder / 'findings.json', [])
            return {'findings': []}

        runtime.validate.side_effect = validate
        runtime.full.side_effect = full
        with patch('draft.autobuild.auto_build', side_effect=docker) as build, \
                patch.object(pipeline, 'ImageRuntime', return_value=runtime), \
                patch.object(pipeline, 'patch', wraps=pipeline.patch) as repair:
            result = pipeline.execute(request, out)
        self.assertEqual(result['status'], 'SUCCEEDED', result)
        build.assert_called_once()
        self.assertEqual(repair.call_args.args[1], self.envelope['data'])
        self.assertEqual((out / 'fixed-md-input.json').read_bytes(), raw)
        self.assertEqual(result['fixed_report_binding']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual([s['name'] for s in result['stages']], ['draft', 'fixed-md', 'repair', 'recheck'])
        self.assertEqual(self.before(), before)
        return result

    def test_mutation_after_preflight_cannot_replace_consumed_bytes(self):
        result = self.successful_unit_run(self.request, mutate_input=True)
        self.assertTrue(result['fixed_report_binding']['exchanged_hash_verified'])

    def test_legacy_request_without_hash_completes_same_four_stage_route(self):
        request = dict(self.request)
        del request['fixed_report_sha256']
        result = self.successful_unit_run(request)
        self.assertFalse(result['fixed_report_binding']['exchanged_hash_verified'])

    def test_target_branch_resolves_to_real_sha_before_checks(self):
        request = dict(self.request, target='HEAD')
        result = self.successful_unit_run(request)
        self.assertEqual(result['target_commit'], self.target)


if __name__ == '__main__':
    unittest.main()
