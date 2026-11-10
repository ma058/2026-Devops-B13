"""Member 3: async-API idempotency under real concurrency, restart recovery,
and server-side HTTP artifact-path boundaries.

Review-fix version (2026-11-10, after member1's Request Changes):

P1 - Isolation: the HTTP tests no longer touch the real ``work/api-jobs``.
``server.ROOT`` is patched to a temporary directory and the ThreadingHTTPServer
instance is captured so it can be shut down cleanly (shutdown + server_close +
thread join). A bystander SUCCEEDED task is byte-asserted unchanged across the
whole suite, proving the server instance cannot rewrite unrelated state.

P2 - Real sentinels: the traversal and ``.git`` rejection cases now target
files that REALLY EXIST (``evidence/.git/config`` and a secret file outside
the evidence root). If someone removes the path guards from server.py, these
requests would return 200 with real content, so the tests must fail. A
mutation verification script recorded in the personal report exercises this
discriminating power against a guard-stripped copy of server.py.

P2 - Real RUNNING: a controlled RUNNING job is injected into the live store
AFTER startup (so the restart-recovery rule in Store.__init__ is not relaxed
and not triggered); the suite first asserts GET returns RUNNING, then that
artifacts answers 409 RESULT_NOT_READY.

The two earlier test groups (concurrent idempotency, restart recovery) already
run against temporary directories and are kept unchanged. The recording pool
prevents any pipeline/Docker execution.
"""
import hashlib
import json
import shutil
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
    """Server-side HTTP boundary checks against the REAL server.py handler.

    ``server.ROOT`` is redirected to a temporary directory and both the Store
    and the ThreadingHTTPServer instances are captured via subclassing, so the
    production handler code runs unmodified while the suite controls its
    lifecycle (shutdown/server_close/join) and its isolation.

    Discriminating power: sentinels below REALLY exist. Removing the
    ``is_relative_to`` guard would let traversal requests return 200 with the
    outside secret; removing the ``'.git' in path.parts`` guard would let
    ``files/.git/config`` return 200. Either mutation must fail this suite
    (verified against a guard-stripped server copy; see personal report).
    """

    SENTINEL_JOB = 'job-member3http-done-0001'
    RUNNING_JOB = 'job-member3http-running-0001'
    BYSTANDER_JOB = 'job-member3http-bystander-0001'

    @classmethod
    def setUpClass(cls):
        cls._tmp = Path(tempfile.mkdtemp(prefix='member3-http-'))
        cls.root = cls._tmp / 'work' / 'api-jobs'
        digest = hashlib.sha256(json.dumps(make_request(), sort_keys=True).encode()).hexdigest()

        # Completed sentinel job: nested artifact + a REAL .git/config sentinel
        # inside the evidence root (its existence is what makes the .git guard
        # observable rather than trivially true).
        evidence = cls.root / cls.SENTINEL_JOB / 'evidence'
        nested = evidence / 'nested'
        nested.mkdir(parents=True)
        (evidence / '.git').mkdir()
        (evidence / '.git' / 'config').write_text('[core] member3 git sentinel\n', encoding='utf-8')
        payload = b'member3 http boundary payload \xe4\xbf\xae\xe5\xa4\x8d\n'
        (nested / 'report.bin').write_bytes(payload)
        manifest = {
            'schema_version': 'e11e12-1',
            'job_id': cls.SENTINEL_JOB,
            'status': 'SUCCEEDED',
            'artifacts': [{
                'uri': f'artifact://{cls.SENTINEL_JOB}/nested/report.bin',
                'sha256': hashlib.sha256(payload).hexdigest(),
                'bytes': len(payload),
            }],
        }
        (evidence / 'result.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        write_state(cls.root, cls.SENTINEL_JOB, 'SUCCEEDED', 'member3-http-key', digest)

        # Bystander SUCCEEDED task: byte-identity asserted at teardown.
        write_state(cls.root, cls.BYSTANDER_JOB, 'SUCCEEDED', 'member3-http-bystander', digest)
        cls._bystander_state = (cls.root / cls.BYSTANDER_JOB / 'state.json').read_bytes()

        # Outside sentinel: a REAL file beyond the evidence root. Traversal
        # requests that escape the guard would serve exactly these bytes.
        cls._outside = cls._tmp / 'outside-secret.txt'
        cls._outside.write_text('server filesystem secret\n', encoding='utf-8')

        # Capture the production instances; handler code itself is untouched.
        real_httpd = server.ThreadingHTTPServer
        real_store = server.Store
        cls._captured = {}

        class CapturingHTTPServer(real_httpd):
            def __init__(self, address, handler):
                cls._captured['httpd'] = self
                super().__init__(address, handler)

        class CapturingStore(real_store):
            def __init__(self, store_root):
                cls._captured['store'] = self
                super().__init__(store_root)

        cls._patchers = [
            patch.object(server, 'ROOT', cls._tmp),
            patch.object(server, 'ThreadingHTTPServer', CapturingHTTPServer),
            patch.object(server, 'Store', CapturingStore),
        ]
        for patcher in cls._patchers:
            patcher.start()

        cls.port = free_port()
        cls._thread = threading.Thread(
            target=server.serve, kwargs={'host': '127.0.0.1', 'port': cls.port}, daemon=True)
        cls._thread.start()
        cls.base = f'http://127.0.0.1:{cls.port}'
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urlopen(cls.base + '/health', timeout=1)
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError('API test instance did not come up')

        # AFTER startup (Store.__init__ restart recovery has already run on the
        # pre-seeded SUCCEEDED jobs only), inject a controlled RUNNING job into
        # the live store. This is a job the server itself did not load, so the
        # recovery rule is neither triggered nor relaxed.
        store = cls._captured['store']
        running = {
            'schema_version': 'e11e12-1',
            'job_id': cls.RUNNING_JOB,
            'status': 'RUNNING',
            'idempotency_key': 'member3-http-running',
            'request_hash': digest,
        }
        store.jobs[cls.RUNNING_JOB] = running
        store.keys['member3-http-running'] = (digest, cls.RUNNING_JOB)
        server.save(cls.root / cls.RUNNING_JOB / 'state.json', running)
        (cls.root / cls.RUNNING_JOB / 'evidence').mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        try:
            httpd = cls._captured.get('httpd')
            if httpd is not None:
                httpd.shutdown()
                httpd.server_close()
            cls._thread.join(timeout=10)
        finally:
            for patcher in cls._patchers:
                patcher.stop()
            try:
                after = (cls.root / cls.BYSTANDER_JOB / 'state.json').read_bytes()
                if after != cls._bystander_state:
                    raise AssertionError(
                        'Bystander task state.json changed during the suite; '
                        'the HTTP tests must not rewrite unrelated tasks')
            finally:
                shutil.rmtree(cls._tmp, ignore_errors=True)

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
        with self.get(f'/v1/jobs/{self.SENTINEL_JOB}/files/nested/report.bin') as response:
            self.assertEqual(200, response.status)
            header = response.headers['X-Content-SHA256']
            data = response.read()
        manifest = json.loads(
            (self.root / self.SENTINEL_JOB / 'evidence' / 'result.json').read_text())
        entry = next(a for a in manifest['artifacts']
                     if a['uri'].endswith('nested/report.bin'))
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(digest, header, 'Body digest must equal X-Content-SHA256')
        self.assertEqual(digest, entry['sha256'], 'Body digest must equal the manifest entry')
        self.assertEqual(len(data), entry['bytes'])

    def test_traversal_to_existing_outside_file_is_rejected(self):
        # evidence = ROOT/work/api-jobs/SENTINEL/evidence -> four levels up is
        # ROOT, where outside-secret.txt REALLY exists. All forms must be 404;
        # a removed is_relative_to guard would serve the secret bytes.
        for path in (
            f'/v1/jobs/{self.SENTINEL_JOB}/files/../../../../outside-secret.txt',
            f'/v1/jobs/{self.SENTINEL_JOB}/files/%2e%2e/%2e%2e/%2e%2e/%2e%2e/outside-secret.txt',
            f'/v1/jobs/{self.SENTINEL_JOB}/files/..%2f..%2f..%2f..%2foutside-secret.txt',
            f'/v1/jobs/{self.SENTINEL_JOB}/files/nested/../../../../outside-secret.txt',
        ):
            with self.subTest(path=path):
                error = self.get_error(path)
                self.assertEqual(404, error.code)
                body = json.loads(error.read())
                self.assertEqual('NOT_FOUND', body['error'])
                self.assertIsNone(error.headers.get('X-Content-SHA256'),
                                  'Rejected paths must not expose content hashes')

    def test_git_path_with_real_file_is_rejected(self):
        # .git/config REALLY exists under the evidence root; only the guard
        # can produce this 404.
        for path in (
            f'/v1/jobs/{self.SENTINEL_JOB}/files/.git/config',
            f'/v1/jobs/{self.SENTINEL_JOB}/files/%2egit/config',
        ):
            with self.subTest(path=path):
                error = self.get_error(path)
                self.assertEqual(404, error.code)
                body = json.loads(error.read())
                self.assertEqual('NOT_FOUND', body['error'])
                self.assertIsNone(error.headers.get('X-Content-SHA256'))

    def test_missing_paths_are_rejected(self):
        for path in (
            f'/v1/jobs/{self.SENTINEL_JOB}/files/no-such-file.json',
            f'/v1/jobs/{self.SENTINEL_JOB}/files/',
        ):
            with self.subTest(path=path):
                self.assertEqual(404, self.get_error(path).code)

    def test_unknown_job_is_not_found(self):
        self.assertEqual(404, self.get_error('/v1/jobs/job-member3-does-not-exist').code)
        self.assertEqual(404, self.get_error('/v1/jobs/').code)

    def test_running_job_reports_running_then_result_not_ready(self):
        # The controlled RUNNING job was injected after startup: GET must show
        # the real RUNNING status first...
        with self.get(f'/v1/jobs/{self.RUNNING_JOB}') as response:
            self.assertEqual(200, response.status)
            state = json.loads(response.read())
        self.assertEqual('RUNNING', state['status'])
        self.assertEqual(self.RUNNING_JOB, state['job_id'])
        # ...and its artifacts must answer 409 RESULT_NOT_READY, distinct from
        # both 404 and any terminal-failure semantics.
        error = self.get_error(f'/v1/jobs/{self.RUNNING_JOB}/artifacts')
        self.assertEqual(409, error.code)
        body = json.loads(error.read())
        self.assertEqual('RESULT_NOT_READY', body['error'])


if __name__ == '__main__':
    unittest.main()
