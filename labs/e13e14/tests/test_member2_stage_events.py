"""Local HTTP, fault-boundary and report contracts. Docker runs have separate evidence."""
import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import member2_profiles as profiles
import member2_service as service
from member2_faults import fault_environment


class StageEvents(unittest.TestCase):
    ids = {'job_id': 'job-12345678', 'trace_id': 'trace-12345678'}

    def exchange(self, path, body, *, authorized=True):
        # One real HTTP exchange. The handler and all request validation are live.
        credential = os.urandom(24).hex()
        encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
        headers = {'X-E14-Token': credential if authorized else 'untrusted'}
        stream = io.StringIO()
        with patch.dict(os.environ, {'E14_TOKEN': credential}), contextlib.redirect_stdout(stream):
            with service.HTTPServer(('127.0.0.1', 0), service.Handler) as server:
                worker = threading.Thread(target=server.handle_request, daemon=True)
                worker.start()
                client = http.client.HTTPConnection(*server.server_address, timeout=5)
                try:
                    client.request('POST', path, body=encoded, headers=headers)
                    response = client.getresponse()
                    decoded = json.loads(response.read())
                finally:
                    client.close()
                    worker.join(timeout=5)
                self.assertFalse(worker.is_alive())
        text = stream.getvalue()
        self.assertNotIn(credential, text)
        self.assertNotIn('private-detail', text)
        self.assertEqual(len(text.splitlines()), 1)
        event = json.loads(text)
        self.assertEqual(event['protocol'], service.PROTOCOL)
        self.assertEqual(event['http_status'], response.status)
        self.assertGreaterEqual(event['elapsed_ms'], 0)
        return decoded, event

    def test_worker_and_role_share_identity_and_report_separate_stage_outcomes(self):
        outcomes = (
            ('/v1/run', 'draft', 'run', 'draft', {'status': 'SUCCEEDED'}, 'SUCCEEDED', None),
            ('/v1/worker', 'draft', 'broker', 'scan', {'status': 'SUCCEEDED'}, 'SUCCEEDED', None),
            ('/v1/worker', 'draft', 'broker', 'validate',
             {'status': 'SUCCEEDED', 'payload': {'accepted': False}}, 'REJECTED', 'VALIDATION_REJECTED'),
            ('/v1/run', 'mdfixer', 'run', 'validate', {'status': 'REJECTED'}, 'REJECTED', 'VALIDATION_REJECTED'),
            ('/v1/run', 'buildchecker', 'run', 'full',
             {'status': 'TIMED_OUT', 'error': 'private-detail'}, 'TIMED_OUT', 'TIMEOUT'),
            ('/v1/run', 'buildchecker', 'run', 'full',
             {'status': 'FAILED', 'error': 'DOCKER_COMMAND_FAILED:/private-detail'}, 'FAILED', 'DOCKER_COMMAND_FAILED'),
        )
        for endpoint, role, method, stage, result, status, code in outcomes:
            with self.subTest(role=role, stage=stage, status=status), patch.object(service, 'ROLE', role), \
                 patch.object(service, method, return_value=result):
                body, event = self.exchange(endpoint, dict(self.ids, operation=stage, unused='private-detail'))
                self.assertEqual(body, result)
                self.assertEqual((event['role'], event['stage'], event['status'], event['error_code']),
                                 (role, stage, status, code))
                self.assertEqual((event['endpoint'], event['http_status']), (endpoint, 200))
                self.assertEqual((event['job_id'], event['trace_id']), tuple(self.ids.values()))

    def test_protocol_rejection_is_correlated(self):
        with patch.object(service, 'ROLE', 'echecker'):
            response, event = self.exchange('/v1/run', self.ids)
        self.assertEqual(response['error'], 'PROTOCOL_REQUIRED')
        self.assertEqual((event['http_status'], event['status'], event['error_code']),
                         (422, 'REJECTED', 'PROTOCOL_REQUIRED'))
        self.assertEqual(event['job_id'], self.ids['job_id'])

    def test_exceptions_and_untrusted_request_data_are_redacted(self):
        for problem, outcome, code in ((RuntimeError('/private-detail'), 'FAILED', 'INTERNAL_ERROR'),
                                       (TimeoutError('private-detail'), 'TIMED_OUT', 'TIMEOUT')):
            with self.subTest(error=code), patch.object(service, 'ROLE', 'draft'), \
                 patch.object(service, 'run', side_effect=problem):
                response, event = self.exchange('/v1/run', dict(self.ids, job_id='private-detail'))
                self.assertEqual((event['job_id'], event['trace_id']), (None, self.ids['trace_id']))
                self.assertEqual((event['status'], event['error_code']), (outcome, code))
                self.assertEqual(response['error_code'], code)
                self.assertIsNone(response['job_id'])

    def test_route_auth_and_decode_do_not_echo_unverified_input(self):
        with patch.object(service, 'ROLE', 'draft'), patch.object(service, 'run') as run:
            for path, body, authorized, stage, code in (
                ('/v1/run?private-detail', self.ids, True, 'route', 'NOT_FOUND'),
                ('/v1/run', self.ids, False, 'authenticate', 'FORBIDDEN'),
                ('/v1/run', b'private-detail', True, 'decode', 'INVALID_JSON'),
            ):
                with self.subTest(stage=stage):
                    _, event = self.exchange(path, body, authorized=authorized)
                    self.assertEqual((event['stage'], event['error_code']), (stage, code))
                    self.assertEqual((event['job_id'], event['trace_id']), (None, None))
            run.assert_not_called()


class FaultPatchBoundary(unittest.TestCase):
    def test_broker_accepts_only_fixed_bad_bytes_in_explicit_c5(self):
        with tempfile.TemporaryDirectory() as name, contextlib.ExitStack() as stack:
            job = Path(name)
            m = {'profile_sha256': 'profile-digest', 'target_files': {}}
            data = dict(StageEvents.ids, operation='validate', patchfile=str(job/'input.patch'), fault_patch=True)
            stack.enter_context(patch.object(service, 'ROLE', 'draft'))
            stack.enter_context(patch.object(service, 'context', return_value=(m, {}, job)))
            stack.enter_context(patch.object(service, 'load_binding', return_value=({'image_id': 'bound'}, job/'state')))
            stack.enter_context(patch.object(service, 'output', return_value=job/'out'))
            stack.enter_context(patch.object(service, 'project', return_value=job/'target'))
            stack.enter_context(patch.object(service, 'report_payload', return_value={}))
            stack.enter_context(patch.object(profiles, 'patch', return_value=('audited change', [])))
            execute = stack.enter_context(patch.object(service, 'execute', return_value={'status': 'FAILED'}))
            for scenario, content, error in (
                ('normal', service.INVALID_PATCH, 'FAULT_DISABLED'),
                ('C4', service.INVALID_PATCH, 'FAULT_DISABLED'),
                ('C5', b'other contents', 'UNSAFE_PATCH'),
                ('C5', service.INVALID_PATCH, None),
            ):
                with self.subTest(scenario=scenario, error=error), patch.dict(os.environ, fault_environment('draft', scenario)):
                    Path(data['patchfile']).write_bytes(content)
                    data['patch_sha256'] = profiles.digest(content)
                    if error:
                        with self.assertRaisesRegex(ValueError, error):
                            service.broker(data)
                        execute.assert_not_called()
                    else:
                        service.broker(data)
                        execute.assert_called_once()


class FullReportScope(unittest.TestCase):
    def collect(self, report):
        profile = profiles.resolve(profiles.legacy.PROFILE)
        fake = types.SimpleNamespace(full_check=Mock(return_value=report))
        with tempfile.TemporaryDirectory() as name, patch.dict(sys.modules, {'fullcheck': fake}), \
             patch.object(profiles, 'check'):
            path = Path(name)
            result = profiles.full(path, path, profile, 120)
            self.assertEqual(result, json.loads((path/'findings.json').read_bytes()))
        return result

    def test_tomlc99_outside_missing_survives_scoped_zero(self):
        outside = {'type': 'MISSING', 'target': 'toml_json', 'dependency': 'toml.h', 'detail': 'retain'}
        inside = {'type': 'REDUNDANT', 'target': 'toml.o', 'dependency': 'extra.h'}
        result = self.collect({'status': 'SUCCEEDED', 'findings': [outside, inside]})
        self.assertEqual(result['success_scope'], ['toml.o'])
        self.assertEqual(result['profile_sha256'], '0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1')
        self.assertEqual(result['whole_project_findings'], [outside, inside])
        self.assertEqual(result['findings'], result['whole_project_findings'])
        self.assertEqual(result['findings_by_scope'],
                         {'in_scope': [inside], 'out_of_scope': [outside], 'in_scope_missing': 0, 'out_of_scope_missing': 1})

    def test_failed_check_never_produces_missing_counts(self):
        for status in ('FAILED', 'TIMED_OUT'):
            with self.subTest(status=status):
                self.assertIsNone(self.collect({'status': status, 'findings': []})['findings_by_scope'])
        with self.assertRaisesRegex(ValueError, 'INVALID_FULL_FINDINGS'):
            self.collect({'status': 'SUCCEEDED'})
        with self.assertRaisesRegex(ValueError, 'INVALID_FULL_FINDINGS'):
            self.collect({'status': 'SUCCEEDED', 'findings': [{'type': 'unknown', 'target': 'toml.o', 'dependency': 'toml.h'}]})


if __name__ == '__main__':
    unittest.main()
