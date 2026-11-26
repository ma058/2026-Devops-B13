"""Preview registration, DRAFT baseline pairing and protocol rejection boundaries."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(ROOT/'labs/e11e12/vendor'))
import member2_profiles as profiles
import member2_service as service
from draft.autobuild import prepare_candidate

REGISTRATION = ROOT/'course/e13-e14/projects'/profiles.FULL_PREVIEW_ID
ORIGINAL = (b'FROM m.daocloud.io/docker.io/library/python:3.13-slim\n'
            b'WORKDIR /work\nCOPY toml.c toml.h toml_extra.h toml_json.c Makefile ./\n'
            b'RUN make toml_json\nCMD ["./toml_json"]\n')


class FullProjectPreviewService(unittest.TestCase):
    def setUp(self):
        self.m = json.loads((REGISTRATION/'manifest.json').read_bytes())
        self.profile = self.m['profile']
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {profiles.PREVIEW_ENV: '1'}).start()

    def request(self):
        data = {key: self.m[key] for key in ('project_id', 'profile', 'profile_sha256', 'base',
                                             'target', 'candidate_sha256')}
        return dict(data, protocol=service.PROTOCOL, job_id='job-preview001',trace_id='trace-preview001')

    def test_preview_is_explicit_and_closed(self):
        self.assertEqual(service.manifest(profiles.FULL_PREVIEW_ID), self.m)
        self.assertEqual(profiles.resolve(self.profile, self.m['profile_sha256']), self.profile)
        with patch.dict(os.environ, {profiles.PREVIEW_ENV: ''}):
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_PROJECT'):
                service.manifest(profiles.FULL_PREVIEW_ID)
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_PROFILE'):
                profiles.resolve(self.profile)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_PROFILE'):
            profiles.resolve(dict(self.profile, run_argv=['make', 'all']))
        with self.assertRaisesRegex(ValueError, 'PROFILE_HASH_MISMATCH'):
            profiles.resolve(self.profile, '0'*64)

    def test_request_cannot_override_registered_inputs(self):
        good = self.request()
        self.assertEqual(service.context(good)[:2], (self.m, self.profile))
        for unknown in ('baseline', 'baseline_pair', 'dockerfile', 'image_git_blobs', 'override'):
            with self.subTest(field=unknown), self.assertRaisesRegex(ValueError, 'INVALID_REQUEST'):
                service.context(dict(good, **{unknown: 'unregistered'}))
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_MISMATCH'):
            service.context(dict(good, candidate_sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'COMMIT_MISMATCH'):
            service.context(dict(good, target=self.m['base']))

    def test_paired_bytes_only_in_staging(self):
        candidate = REGISTRATION/'candidate.Dockerfile'
        with TemporaryDirectory() as tmp:
            stage = Path(tmp)/'stage'
            stage.mkdir()
            baseline = stage/'Dockerfile.broken'
            baseline.write_bytes(ORIGINAL)
            with self.assertRaisesRegex(ValueError, 'changed required'):
                prepare_candidate(ORIGINAL.decode(), candidate.read_bytes().decode())
            frozen = service.stage_preview_pair(stage, candidate, self.m)
            self.assertEqual(frozen.read_bytes(), candidate.read_bytes())
            self.assertEqual(baseline.read_bytes(), (REGISTRATION/'Dockerfile.broken.proposed').read_bytes())
            effective = prepare_candidate(baseline.read_bytes().decode(), frozen.read_bytes().decode())
            self.assertEqual(profiles.digest(effective.encode()), self.m['baseline_pair']['Dockerfile.broken.effective'])

    def test_failed_pair_is_rejected_before_baseline_write(self):
        candidate = REGISTRATION/'candidate.Dockerfile'
        with TemporaryDirectory() as tmp:
            stage = Path(tmp)
            baseline = stage/'Dockerfile.broken'
            baseline.write_bytes(ORIGINAL)
            bad_candidate = stage/'changed'
            bad_candidate.write_bytes(candidate.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'CANDIDATE_MISMATCH'):
                service.stage_preview_pair(stage, bad_candidate, self.m)
            self.assertEqual(baseline.read_bytes(), ORIGINAL)
            baseline.write_bytes(ORIGINAL+b'\n')
            with self.assertRaisesRegex(ValueError, 'SOURCE_BINDING_MISMATCH'):
                service.stage_preview_pair(stage,candidate,self.m)
            self.assertEqual(baseline.read_bytes(), ORIGINAL+b'\n')


if __name__ == '__main__':
    unittest.main()
