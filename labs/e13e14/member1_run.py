"""Real C1/C2/C3/C8 preparatory runs on a controlled course fixture.

Run inside the non-root E11-E12 Linux image with its usual Docker/strace
permissions, source at /course (read-only), data and work writable:
  python3 labs/e13e14/member1_run.py --request data/NAME/e12.json --out work/NEW

The local E11-A implementation supplies LOCAL_SIMULATED_A reports. This is
neither an A13 client session nor the formal cross-group E13 matrix. No detector,
compiler, DRAFT image execution or HTTP job outcome is mocked by this driver.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e11e12'), str(ROOT / 'course/e11-e12')]
import pipeline
from api_probe import safe_download_target
from handoff_a_to_b import make_handoff

SOURCE_LABEL = 'LOCAL_SIMULATED_A'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def command(argv, cwd=ROOT):
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=30)
    require(completed.returncode == 0, repr(argv) + ': ' + completed.stderr.decode(errors='replace'))
    return completed.stdout


def source_bytes(project):
    names = command(['git', 'ls-files', '-z'], project).split(b'\0')
    result = {}
    for raw in names:
        if not raw:
            continue
        name = raw.decode('utf-8')
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe tracked path')
        path = project.joinpath(*relative.parts)
        require(not path.is_symlink() and path.resolve().is_relative_to(project.resolve()),
                'Unsupported source symbolic link')
        result[name] = path.read_bytes()
    return result


def source_snapshot(project, destination):
    files = source_bytes(project)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    pipeline.save(destination / 'sha256.json', {name: digest(data) for name, data in files.items()})
    return files


def verify_manifest(result, out):
    checks, seen = [], set()
    prefix = 'artifact://' + result['job_id'] + '/'
    references = result.get('artifacts')
    require(isinstance(references, list) and bool(references), 'Expected nonempty artifact list')
    for item in references:
        require(isinstance(item, dict), 'Artifact reference must be an object')
        uri = item['uri']
        require(isinstance(uri, str) and uri.startswith(prefix), 'Foreign artifact job')
        relative = uri[len(prefix):]
        require(relative not in seen, 'Duplicate artifact URI')
        seen.add(relative)
        path = safe_download_target(out, relative)
        content = path.read_bytes()
        require(type(item['bytes']) is int and len(content) == item['bytes'], 'Artifact size mismatch')
        require(digest(content) == item['sha256'], 'Artifact hash mismatch')
        checks.append({'path': relative, 'sha256': item['sha256'], 'bytes': len(content)})
    require(bool(checks), 'Expected actual pipeline artifacts')
    return checks


def verify_c8_downloads(result, request, downloads):
    """Bind every downloaded stage to the final manifest and requested commits."""
    require(result.get('schema_version') == 'e11e12-1' and result.get('status') == 'SUCCEEDED',
            'C8 result schema or status differs')
    require(result.get('base_commit') == request['base'] and result.get('target_commit') == request['target'],
            'C8 result commits differ from request')
    checks = verify_manifest(result, downloads)
    references = {item['uri']: item for item in result['artifacts']}
    stages = result.get('stages')
    require(isinstance(stages, list) and all(isinstance(item, dict) for item in stages)
            and [item.get('name') for item in stages] == ['full-check', 'incremental-check'],
            'C8 must contain the two E11-A stages')

    def check_reference(ref):
        require(isinstance(ref, dict) and type(ref.get('bytes')) is int, 'Invalid stage artifact reference')
        actual = references.get(ref.get('uri'))
        require(actual is not None and actual.get('sha256') == ref.get('sha256')
                and actual.get('bytes') == ref.get('bytes'), 'Stage artifact missing or different in manifest')

    verified_stages = []
    for item in stages:
        name = item['name']
        ref = item.get('artifact')
        check_reference(ref)
        relative = name + '.json'
        require(ref['uri'] == 'artifact://' + result['job_id'] + '/' + relative,
                'Unexpected stage artifact path')
        envelope = json.loads(safe_download_target(downloads, relative).read_bytes())
        require(isinstance(envelope, dict), 'Stage envelope must be an object')
        require(envelope.get('job_id') == result['job_id']
                and envelope.get('trace_id') == result['trace_id'], 'Downloaded stage task identity differs')
        commit = request['base'] if name == 'full-check' else request['target']
        pipeline.check_envelope(envelope, commit, name)
        nested = envelope.get('artifacts')
        require(isinstance(nested, list), 'Stage references must be an array')
        for nested_ref in nested:
            check_reference(nested_ref)
        verified_stages.append({'name': name, 'sha256': ref['sha256'], 'commit': commit,
                                'job_id': envelope['job_id'], 'trace_id': envelope['trace_id']})
    return {'files_verified': len(checks), 'stages_verified': verified_stages}


def cleanup_server_group(process, timeout=5):
    """Observe/stop only the private start_new_session process group.

    Parent exit is checked separately from group absence. A descendant which
    creates a different process group is outside this observation's scope.
    """
    pgid = process.pid
    require(pgid > 1 and pgid != os.getpgrp(), 'Refuse to signal the caller process group')
    actions, errors = [], []

    def present():
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError as exc:
            errors.append(str(exc))
            return None

    def send(sig):
        try:
            os.killpg(pgid, sig)
            actions.append(int(sig))
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            errors.append(str(exc))

    def wait_absent():
        deadline = time.monotonic() + timeout
        while True:
            process.poll()  # Reap the parent, including when it exited first.
            exists = present()
            if exists is not True or time.monotonic() >= deadline:
                return exists
            time.sleep(0.05)

    parent_exited_before = process.poll() is not None
    initial = present()
    if initial is True:
        send(signal.SIGTERM)
        if wait_absent() is True:
            send(getattr(signal, 'SIGKILL', 9))
            wait_absent()
    parent_stopped = process.poll() is not None
    final = present()
    return {'pid': pgid, 'process_group_id': pgid, 'private_process_group_only': True,
            'parent_exited_before_cleanup': parent_exited_before,
            'parent_stopped': parent_stopped, 'process_exit_code': process.returncode,
            'process_group_present_before': initial,
            'process_group_absent_at_observation': None if final is None else not final,
            'observation_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'signals_sent': actions, 'errors': errors,
            'scope': 'Original private process group only; escaped descendants are not proven stopped'}


def verify_success(result, out, request):
    require(result['status'] == 'SUCCEEDED', 'Pipeline failed: ' + str(result.get('error')))
    names = ['full-check', 'incremental-check'] if request['mode'] == 'e11-a' else [
        'draft', 'fixed-md', 'repair', 'recheck']
    require([item['name'] for item in result['stages']] == names, 'Unexpected stage sequence')
    for name in names:
        envelope = json.loads((out / (name + '.json')).read_bytes())
        require(envelope['job_id'] == result['job_id'] and envelope['trace_id'] == result['trace_id'],
                'Stage task identity mismatch')
        pipeline.check_envelope(envelope, request['base'] if name == 'full-check' else request['target'], name)
    checks = verify_manifest(result, out)
    if request['mode'] == 'e11-b':
        require(result.get('execution_environment') == 'draft-image'
                and result.get('draft_image_reused') is True, 'DRAFT image was not actually reused')
        require([item['operation'] for item in result['image_operations']] == ['validate', 'full'],
                'Expected actual immutable-image validation and recheck')
        verdict = json.loads((out / 'validation/validation.json').read_bytes())
        require(verdict['accepted'] is True and verdict.get('error') is None
                and set(verdict['checks']) == {'patch_applies', 'build', 'test', 'header_change', 'no_missing'}
                and all(value is True for value in verdict['checks'].values()), 'Validation incomplete')
        findings = json.loads((out / 'final-full/findings.json').read_bytes())['findings']
        require(not any(item['type'] == 'MISSING' for item in findings), 'Recheck still has missing dependencies')
        require(any(item['type'] == 'REDUNDANT' and item['dependency'] == 'unused.h' for item in findings),
                'Expected controlled fixture redundant dependency absent')
    pipeline.save(out.parent / (out.name + '-artifact-checks.json'), checks)
    return {'status': result['status'], 'job_id': result['job_id'], 'trace_id': result['trace_id'],
            'artifacts_verified': len(checks)}


def run_api_server(store, ready):
    """Start the unchanged E12 handler, recording its OS-assigned loopback port.

    This lifecycle subclass only exposes the selected address. Store.submit,
    pipeline.execute, HTTP handlers and worker behavior remain unmodified.
    """
    import server
    original = server.ThreadingHTTPServer

    class RecordingServer(original):
        def server_activate(self):
            super().server_activate()
            pipeline.save(ready, {'host': '127.0.0.1', 'port': self.server_address[1]})

    server.ThreadingHTTPServer = RecordingServer
    server.serve(host='127.0.0.1', port=0, store_root=store)


def http_exchange(base, path, out, name, body=None):
    raw_request = None if body is None else json.dumps(body).encode('utf-8')
    if raw_request is not None:
        (out / (name + '.request.json')).write_bytes(raw_request)
    request = Request(base + path, data=raw_request, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=30) as response:
            status, headers, content = response.status, dict(response.headers), response.read()
    except HTTPError as response:
        status, headers, content = response.code, dict(response.headers), response.read()
    (out / (name + '.response.bin')).write_bytes(content)
    pipeline.save(out / (name + '.http.json'), {
        'method': 'GET' if body is None else 'POST', 'url': base + path,
        'status': status, 'headers': headers, 'response_sha256': digest(content)})
    return status, headers, content


def run_c8(request, out, timeout):
    """Real isolated loopback HTTP; finish worker before terminating its server."""
    out.mkdir(parents=True, exist_ok=False)
    ready, store = out / 'server-ready.json', out / 'store'
    argv = [sys.executable, '-u', str(Path(__file__).resolve()), '--serve-store', str(store),
            '--ready-file', str(ready)]
    pipeline.save(out / 'server-command.json', {'argv': argv, 'scope': 'isolated E12 API, not E14 /v1/run'})
    completed_job, summary = False, None
    with (out / 'server.stdout.log').open('wb') as stdout, (out / 'server.stderr.log').open('wb') as stderr:
        process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while not ready.exists():
                require(process.poll() is None, 'Private HTTP server exited during startup')
                require(time.monotonic() < deadline, 'Private HTTP server startup timed out')
                time.sleep(0.1)
            address = json.loads(ready.read_bytes())
            base = 'http://127.0.0.1:' + str(address['port'])
            status, _, raw = http_exchange(base, '/health', out, 'health')
            require(status == 200 and json.loads(raw)['status'] == 'ok', 'Private API health failed')
            body = {'idempotency_key': 'member1-e13-c8', 'input': request}
            status, _, raw = http_exchange(base, '/v1/jobs', out, 'submit', body)
            require(status == 202, 'Submit HTTP status was not 202')
            job = json.loads(raw)['job_id']
            status, _, raw = http_exchange(base, '/v1/jobs', out, 'duplicate', body)
            require(status == 202 and json.loads(raw)['job_id'] == job, 'Duplicate created another job')
            changed = dict(body, input=dict(request, expected_output='different-input-for-conflict'))
            status, _, raw = http_exchange(base, '/v1/jobs', out, 'conflict', changed)
            require(status == 409 and json.loads(raw)['error'] == 'IDEMPOTENCY_CONFLICT', 'Conflict not rejected')
            deadline, sequence = time.monotonic() + timeout, 0
            while True:
                status, _, raw = http_exchange(base, '/v1/jobs/' + job, out, 'poll-%04d' % sequence)
                require(status == 200, 'Polling HTTP status was not 200')
                state = json.loads(raw)
                if state['status'] in ('SUCCEEDED', 'FAILED', 'TIMED_OUT'):
                    completed_job = True
                    break
                require(time.monotonic() < deadline, 'C8 API task exceeded client budget')
                sequence += 1
                time.sleep(1)
            pipeline.save(out / 'state.json', state)
            status, _, raw = http_exchange(base, '/v1/jobs/' + job + '/artifacts', out, 'artifacts')
            require(status == 200, 'Cannot obtain final artifact manifest')
            result = json.loads(raw)
            require(state['status'] == result['status'] == 'SUCCEEDED'
                    and result['job_id'] == job and result['trace_id'] == state['trace_id'],
                    'C8 job did not complete successfully')
            require([item['name'] for item in result['stages']] == ['full-check', 'incremental-check'],
                    'C8 must run the actual E11-A worker')
            require(isinstance(result.get('artifacts'), list) and bool(result['artifacts']),
                    'C8 requires a nonempty artifact list')
            downloads, seen = [], set()
            for index, ref in enumerate(result['artifacts']):
                prefix = 'artifact://' + job + '/'
                require(ref['uri'].startswith(prefix), 'Foreign downloaded artifact')
                relative = ref['uri'][len(prefix):]
                require(relative not in seen, 'Duplicate downloaded artifact')
                seen.add(relative)
                target = safe_download_target(out / 'downloads', relative)
                status, headers, data = http_exchange(base, '/v1/jobs/' + job + '/files/'
                                                      + quote(relative, safe='/'), out, 'file-%04d' % index)
                received_hash = {k.lower(): v for k, v in headers.items()}.get('x-content-sha256')
                require(status == 200 and digest(data) == ref['sha256'] == received_hash
                        and type(ref['bytes']) is int and len(data) == ref['bytes'], 'Downloaded artifact differs')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                downloads.append({'path': relative, 'sha256': digest(data), 'header_sha256': received_hash,
                                  'bytes': len(data)})
            pipeline.save(out / 'download-checks.json', downloads)
            stage_checks = verify_c8_downloads(result, request, out / 'downloads')
            pipeline.save(out / 'stage-checks.json', stage_checks)
            require(len(list(store.glob('job-*/state.json'))) == 1, 'Idempotency created extra jobs')
            summary = {'passed': True, 'same_key_same_job': True, 'conflict_status': 409,
                       'job_id': job, 'trace_id': result['trace_id'], 'downloaded_files': len(downloads),
                       'stage_checks': stage_checks,
                       'api': 'existing E12 asynchronous /v1/jobs', 'a13_client_session': False}
        finally:
            # This process group belongs only to the driver-launched API. C8 uses
            # E11-A, so no Docker jobs are launched by this private worker.
            cleanup = cleanup_server_group(process)
            cleanup['worker_terminal_before_shutdown'] = completed_job
            pipeline.save(out / 'server-cleanup.json', cleanup)
            if summary is not None:
                summary['cleanup'] = cleanup
                summary['passed'] = cleanup['parent_stopped'] and cleanup['process_group_absent_at_observation'] is True
                pipeline.save(out / 'summary.json', summary)
                require(summary['passed'], 'Private API process-group cleanup not verified')
    return summary


def run(request_path, out, api_timeout):
    require(os.name == 'posix' and os.getuid() != 0, 'Use the non-root Linux E11-E12 teaching image')
    require(not out.exists(), 'Use a new output directory')
    require(out.is_relative_to((ROOT / 'work').resolve()) and out != (ROOT / 'work').resolve(),
            'Output must be a new child of course work/')
    request_bytes = request_path.read_bytes()
    original = json.loads(request_bytes)
    require(original.get('profile') is None, 'This driver is for the controlled two-source fixture only')
    project = Path(original['repo']).resolve()
    require(project.is_relative_to((ROOT / 'data').resolve()), 'Fixture must be under course data/')
    require(original['base'] != original['target'], 'Need distinct real base and target commits')
    status_before = command(['git', 'status', '--porcelain=v1', '--untracked-files=all'], project)
    require(not status_before, 'Use a clean prepared fixture')
    out.mkdir(parents=True)
    (out / 'provided-request.json').write_bytes(request_bytes)
    before = source_snapshot(project, out / 'source-before')
    summary = {'student': '241880054', 'source_label': SOURCE_LABEL, 'passed': False, 'cases': {},
               'formal_cross_group_matrix': 'NOT_RUN', 'teacher_hidden_tests': 'NOT_RECEIVED',
               'scope': 'Local controlled rehearsal; not A13 execution, not E14 four-service acceptance',
               'request_sha256': digest(request_bytes),
               'course_source_commit': command(['git', '-c', 'safe.directory=' + str(ROOT),
                                                'rev-parse', 'HEAD']).decode().strip(),
               'base_commit': original['base'], 'target_commit': original['target'],
               'uid': os.getuid(), 'gid': os.getgid()}
    try:
        bundle = out / 'source-project.bundle'
        command(['git', 'bundle', 'create', str(bundle), '--all'], project)
        bundle_verify = command(['git', 'bundle', 'verify', str(bundle)], project)
        (out / 'source-bundle-verify.stdout.log').write_bytes(bundle_verify)
        pipeline.save(out / 'source-bundle.json', {
            'source': 'course-generated controlled fixture; LOCAL_SIMULATED_A',
            'file': bundle.name, 'sha256': digest(bundle.read_bytes()),
            'base_commit': original['base'], 'target_commit': original['target']})
        a_request = {key: original[key] for key in ('repo', 'base', 'target')}
        a_request['mode'] = 'e11-a'
        a_out = out / 'C1-local-A'
        a_result = pipeline.execute(a_request, a_out)
        a_verified = verify_success(a_result, a_out, a_request)
        result_path = a_out / 'result.json'
        expected_hash = digest(result_path.read_bytes())
        pipeline.save(out / 'local-A-input-binding.json', {
            'source_label': SOURCE_LABEL, 'result_sha256': expected_hash,
            'job_id': a_result['job_id'], 'trace_id': a_result['trace_id'],
            'target_commit': original['target'], 'independent_A13_acknowledgement': False})
        handoff = make_handoff(result_path, original['target'], result_sha256=expected_hash,
                               expected_job_id=a_result['job_id'], expected_trace_id=a_result['trace_id'])
        # This detects result mutation around the conversion; formal exchange
        # additionally uses the independently supplied A13 digest and identity.
        require(digest(result_path.read_bytes()) == expected_hash, 'Local A result changed during conversion')
        fixed = out / 'C1-handoff-fixed-md.json'
        pipeline.save(fixed, handoff)
        fixed_bytes = fixed.read_bytes()
        b_request = dict(original, mode='e11-b', fixed_report=str(fixed), fixed_report_sha256=digest(fixed_bytes))
        b_out = out / 'C1-B-consumption'
        b_result = pipeline.execute(b_request, b_out)
        b_verified = verify_success(b_result, b_out, b_request)
        summary['cases']['C1'] = {'passed': True, 'local_A': a_verified, 'B': b_verified,
                                  'result_sha256': expected_hash, 'fixed_report_sha256': digest(fixed_bytes),
                                  'source_report': handoff['source_report'], 'draft_image_id': b_result['draft_image_id']}
        require(source_bytes(project) == before, 'C1 changed original project')
        source_snapshot(project, out / 'source-after-C1')
        for name, negative_request, expected_code in (
            ('C2', dict(b_request, target=original['base']), 'STALE_REPORT'),
            ('C3', dict(b_request, fixed_report=str(out / 'C3-tampered-fixed-md.json')), 'ARTIFACT_HASH_MISMATCH'),
        ):
            if name == 'C3':
                tampered = fixed_bytes + b' \n'
                (out / 'C3-tampered-fixed-md.json').write_bytes(tampered)
                pipeline.save(out / 'C3-hashes.json', {'expected': digest(fixed_bytes), 'actual': digest(tampered),
                                                       'modification': 'Added whitespace to a separate copy'})
            case_out = out / (name + '-rejection')
            rejected = pipeline.execute(negative_request, case_out)
            require(rejected['status'] == 'FAILED' and rejected['error']['code'] == expected_code,
                    name + ' wrong rejection: ' + str(rejected.get('error')))
            require(rejected['stages'] == [] and not (case_out / 'draft-build').exists()
                    and not (case_out / 'candidate.patch').exists(), name + ' reached side effects')
            require(source_bytes(project) == before and fixed.read_bytes() == fixed_bytes,
                    name + ' changed original inputs')
            checks = verify_manifest(rejected, case_out)
            pipeline.save(out / (name + '-artifact-checks.json'), checks)
            source_snapshot(project, out / ('source-after-' + name))
            summary['cases'][name] = {'passed': True, 'expected_error': expected_code,
                                      'job_id': rejected['job_id'], 'trace_id': rejected['trace_id'],
                                      'stages': [], 'original_sources_preserved': True}
        summary['cases']['C8'] = run_c8(a_request, out / 'C8-http', api_timeout)
        require(source_bytes(project) == before, 'C8 changed original sources')
        require(command(['git', 'status', '--porcelain=v1', '--untracked-files=all'], project) == status_before,
                'Original repository status changed')
        source_snapshot(project, out / 'source-after-C8')
        require(digest(result_path.read_bytes()) == expected_hash and fixed.read_bytes() == fixed_bytes,
                'Original input changed')
        summary.update(passed=True, original_sources_preserved=True)
    except Exception as exc:
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        pipeline.save(out / 'summary.json', summary)
        # Exclude the list itself, Git metadata and symlinks. Legal hidden
        # tracked files, including .gitignore snapshots, remain in this list.
        entries = {path.relative_to(out).as_posix(): digest(path.read_bytes())
                   for path in sorted(out.rglob('*'))
                   if path.is_file() and not path.is_symlink() and '.git' not in path.relative_to(out).parts
                   and path != out / 'evidence-sha256.json'}
        pipeline.save(out / 'evidence-sha256.json', entries)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--api-timeout', type=int, default=600)
    parser.add_argument('--serve-store', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--ready-file', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_store is not None:
        if args.ready_file is None:
            parser.error('--ready-file required for internal server lifecycle')
        run_api_server(args.serve_store.resolve(), args.ready_file.resolve())
        return 0
    if args.request is None or args.out is None or args.api_timeout <= 0:
        parser.error('--request, --out and a positive --api-timeout are required')
    result = run(args.request.resolve(), args.out.resolve(), args.api_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
