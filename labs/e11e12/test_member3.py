"""Member 3: async-API idempotency under real concurrency, restart recovery,
and server-side HTTP artifact-path boundaries.

Differentiation from existing suites (38 tests):
- test_contract.test_same_key_same_request_same_job submits the same key twice
  sequentially; here N threads hit submit() simultaneously behind a barrier.
- test_member1_api_client.py exercises the *client* download-path guard in
  course/e11-e12/api_probe.py; here the *server* HTTP layer is tested over a
  real socket: encoded traversal, .git access, unknown jobs, RESULT_NOT_READY,
  and byte/header/manifest three-way SHA agreement.
- Restart recovery: Store.__init__ semantics for interrupted vs completed jobs
  plus idempotency-key mapping restoration and evidence preservation.

No pipeline execution is triggered: the thread pool is replaced by a recorder,
so these tests stay fast and never touch Docker.
"""
import hashlib
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pipeline
import server


class RecordingPool:
    """Executor stub recording submissions without running any work."""

    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        with self.lock:
            self.calls.append((fn, args, kwargs))

    def shutdown(self):
        pass


def make_request():
    # Repo path must stay under ROOT/data to pass Store.submit validation.
    return {
        'mode': 'e12',
        'repo': str(pipeline.ROOT / 'data' / 'member3-test-repo'),
        'base': 'a' * 40,
        'target': 'b' * 40,
    }


def write_state(root, job_id, status, key, digest):
    folder = root / job_id
    folder.mkdir(parents=True, exist_ok=True)
    state = {
        'schema_version': 'e11e12-1',
        'job_id': job_id,
        'status': status,
        'idempotency_key': key,
        'request_hash': digest,
    }
    server.save(folder / 'state.json', state)
    return state


class Member3ConcurrentIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'jobs'

    def test_concurrent_same_key_yields_single_job_and_single_enqueue(self):
        store = server.Store(self.root)
        store.pool = RecordingPool()
        request = make_request()
        barrier = threading.Barrier(8)
        results, errors = [], []

        def hit():
            try:
                barrier.wait()
                results.append(store.submit(request, 'member3-concurrent-key'))
            except Exception as exc:  # pragma: no cover - only on defect
                errors.append(exc)

        threads = [threading.Thread(target=hit) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual([], errors)
        self.assertEqual(8, len(results))
        job_ids = {state['job_id'] for state in results}
        self.assertEqual(1, len(job_ids), 'All responses must share one job_id')
        self.assertEqual(1, len(store.pool.calls),
                         'Exactly one background build may be enqueued')
        job_dirs = [p for p in self.root.iterdir() if p.is_dir()]
        self.assertEqual(1, len(job_dirs), 'No duplicate task directories')
        self.assertEqual(1, len(store.keys), 'One idempotency mapping only')

    def test_concurrent_distinct_keys_each_enqueue_once(self):
        store = server.Store(self.root)
        store.pool = RecordingPool()
        request = make_request()
        barrier = threading.Barrier(8)
        results, errors = [], []

        def hit(index):
            try:
                barrier.wait()
                results.append(store.submit(request, f'member3-key-{index}'))
            except Exception as exc:  # pragma: no cover - only on defect
                errors.append(exc)

        threads = [threading.Thread(target=hit, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual([], errors)
        self.assertEqual(8, len({state['job_id'] for state in results}))
        self.assertEqual(8, len(store.pool.calls))
        self.assertEqual(8, len([p for p in self.root.iterdir() if p.is_dir()]))


class Member3RestartRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'jobs'
        self.root.mkdir(parents=True)

    def test_interrupted_jobs_become_failed_and_persist_on_disk(self):
        digest = hashlib.sha256(json.dumps(make_request(), sort_keys=True).encode()).hexdigest()
        write_state(self.root, 'job-queued-1', 'QUEUED', 'k1', digest)
        write_state(self.root, 'job-running-1', 'RUNNING', 'k2', digest)

        store = server.Store(self.root)

        for job_id in ('job-queued-1', 'job-running-1'):
            state = store.jobs[job_id]
            self.assertEqual('FAILED', state['status'])
            self.assertEqual('SERVER_RESTARTED', state['error']['code'])
            on_disk = json.loads((self.root / job_id / 'state.json').read_text())
            self.assertEqual('FAILED', on_disk['status'])
            self.assertEqual('SERVER_RESTARTED', on_disk['error']['code'])
        # Original evidence directories are preserved, not deleted.
        self.assertTrue((self.root / 'job-queued-1').is_dir())
        self.assertTrue((self.root / 'job-running-1').is_dir())

    def test_completed_job_survives_restart_and_key_mapping_is_restored(self):
        digest = hashlib.sha256(json.dumps(make_request(), sort_keys=True).encode()).hexdigest()
        done = write_state(self.root, 'job-done-1', 'SUCCEEDED', 'member3-done-key', digest)

        store = server.Store(self.root)
        self.assertEqual('SUCCEEDED', store.jobs['job-done-1']['status'])

        store.pool = RecordingPool()
        again = store.submit(make_request(), 'member3-done-key')
        self.assertEqual(done['job_id'], again['job_id'])
        self.assertEqual([], store.pool.calls,
                         'A completed key must resolve from the store without re-enqueue')

    def test_new_key_after_restart_starts_fresh_job_and_keeps_old_evidence(self):
        digest = hashlib.sha256(json.dumps(make_request(), sort_keys=True).encode()).hexdigest()
        write_state(self.root, 'job-old-1', 'FAILED', 'old-key', digest)

        store = server.Store(self.root)
        store.pool = RecordingPool()
        retried = store.submit(make_request(), 'member3-new-key')

        self.assertNotEqual('job-old-1', retried['job_id'])
        self.assertEqual(1, len(store.pool.calls), 'Retry must enqueue exactly one new job')
        self.assertEqual('FAILED', store.jobs['job-old-1']['status'])
        self.assertTrue((self.root / 'job-old-1' / 'state.json').is_file(),
                        'Old evidence stays for the audit trail')


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Member3HttpBoundaryTests(unittest.TestCase):
    """Server-side HTTP layer on a real socket; evidence staged on disk."""

    JOB_DONE = 'job-member3http-done-0001'
    JOB_RUNNING = 'job-member3http-running-0001'

    @classmethod
    def setUpClass(cls):
        cls.jobs_root = pipeline.ROOT / 'work' / 'api-jobs'
        cls.jobs_root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(json.dumps(make_request(), sort_keys=True).encode()).hexdigest()

        # Completed job with a manifest and a nested artifact.
        done = cls.jobs_root / cls.JOB_DONE
        evidence = done / 'evidence' / 'nested'
        evidence.mkdir(parents=True, exist_ok=True)
        payload = b'member3 http boundary payload \xe4\xbf\xae\xe5\xa4\x8d\n'
        (evidence / 'report.bin').write_bytes(payload)
        manifest = {
            'schema_version': 'e11e12-1',
            'job_id': cls.JOB_DONE,
            'status': 'SUCCEEDED',
            'artifacts': [{
                'uri': f'artifact://{cls.JOB_DONE}/nested/report.bin',
                'sha256': hashlib.sha256(payload).hexdigest(),
                'bytes': len(payload),
            }],
        }
        (done / 'evidence' / 'result.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        write_state(cls.jobs_root, cls.JOB_DONE, 'SUCCEEDED', 'member3-http-key', digest)

        # Running job: state only, no result.json yet -> artifacts must 409.
        write_state(cls.jobs_root, cls.JOB_RUNNING, 'RUNNING', 'member3-http-running', digest)

        cls.port = free_port()
        cls.thread = threading.Thread(
            target=server.serve, kwargs={'host': '127.0.0.1', 'port': cls.port}, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.port}'
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                urlopen(cls.base + '/health', timeout=1)
                return
            except OSError:
                time.sleep(0.1)
        raise AssertionError('API test instance did not come up')

    @classmethod
    def tearDownClass(cls):
        for job_id in (cls.JOB_DONE, cls.JOB_RUNNING):
            folder = cls.jobs_root / job_id
            if folder.is_dir():
                for path in sorted(folder.rglob('*'), reverse=True):
                    if path.is_file() or path.is_symlink():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()
                folder.rmdir()

    def get(self, path):
        return urlopen(Request(self.base + path), timeout=5)

    def get_error(self, path):
        try:
            self.get(path)
        except HTTPError as error:
            return error
        raise AssertionError(f'GET {path} should have failed')

    def test_health_reports_schema(self):
        with self.get('/health') as response:
            self.assertEqual(200, response.status)
            body = json.loads(response.read())
        self.assertEqual('e11e12-1', body['schema_version'])

    def test_download_bytes_header_and_manifest_agree(self):
        with self.get(f'/v1/jobs/{self.JOB_DONE}/files/nested/report.bin') as response:
            self.assertEqual(200, response.status)
            header = response.headers['X-Content-SHA256']
            data = response.read()
        manifest = json.loads(
            (self.jobs_root / self.JOB_DONE / 'evidence' / 'result.json').read_text())
        entry = next(a for a in manifest['artifacts']
                     if a['uri'].endswith('nested/report.bin'))
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(digest, header, 'Body digest must equal X-Content-SHA256')
        self.assertEqual(digest, entry['sha256'], 'Body digest must equal the manifest entry')
        self.assertEqual(len(data), entry['bytes'])

    def test_encoded_traversal_is_rejected(self):
        # The %-encoded forms reach the server's own path check unchanged;
        # the plain '../..' form is normalised by urllib before it is sent,
        # so that request must also be refused, whatever it resolves to.
        for path in (
            f'/v1/jobs/{self.JOB_DONE}/files/%2e%2e/%2e%2e/etc/passwd',
            f'/v1/jobs/{self.JOB_DONE}/files/nested/../../etc/hostname',
            f'/v1/jobs/{self.JOB_DONE}/files/%2e%2e%2f%2e%2e%2fsecret',
        ):
            with self.subTest(path=path):
                error = self.get_error(path)
                self.assertEqual(404, error.code)
                body = json.loads(error.read())
                self.assertEqual('NOT_FOUND', body['error'])
                leaked = error.headers.get('X-Content-SHA256')
                self.assertIsNone(leaked, 'Rejected paths must not expose content hashes')

    def test_git_and_missing_paths_are_rejected(self):
        for path in (
            f'/v1/jobs/{self.JOB_DONE}/files/.git/config',
            f'/v1/jobs/{self.JOB_DONE}/files/nested/.git/HEAD',
            f'/v1/jobs/{self.JOB_DONE}/files/no-such-file.json',
            f'/v1/jobs/{self.JOB_DONE}/files/',
        ):
            with self.subTest(path=path):
                self.assertEqual(404, self.get_error(path).code)

    def test_unknown_job_is_not_found(self):
        self.assertEqual(404, self.get_error('/v1/jobs/job-member3-does-not-exist').code)
        self.assertEqual(404, self.get_error('/v1/jobs/').code)

    def test_running_job_artifacts_are_result_not_ready(self):
        error = self.get_error(f'/v1/jobs/{self.JOB_RUNNING}/artifacts')
        self.assertEqual(409, error.code)
        body = json.loads(error.read())
        self.assertEqual('RESULT_NOT_READY', body['error'])


if __name__ == '__main__':
    unittest.main()
