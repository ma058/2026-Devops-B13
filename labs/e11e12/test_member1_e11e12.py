"""Member 1 independent boundary checks; no Docker success is mocked here.

Git/GCC tests exercise the retained B13 E8-E10 implementation. Store tests
reconstruct persisted classroom states without launching background jobs.
These are unit/contract tests, separate from the real Docker evidence driver.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pipeline
import server
from lab import commit, fixture, patch, run, scan


class Member1IntegrationBoundaries(unittest.TestCase):
    def test_macro_two_headers_repair_definition_preserve_rule_recipe_and_rd(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / 'project'
            fixture(project, 'macro')
            (project / 'main.c').write_text('#include "extra.h"\n' + (project / 'main.c').read_text())
            commit(project, 'C1 second actual include')
            original = (project / 'Makefile').read_text()
            report = scan(project)
            self.assertEqual({(f['type'], f['target'], f['dependency']) for f in report['findings']}, {
                ('MISSING', 'main.o', 'config.h'), ('MISSING', 'main.o', 'extra.h'),
                ('REDUNDANT', 'main.o', 'unused.h')})
            diff, plan = patch(project, report)
            self.assertEqual(plan, [
                {'target': 'main.o', 'dependency': 'config.h', 'style': 'macro'},
                {'target': 'main.o', 'dependency': 'extra.h', 'style': 'macro'}])
            candidate = Path(temporary) / 'candidate.patch'
            candidate.write_text(diff)
            run(['git', 'apply', '--check', str(candidate)], project)
            self.assertEqual((project / 'Makefile').read_text(), original)
            run(['git', 'apply', str(candidate)], project)
            expected = original.replace('DEPS = main.c unused.h\n',
                                        'DEPS = main.c unused.h config.h extra.h\n')
            self.assertEqual((project / 'Makefile').read_text(), expected)

    def test_true_old_report_rejected_without_relabeling_or_source_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / 'project'
            fixture(project, 'macro')
            old = scan(project)
            old_bytes = json.dumps(old, sort_keys=True).encode()
            (project / 'main.c').write_text('#include "extra.h"\n' + (project / 'main.c').read_text())
            target = commit(project, 'C1 real dependency change')
            self.assertNotEqual(old['commit'], target)
            before = (project / 'Makefile').read_bytes()
            with self.assertRaisesRegex(ValueError, '^STALE_REPORT$'):
                patch(project, old)
            self.assertEqual((project / 'Makefile').read_bytes(), before)
            self.assertEqual(json.dumps(old, sort_keys=True).encode(), old_bytes)

    def test_even_semantically_equal_json_with_changed_bytes_fails_transfer_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / 'report.json'
            initial = b'{"commit":"a","status":"SUCCEEDED"}\n'
            artifact.write_bytes(initial)
            digest = hashlib.sha256(initial).hexdigest()
            self.assertEqual(pipeline.load_artifact(artifact, digest)['status'], 'SUCCEEDED')
            artifact.write_bytes(b'{ "commit": "a", "status": "SUCCEEDED" }\n')
            self.assertEqual(json.loads(initial), json.loads(artifact.read_bytes()))
            with self.assertRaises(pipeline.Failure) as raised:
                pipeline.load_artifact(artifact, digest)
            self.assertEqual(raised.exception.code, 'ARTIFACT_HASH_MISMATCH')

    def test_restart_retains_completed_job_and_same_input_different_key_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobs = Path(temporary) / 'jobs'
            request = {'mode': 'e11-b', 'repo': str(pipeline.ROOT / 'data' / 'persisted'),
                       'base': 'a' * 40, 'target': 'b' * 40}
            digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            state = {'schema_version': 'e11e12-1', 'job_id': 'job-finished',
                     'status': 'SUCCEEDED', 'idempotency_key': 'finished-key',
                     'request_hash': digest, 'trace_id': 'trace-original'}
            pipeline.save(jobs / 'job-finished' / 'state.json', state)
            store = server.Store(jobs)
            try:
                repeated = store.submit(dict(reversed(list(request.items()))), 'finished-key')
                self.assertEqual(repeated, state)
                self.assertEqual(set(store.jobs), {'job-finished'})
                self.assertFalse((jobs / 'job-finished' / 'evidence').exists())
            finally:
                store.pool.shutdown()

    def test_restart_marks_unfinished_job_failed_preserves_idempotency_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobs = Path(temporary) / 'jobs'
            request = {'mode': 'e11-b', 'repo': str(pipeline.ROOT / 'data' / 'interrupted'),
                       'base': 'a' * 40, 'target': 'b' * 40}
            digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            pipeline.save(jobs / 'job-interrupted' / 'state.json', {
                'schema_version': 'e11e12-1', 'job_id': 'job-interrupted', 'status': 'RUNNING',
                'idempotency_key': 'interrupted-key', 'request_hash': digest})
            store = server.Store(jobs)
            try:
                state = store.submit(request, 'interrupted-key')
                self.assertEqual(state['job_id'], 'job-interrupted')
                self.assertEqual(state['status'], 'FAILED')
                self.assertEqual(state['error']['code'], 'SERVER_RESTARTED')
                self.assertEqual(set(store.jobs), {'job-interrupted'})
                persisted = json.loads((jobs / 'job-interrupted' / 'state.json').read_text())
                self.assertEqual(persisted, state)
            finally:
                store.pool.shutdown()


if __name__ == '__main__':
    unittest.main()
