"""DRAFT build context tests for private checkouts and non-root image workers."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import member2_service as service


class DraftStaging(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.job = self.root/'work/jobs/job-12345678'
        self.source = self.job/'target'
        self.source.mkdir(parents=True)
        self.candidate = self.root/'data/candidate.Dockerfile'
        self.candidate.parent.mkdir()
        self.candidate.write_bytes(b'candidate bytes')
        self.manifest = {'target_files': {}, 'image_files': ['config.h', 'script.sh'],
                         'candidate_sha256': service.profiles.digest(self.candidate.read_bytes()),
                         'expected_output': '1'}
        for name in ['config.h', 'script.sh', 'Dockerfile.broken', 'README.md']:
            raw = name.encode()
            entry = self.source/name
            entry.write_bytes(raw)
            entry.chmod(0o700 if name == 'script.sh' else 0o600)
            self.manifest['target_files'][name] = service.profiles.digest(raw)
        (self.source/'roles.secret.env').write_bytes(b'private material')
        (self.source/'.git').mkdir()

    def request(self, inspect_build):
        module = types.ModuleType('draft.autobuild')
        module.auto_build = inspect_build
        with patch.dict(sys.modules, {'draft.autobuild': module}), patch.object(service, 'ROLE', 'draft'), \
             patch.object(service, 'ROOT', self.root), patch.object(service, 'STATE', self.root/'state'), \
             patch.object(service, 'context', return_value=(self.manifest, {}, self.job)), \
             patch.object(service, 'project', return_value=self.source):
            return service.run({'job_id': 'job-12345678', 'out': str(self.job/'draft'), 'candidate': str(self.candidate)})

    def test_private_checkout_builds_from_verified_disposable_copy(self):
        original_mode = (self.source/'config.h').stat().st_mode
        directory = []
        applied = {}
        original_chmod = Path.chmod

        def chmod(path, mode, *args, **kwargs):
            applied[path] = mode
            return original_chmod(path, mode, *args, **kwargs)

        def inspect(context, candidate, out, expected_output, timeout):
            directory.append(context)
            self.assertEqual(context.parent, self.job)
            self.assertNotEqual(context, self.source)
            self.assertEqual({p.name for p in context.iterdir()}, set(self.manifest['target_files']))
            self.assertEqual((candidate, out, expected_output, timeout), (self.candidate, self.job/'draft', '1', 900))
            for name, digest in self.manifest['target_files'].items():
                self.assertEqual(service.profiles.digest((context/name).read_bytes()), digest)
            self.assertEqual(applied[context/'config.h'], 0o644)
            self.assertEqual(applied[context/'README.md'], 0o600)
            if os.name == 'posix':
                self.assertEqual(stat.S_IMODE(context.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((context/'config.h').stat().st_mode), 0o644)
                self.assertEqual(stat.S_IMODE((context/'script.sh').stat().st_mode), 0o755)
                self.assertEqual(stat.S_IMODE((self.source/'config.h').stat().st_mode), 0o600)
            return {'status': 'FAILED'}  # Stop before creating any image binding.

        with patch.object(Path, 'chmod', chmod):
            self.assertEqual(self.request(inspect)['error'], 'DRAFT_FAILED')
        self.assertEqual((self.source/'config.h').stat().st_mode, original_mode)
        self.assertEqual((self.source/'roles.secret.env').read_bytes(), b'private material')
        self.assertEqual(self.candidate.read_bytes(), b'candidate bytes')
        self.assertFalse(directory[0].exists())

    def test_drifted_c1_bytes_never_enter_builder_and_staging_is_cleaned(self):
        (self.source/'config.h').write_bytes(b'changed content')
        with self.assertRaisesRegex(ValueError, 'SOURCE_BINDING_MISMATCH'):
            self.request(lambda *args, **kwargs: self.fail('unverified source reached DRAFT'))
        self.assertFalse(list(self.job.glob('draft-context-*')))
        self.assertEqual((self.source/'config.h').read_bytes(), b'changed content')

    def test_b13_default_baked_files_and_a13_explicit_list(self):
        b13 = service.manifest('b13-level-v1')
        a13 = service.manifest('a13-tomlc99-release-1')
        self.assertEqual(set(service.baked_files(b13)), {'main.c', 'helper.c', 'config.h', 'extra.h', 'unused.h', 'Makefile'})
        self.assertEqual(set(service.baked_files(a13)), {'toml.c', 'toml.h', 'toml_extra.h', 'toml_json.c', 'Makefile'})


if __name__ == '__main__':
    unittest.main()
