"""Non-root Linux acceptance runner. Real Docker operations; no simulated success."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'labs/e11e12'))
import project_profile as pp
import pipeline
from consume_report import consume
from image_runtime import ImageRuntime

C0 = '592fc6f3d2463a58fe7f60b8d255ed242740bec0'
C1 = 'b2dda5513fe4a7d250493528800fe425cae459a5'
OLD_IMAGE = 'sha256:de2ea79e001d88ce6e40f38cd9d73025af12aeda21269ec6d9170738c36258e3'
PROFILE = pp.PROFILE
PHASH = pp.profile_hash(PROFILE)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(pp.canonical(value) + b'\n')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args, cwd=ROOT): return subprocess.check_output(['git', *args], cwd=cwd).decode().strip()
def require(ok, message):
    if not ok: raise ValueError(message)


def fingerprint(project):
    return {p.relative_to(project).as_posix(): sha(p) for p in sorted(project.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(project).parts}


def verify_result(out, expected_operations):
    result = json.loads((out / 'result.json').read_bytes())
    require(result['status'] == 'SUCCEEDED', 'Run failed: ' + str(out))
    require(result['profile_sha256'] == PHASH and result['success_scope'] == ['toml.o'], 'Profile/scope differs')
    image = result['draft_image_id']
    require(image != OLD_IMAGE and result['draft_image_reused'], 'Old/unreused DRAFT')
    operations = result['image_operations']
    require([op['operation'] for op in operations] == expected_operations, 'Missing image operations')
    for op in operations:
        require(op['image_id'] == op['actual_container_image'] == image and op['container_exit_code'] == 0,
                'Actual container image/exit differs')
        require(op['profile_sha256'] == PHASH and all(op['tools'].get(t) for t in ('git', 'gcc', 'make', 'strace', 'python3')),
                'Profile/tools witness missing')
        for name, digest in op['code_sha256'].items():
            path = {'lab.py': ROOT / 'labs/e8e10/lab.py',
                    'fullcheck.py': ROOT / 'labs/e11e12/environment/services/buildchecker/buildchecker/fullcheck.py'}.get(name, ROOT / 'labs/e11e12' / name)
            require(sha(path) == digest, 'Worker source changed: ' + name)
    validation = json.loads((out / 'validation/validation.json').read_bytes())
    require(validation['accepted'] and all(validation['checks'].values()), 'Validation failed')
    probe = json.loads((out / 'validation/header-probe.json').read_bytes())
    require(probe['successful_compiler_execs'] and probe['after_mtime_ns'] > probe['before_mtime_ns'], 'No real header-triggered compilation')
    findings = json.loads((out / 'final-full/findings.json').read_bytes())['findings']
    require(not any(f['type'] == 'MISSING' and f['target'] == 'toml.o' for f in findings), 'Scoped MD remains')
    residual = [f for f in findings if f['type'] == 'MISSING' and f['target'] != 'toml.o']
    require(any(f['target'] == 'toml_json' and f['dependency'] == 'toml.h' for f in residual), 'Expected full-project finding was lost')
    for ref in result['artifacts']:
        prefix = 'artifact://' + result['job_id'] + '/'
        require(ref['uri'].startswith(prefix), 'Artifact job differs')
        path = (out / ref['uri'][len(prefix):]).resolve()
        require(out.resolve() in path.parents and path.is_file(), 'Unsafe/missing artifact')
        require(sha(path) == ref['sha256'] and path.stat().st_size == ref['bytes'], 'Artifact hash/bytes differ')
    return {'status': 'PASS', 'job_id': result['job_id'], 'trace_id': result['trace_id'],
            'image_id': image, 'operations': expected_operations, 'artifact_count': len(result['artifacts']),
            'scope': ['toml.o'], 'whole_project_residual_missing': residual}


def consume_args(run, project, output):
    ep, payload = run / 'incremental-check.json', run / 'incremental-report.json'
    e = json.loads(ep.read_bytes()); result = json.loads((run / 'result.json').read_bytes())
    return dict(envelope_path=ep, envelope_sha256=sha(ep), payload_path=payload, payload_sha256=sha(payload),
                repo=project, target=C1, job_id=e['job_id'], trace_id=e['trace_id'], out=output,
                source_label='Member2 real tomlc99 E12 raw incremental output; not A13 original',
                image_id=result['draft_image_id'], profile=PROFILE, profile_sha256=PHASH)


def rejection_tests(run, project, out, base_project):
    out.mkdir()
    before = fingerprint(project)
    original = consume_args(run, project, out / 'unused')
    e0 = json.loads(original['envelope_path'].read_bytes()); p0 = json.loads(original['payload_path'].read_bytes())
    # Actual C0 scanner result inside the very same immutable DRAFT, never a relabeled C1 payload.
    runtime = ImageRuntime(original['image_id'], out / 'c0-image-execution', profile=PROFILE)
    c0 = runtime.scan(base_project)
    require(c0['commit'] == C0, 'C0 probe did not scan C0')
    save(out / 'actual-c0-report.json', c0)
    cases = [('wrong-hash', 'ARTIFACT_HASH_MISMATCH'), ('wrong-schema', 'SCHEMA_MISMATCH'),
             ('wrong-kind', 'ARTIFACT_TYPE_MISMATCH'), ('wrong-job', 'JOB_ID_MISMATCH'),
             ('wrong-trace', 'TRACE_ID_MISMATCH'), ('wrong-profile', 'PROFILE_HASH_MISMATCH'),
             ('late-unsafe', 'UNSAFE_PATH'), ('stale-c0', 'STALE_REPORT')]
    results = []
    for label, expected in cases:
        folder = out / label; folder.mkdir()
        envelope, payload = copy.deepcopy(e0), copy.deepcopy(p0)
        if label == 'wrong-schema': envelope['schema_version'] = 'unsupported'
        if label == 'wrong-kind': envelope['kind'] = 'fixed-md'
        if label == 'wrong-profile': payload['profile_sha256'] = '0' * 64
        if label == 'late-unsafe': payload['findings'].append({'type': 'MISSING', 'target': 'toml.o', 'dependency': '../outside.h'})
        if label == 'stale-c0': payload = c0; envelope['commit'] = C0
        save(folder / 'incremental-report.json', payload)
        envelope['data'] = payload
        envelope['artifacts'] = [{'uri': 'artifact://' + envelope['job_id'] + '/incremental-report.json',
                                  'sha256': sha(folder / 'incremental-report.json'),
                                  'bytes': (folder / 'incremental-report.json').stat().st_size}]
        save(folder / 'incremental-check.json', envelope)
        args = dict(original, envelope_path=folder / 'incremental-check.json', payload_path=folder / 'incremental-report.json',
                    envelope_sha256=sha(folder / 'incremental-check.json'), payload_sha256=sha(folder / 'incremental-report.json'), out=folder / 'output')
        if label == 'wrong-hash': args['payload_sha256'] = '0' * 64
        if label == 'wrong-job': args['job_id'] = 'wrong-job'
        if label == 'wrong-trace': args['trace_id'] = 'wrong-trace'
        try:
            consume(**args)
            raise AssertionError('Invalid input accepted: ' + label)
        except ValueError as exc:
            require(getattr(exc, 'code', None) == expected, 'Wrong rejection: ' + str(exc))
            require(not args['out'].exists() and fingerprint(project) == before, 'Rejected input wrote source/output')
            record = {'case': label, 'expected': expected, 'actual': exc.code, 'source_unchanged': True, 'output_absent': True}
            save(folder / 'rejection.json', record); results.append(record)
    save(out / 'summary.json', {'status': 'PASS', 'cases': results, 'c0_image_operations': runtime.operations})
    return results


def formal(project, out, head):
    require(git('rev-parse', 'HEAD', cwd=project) == C1 and not git('status', '--porcelain', cwd=project), 'C1 source must be clean')
    before = fingerprint(project)
    require(len(before) == 154, 'Expected 154 audited C1 files')
    data = ROOT / 'data' / ('m2-tomlc99-' + uuid.uuid4().hex); data.mkdir(parents=True)
    pipeline.snapshot(project, C1, data / 'repo', out / 'input-logs', profile=PROFILE)
    candidate = ROOT / 'course/e11-e12/profiles/tomlc99-tools-v1.candidate.Dockerfile'
    shutil.copyfile(candidate, data / 'candidate.Dockerfile')
    fixed = {'schema_version': 'e11e12-1', 'kind': 'fixed-md', 'status': 'SUCCEEDED', 'commit': C1,
             'profile_sha256': PHASH, 'source_label': 'Member2 fixed oracle from audited C1; not A13 raw incremental report',
             'data': {'schema_version': 'e8e10-1', 'commit': C1, 'profile_sha256': PHASH,
                      'findings': [{'type': 'MISSING', 'target': 'toml.o', 'dependency': h} for h in ('toml.h', 'toml_extra.h')]}}
    save(data / 'fixed-md.json', fixed)
    request = {'mode': 'e12', 'repo': str(data / 'repo'), 'base': C0, 'target': C1,
               'candidate': str(data / 'candidate.Dockerfile'), 'fixed_report': str(data / 'fixed-md.json'),
               'expected_output': '{}', 'build_timeout': 900, 'profile': PROFILE, 'profile_sha256': PHASH}
    save(out / 'runtime-request.json', request)
    summaries = {}
    for mode, operations in [('e11-b', ['validate', 'full']), ('e12', ['full', 'scan', 'scan', 'full', 'validate', 'full'])]:
        print('START=' + mode, flush=True)
        r = pipeline.execute(dict(request, mode=mode), out / mode)
        require(r['status'] == 'SUCCEEDED', mode + ': ' + json.dumps(r.get('error')))
        summaries[mode] = verify_result(out / mode, operations)
    args = consume_args(out / 'e12', data / 'repo', out / 'consumer')
    r = consume(**args); require(r['status'] == 'SUCCEEDED', 'Independent consumer failed: ' + str(r.get('error')))
    summaries['consumer'] = verify_result(out / 'consumer', ['validate', 'full'])
    require((out / 'consumer/received/incremental-check.json').read_bytes() == args['envelope_path'].read_bytes()
            and (out / 'consumer/received/incremental-report.json').read_bytes() == args['payload_path'].read_bytes(), 'Original report bytes differ')
    negatives = rejection_tests(out / 'e12', data / 'repo', out / 'rejections', out / 'e12/base-project')
    require(before == fingerprint(project), 'Original received source changed')
    summary = {'status': 'PASS', 'scope': 'Member2 real tomlc99 scoped acceptance; not A13 new HTTP acceptance',
               'source_commit': head, 'C0': C0, 'C1': C1, 'profile_sha256': PHASH,
               'candidate_sha256': sha(candidate), 'runtime_data': str(data), 'original_source': str(project),
               'original_source_unchanged': True, 'runs': summaries, 'rejection_cases': len(negatives),
               'original_A13_image_reused': False, 'new_tool_complete_DRAFT_used': True}
    save(out / 'original-source-sha256.json', before)
    save(out / 'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)
    print('REAL_FORMAL_EVIDENCE_CHECK=PASS', flush=True)


def http_check(formal_out, out, head):
    summary = json.loads((formal_out / 'summary.json').read_bytes())
    require(summary['status'] == 'PASS' and summary['source_commit'] == head, 'Use passed formal run from current code')
    request = json.loads((formal_out / 'runtime-request.json').read_bytes())
    with socket.socket() as sock: sock.bind(('127.0.0.1', 8082))
    key = 'member2-real-' + uuid.uuid4().hex
    log = (out / 'server.log').open('xb')
    process = subprocess.Popen([sys.executable, str(ROOT / 'labs/e11e12/server.py'), '--host', '127.0.0.1', '--port', '8082', '--store', str(out / 'store')],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save(out / 'server-identity.json', {'pid': process.pid, 'source_commit': head, 'port': 8082,
                                      'argv': process.args, 'scope': 'own loopback server only; shared 8081 untouched'})
    counter = 0
    local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(path, body=None):
        nonlocal counter
        counter += 1
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request('http://127.0.0.1:8082' + path, data=data, headers={'Content-Type': 'application/json'})
        try: response = local_http.open(req, timeout=30)
        except urllib.error.HTTPError as exc: response = exc
        with response:
            raw = response.read(); status = response.status; headers = dict(response.headers)
        stem = out / ('http-%04d' % counter)
        stem.with_suffix('.body').write_bytes(raw)
        save(stem.with_suffix('.json'), {'path': path, 'request': body, 'status': status, 'headers': headers, 'body_sha256': hashlib.sha256(raw).hexdigest()})
        return status, raw, headers
    try:
        for _ in range(60):
            require(process.poll() is None, 'Own server exited; inspect log')
            try:
                code, raw, _ = call('/health')
                if code == 200: break
            except urllib.error.URLError: time.sleep(0.5)
        else: raise ValueError('Own server did not become healthy')
        require(process.poll() is None, 'Port was taken by another process')
        body = {'input': request, 'idempotency_key': key}
        code, raw, _ = call('/v1/jobs', body); require(code == 202, 'POST failed'); jid = json.loads(raw)['job_id']
        code, raw, _ = call('/v1/jobs', body); require(code == 202 and json.loads(raw)['job_id'] == jid, 'Idempotency failed')
        conflict = copy.deepcopy(body); conflict['input']['target'] = C0
        code, raw, _ = call('/v1/jobs', conflict); require(code == 409, 'Expected conflict 409')
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            code, raw, _ = call('/v1/jobs/' + jid); require(code == 200, 'Poll failed')
            state = json.loads(raw)
            if state['status'] not in ('QUEUED', 'RUNNING'): break
            time.sleep(5)
        else: raise ValueError('Job timeout; evidence retained in ' + str(out / 'store' / jid))
        require(state['status'] == 'SUCCEEDED', 'HTTP job failed: ' + str(state))
        code, raw, _ = call('/v1/jobs/' + jid + '/artifacts'); require(code == 200, 'Artifacts unavailable')
        result = json.loads(raw); save(out / 'http-result.json', result)
        evidence = out / 'store' / jid / 'evidence'
        checked = verify_result(evidence, ['full', 'scan', 'scan', 'full', 'validate', 'full'])
        downloads = out / 'downloads'; downloads.mkdir()
        for ref in result['artifacts']:
            prefix = 'artifact://' + jid + '/'; require(ref['uri'].startswith(prefix), 'Wrong download job')
            name = ref['uri'][len(prefix):]; dest = (downloads / name).resolve()
            require(downloads.resolve() in dest.parents and '.git' not in dest.parts, 'Unsafe artifact path')
            code, raw, headers = call('/v1/jobs/' + jid + '/files/' + urllib.parse.quote(name, safe='/'))
            lower = {k.lower(): v for k, v in headers.items()}
            require(code == 200 and hashlib.sha256(raw).hexdigest() == ref['sha256'] == lower.get('x-content-sha256')
                    and len(raw) == ref['bytes'], 'Download verification failed: ' + name)
            dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
        save(out / 'summary.json', {'status': 'PASS', 'source_commit': head, 'scope': 'Member2 own 127.0.0.1:8082; not A13 cross-machine acceptance',
                                   'job_id': jid, 'evidence': str(evidence), 'checked': checked, 'idempotency': True, 'conflict_status': 409,
                                   'downloaded_artifacts': len(result['artifacts'])})
        print('REAL_HTTP_EVIDENCE_CHECK=PASS\nHTTP_JOB=' + jid, flush=True)
    finally:
        # Only the child created by this invocation is signalled. No port-based kill.
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        log.close()
        save(out / 'server-stopped.json', {'pid': process.pid, 'returncode': process.returncode})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['formal', 'http'])
    p.add_argument('--project', type=Path)
    p.add_argument('--formal-out', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    import pwd
    require(os.name == 'posix' and os.getuid() == os.geteuid() != 0 and pwd.getpwuid(os.getuid()).pw_name == 'm2_241880091', 'Use member2 non-root Linux account')
    require(os.environ.get('HOME') == '/home/m2_241880091', 'HOME differs')
    require(git('config', 'user.name') == '241880091', 'Git identity differs')
    require(not git('status', '--porcelain'), 'Commit code changes before formal execution')
    pp.check_environment()
    head = git('rev-parse', 'HEAD')
    out = a.out.resolve(); require((ROOT / 'work').resolve() in out.parents and not out.exists(), 'Use a new OUT under this worktree/work')
    out.mkdir(parents=True)
    save(out / 'execution-source.json', {'source_commit': head, 'uid': os.getuid(), 'root': str(ROOT),
        'tracked_sha256': {n: sha(ROOT / n) for n in git('ls-files', '-z').split('\0') if n}})
    try:
        if a.mode == 'formal':
            require(a.project is not None, '--project required'); formal(a.project.resolve(), out, head)
        else:
            require(a.formal_out is not None, '--formal-out required'); http_check(a.formal_out.resolve(), out, head)
        require(git('rev-parse', 'HEAD') == head and not git('status', '--porcelain'), 'Execution source changed')
        return 0
    except Exception as exc:
        save(out / 'failure.json', {'status': 'FAIL', 'error': repr(exc), 'source_commit': head})
        raise


if __name__ == '__main__': raise SystemExit(main())
