"""Portable profile contracts. These tests do not certify Docker execution."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_profile as pp
import pipeline
import consume_report


class RealProfileContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'source'; self.project.mkdir()
        self.original = Path(__file__).with_name('fixtures').joinpath('tomlc99.Makefile').read_bytes()
        (self.project / 'Makefile').write_bytes(self.original)
        for name in ('toml.c', 'toml.h', 'toml_json.c', 'toml_extra.h'):
            (self.project / name).write_bytes(b'/* fixture for contracts only */\n')
        for args in (['init'], ['config', 'core.autocrlf', 'false'], ['config', 'user.name', 'Fixture'],
                     ['config', 'user.email', 'fixture@localhost'], ['add', '.'], ['commit', '-m', 'fixture']):
            subprocess.run(['git', *args], cwd=self.project, check=True, capture_output=True)
        self.sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.project, text=True).strip()
        self.report = {'schema_version': 'e8e10-1', 'commit': self.sha,
                       'profile_sha256': pp.profile_hash(pp.PROFILE), 'findings': [
                           {'type': 'MISSING', 'target': 'toml.o', 'dependency': h}
                           for h in ('toml.h', 'toml_extra.h')]}

    def tearDown(self):
        # Git's readonly objects need explicit chmod on Windows.
        import os, shutil, stat
        def retry(fn, path, exc):
            os.chmod(path, stat.S_IWRITE); fn(path)
        shutil.rmtree(self.root, onerror=retry)
        self.tmp.cleanup()

    def test_snapshot_accepts_audited_layout_without_c1_only_dockerfile(self):
        sha = pipeline.snapshot(self.project, self.sha, self.root / 'copy', self.root / 'logs', profile=pp.PROFILE)
        self.assertEqual(sha, self.sha)
        self.assertEqual((self.root / 'copy/Makefile').read_bytes(), self.original)

    def test_consumer_exposes_bound_profile(self):
        self.assertIn('profile', inspect.signature(consume_report.consume).parameters)
        self.assertIn('profile_sha256', inspect.signature(consume_report.consume).parameters)

    def test_versioned_json_matches_module(self):
        path = Path(__file__).resolve().parents[2] / 'course/e11-e12/profiles/tomlc99-release-v1.json'
        self.assertEqual(pp.resolve_profile(json.loads(path.read_bytes())), pp.PROFILE)

    def test_profile_rejects_unknown_keys_wrong_types_flags_and_paths(self):
        for key, value in [('exit_code', False), ('recursive_scan', 0), ('extra', 'x'),
                           ('effective_flags', pp.FLAGS[::-1]), ('run_argv', ['/bin/sh', '-c', 'true'])]:
            raw = copy.deepcopy(pp.PROFILE); raw[key] = value
            with self.subTest(key=key), self.assertRaises(pp.ProfileError): pp.resolve_profile(raw)

    def test_override_presence_is_rejected_even_empty(self):
        pp.check_environment({})
        for key in pp.OVERRIDES:
            with self.subTest(key=key), self.assertRaises(pp.ProfileError): pp.check_environment({key: ''})

    def test_missing_headers_patch_only_target_preserving_all_other_bytes(self):
        self.report['findings'] += [self.report['findings'][0], {'type': 'REDUNDANT', 'target': 'toml.o', 'dependency': 'toml.c'}]
        diff, edits = pp.patch(self.project, self.report, pp.PROFILE)
        self.assertEqual(len(edits), 2)
        self.assertEqual((self.project / 'Makefile').read_bytes(), self.original)
        patchfile = self.root / 'change.patch'; patchfile.write_bytes(diff.encode())
        subprocess.run(['git', 'apply', str(patchfile)], cwd=self.project, check=True, capture_output=True)
        expected = self.original.replace(b'toml.o: toml.c\n', b'toml.o: toml.c toml.h toml_extra.h\n')
        self.assertEqual((self.project / 'Makefile').read_bytes(), expected)
        self.assertEqual(pp.patch(self.project, self.report, pp.PROFILE), ('', []))

    def test_stale_profile_and_late_unsafe_findings_never_write(self):
        cases = []
        for key, value in [('commit', '0' * 40), ('profile_sha256', '0' * 64)]:
            r = copy.deepcopy(self.report); r[key] = value; cases.append(r)
        for target, dep in [('toml.o', '../outside.h'), ('toml_json', 'toml.h'), ('toml.o', 'absent.h')]:
            r = copy.deepcopy(self.report); r['findings'].append({'type': 'MISSING', 'target': target, 'dependency': dep}); cases.append(r)
        for r in cases:
            with self.subTest(report=r), self.assertRaises(pp.ProfileError): pp.patch(self.project, r, pp.PROFILE)
            self.assertEqual((self.project / 'Makefile').read_bytes(), self.original)

    def test_unrelated_makefile_change_rejected(self):
        (self.project / 'Makefile').write_bytes(self.original + b'\n# unversioned change\n')
        with self.assertRaises(pp.ProfileError): pp.declarations(self.project, pp.PROFILE)

    def test_profile_hash_checked_before_snapshot_output(self):
        out = self.root / 'bad-profile-output'
        request = {'mode': 'e12', 'repo': str(self.project), 'base': self.sha, 'target': self.sha,
                   'profile': pp.PROFILE, 'profile_sha256': '0' * 64}
        result = pipeline.execute(request, out)
        self.assertEqual(result['error']['code'], 'PROFILE_HASH_MISMATCH')
        self.assertFalse((out / 'base-project').exists())

    def test_consumer_rejects_mismatched_profile_before_any_output_or_image(self):
        payload = self.root / 'report.json'; payload.write_bytes(pp.canonical(self.report))
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        envelope = {'schema_version': 'e11e12-1', 'kind': 'incremental-check', 'status': 'SUCCEEDED',
                    'commit': self.sha, 'job_id': 'job-contract', 'trace_id': 'trace-contract',
                    'profile_sha256': pp.profile_hash(pp.PROFILE), 'data': self.report,
                    'artifacts': [{'uri': 'artifact://job-contract/incremental-report.json',
                                   'sha256': digest, 'bytes': payload.stat().st_size}]}
        ep = self.root / 'envelope.json'; ep.write_bytes(pp.canonical(envelope))
        for profile, phash, code in [(None, None, 'PROFILE_REQUIRED'), (pp.PROFILE, '0' * 64, 'PROFILE_HASH_MISMATCH')]:
            out = self.root / code
            with self.assertRaises(ValueError) as caught:
                consume_report.consume(ep, hashlib.sha256(ep.read_bytes()).hexdigest(), payload, digest,
                    self.project, self.sha, 'job-contract', 'trace-contract', out,
                    profile=profile, profile_sha256=phash)
            self.assertEqual(caught.exception.code, code)
            self.assertFalse(out.exists())
            self.assertEqual((self.project / 'Makefile').read_bytes(), self.original)

    def test_recompile_parser_requires_success_and_exact_release_flags(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'environment/services/buildchecker'))
        trace = self.root / 'trace'; trace.mkdir()
        argv = ['cc', *pp.FLAGS, '-c', '-o', 'toml.o', 'toml.c']
        record = 'execve("/usr/bin/cc", ' + json.dumps(argv) + ', 0x0) = '
        (trace / 't.1').write_bytes((record + '-1 ENOENT\n').encode())
        self.assertEqual(pp.observed_recompile(trace), [])
        (trace / 't.2').write_bytes((record + '0\n').encode())
        observed = pp.observed_recompile(trace)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]['argv'], argv)


if __name__ == '__main__': unittest.main(verbosity=2)
