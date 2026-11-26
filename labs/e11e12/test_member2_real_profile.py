"""Portable profile contracts. These tests do not certify Docker execution."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import shutil
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


class B13LevelV1Contracts(unittest.TestCase):
    fixtures = Path(__file__).resolve().parents[2] / 'course/e13-e14/projects/b13-level-v1'

    def setUp(self):
        self.profile = json.loads((self.fixtures / 'profile.json').read_bytes())

    def test_requires_exact_frozen_profile_and_hash(self):
        self.assertEqual(pp.bind_profile(self.profile, pp.B13_PROFILE_SHA256), self.profile)
        for key, value in [('repair_targets', ['main.o']), ('effective_flags', ['-O1']),
                           ('build_argv', ['make', 'all']), ('exit_code', False)]:
            wrong = dict(self.profile, **{key: value})
            with self.subTest(key=key), self.assertRaises(pp.ProfileError):
                pp.bind_profile(wrong, hashlib.sha256(pp.canonical(wrong)).hexdigest())
        with self.assertRaises(pp.ProfileError):
            pp.bind_profile(self.profile, pp.profile_hash(pp.PROFILE))

    def test_only_frozen_recipes_and_scoped_header_insertions_allowed(self):
        for version in ('base', 'target'):
            self.assertTrue(pp.check_project(self.fixtures / version, self.profile))
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'target'
            shutil.copytree(self.fixtures / 'target', project)
            makefile = project / 'Makefile'
            source = makefile.read_bytes()
            for old, new in [(b'gcc main.o helper.o', b'cc main.o helper.o'),
                             (b'HEADERS = unused.h', b'HEADERS = config.h'),
                             (b'helper.o: helper.c', b'helper.o: helper.c config.h'),
                             (b'helper.o: helper.c', b'helper.o: helper.c extra.h extra.h')]:
                makefile.write_bytes(source.replace(old, new))
                with self.subTest(change=new), self.assertRaises(pp.ProfileError):
                    pp.check_project(project, self.profile)
                self.assertEqual(makefile.read_bytes(), source.replace(old, new))
            makefile.write_bytes(source)
            (project / 'extra.c').write_bytes(b'')
            with self.assertRaises(pp.ProfileError):
                pp.check_project(project, self.profile)

    def test_exact_two_target_patch_and_no_writes_on_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'project'
            subprocess.run(['git', 'clone', '-q', '-c', 'core.autocrlf=false',
                            str(self.fixtures / 'project.bundle'), str(project)], check=True)
            commit = json.loads((self.fixtures / 'manifest.json').read_bytes())['target']
            subprocess.run(['git', 'checkout', '-q', '--detach', commit], cwd=project, check=True)
            makefile = project / 'Makefile'
            source = makefile.read_bytes()
            report = {'schema_version': 'e8e10-1', 'commit': commit,
                      'profile_sha256': pp.B13_PROFILE_SHA256,
                      'findings': [{'type': 'MISSING', 'target': 'helper.o', 'dependency': 'extra.h'},
                                   {'type': 'REDUNDANT', 'target': 'main.o', 'dependency': 'unused.h'},
                                   {'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]}
            for field, value in [('commit', '0' * 40), ('profile_sha256', '0' * 64),
                                 ('findings', report['findings'] + [
                                     {'type': 'MISSING', 'target': 'helper.o', 'dependency': 'config.h'}])]:
                with self.subTest(field=field), self.assertRaises(pp.ProfileError):
                    pp.patch(project, dict(report, **{field: value}), self.profile)
                self.assertEqual(makefile.read_bytes(), source)
            diff, edits = pp.patch(project, report, self.profile)
            self.assertEqual(len(edits), 2)
            self.assertEqual(makefile.read_bytes(), source)
            subprocess.run(['git', 'apply', '-'], input=diff.encode(), cwd=project, check=True)
            expected = source.replace(b'main.o: main.c $(HEADERS)\n', b'main.o: main.c $(HEADERS) config.h\n')
            expected = expected.replace(b'helper.o: helper.c\n', b'helper.o: helper.c extra.h\n')
            self.assertEqual(makefile.read_bytes(), expected)
            self.assertTrue(pp.check_project(project, self.profile))

    def test_b13_header_probe_requires_successful_main_object_compile(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'environment/services/buildchecker'))
        good = ['gcc', '-O0', '-c', 'main.c', '-o', 'main.o']
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / 't.1'
            rows = [(good, '-1 ENOENT'), (['gcc', '-O0', '-c', 'helper.c', '-o', 'helper.o'], '0'),
                    (['gcc', '-O2', '-c', 'main.c', '-o', 'main.o'], '0'), (good, '0')]
            trace.write_text(''.join('execve("/usr/bin/gcc", ' + json.dumps(argv) + ', 0x0) = ' + ret + '\n'
                                     for argv, ret in rows), encoding='utf-8')
            hits = pp.observed_recompile(Path(tmp), self.profile)
            self.assertEqual([hit['argv'] for hit in hits], [good])

if __name__ == '__main__': unittest.main(verbosity=2)
