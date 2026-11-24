"""Compose the existing E5-E10 teaching components using versioned artifacts."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e8e10'), str(ROOT / 'labs/e11e12/vendor'), '/app']
from lab import scan, patch, validate
from image_runtime import ImageRuntime
import project_profile as pp

class Failure(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def artifact(path, out, job_id):
    return {'uri': f'artifact://{job_id}/{path.relative_to(out).as_posix()}',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes':path.stat().st_size}

def check_envelope(report, commit, kind=None):
    if report.get('schema_version') != 'e11e12-1':
        raise Failure('SCHEMA_MISMATCH', 'Expected e11e12-1')
    if report.get('commit') != commit:
        raise Failure('STALE_REPORT', 'Report belongs to another commit')
    if report.get('status') != 'SUCCEEDED':
        raise Failure('UPSTREAM_FAILED', 'Upstream stage did not succeed')
    if kind and report.get('kind') != kind:
        raise Failure('ARTIFACT_TYPE_MISMATCH', kind)

def load_artifact(path, expected_sha256):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected_sha256:
        raise Failure('ARTIFACT_HASH_MISMATCH','Artifact content changed during transfer')
    return json.loads(data)

def read_fixed_report(request, target_sha, profile=None):
    """Check one received byte string before cloning or executing project code.

    The checksum remains optional for legacy classroom requests. If the key is
    supplied, even null/empty/malformed values are errors, never an opt-out.
    The lazy import reuses the existing strict report parser without creating
    a module initialization cycle (consume_report also imports this module).
    """
    from consume_report import _json_object
    if not isinstance(target_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', target_sha):
        raise Failure('INVALID_REQUEST', 'Fixed report target must be a resolved complete Git SHA')
    path = request.get('fixed_report')
    if not isinstance(path, str) or not path:
        raise Failure('INVALID_REQUEST', 'fixed_report must be a nonempty file path')
    expected = request.get('fixed_report_sha256')
    if 'fixed_report_sha256' in request and (
        not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected)
    ):
        raise Failure('INVALID_REQUEST', 'fixed_report_sha256 must be 64 lowercase hex digits')
    received = Path(path).read_bytes()
    actual = hashlib.sha256(received).hexdigest()
    if expected is not None and expected != actual:
        raise Failure('ARTIFACT_HASH_MISMATCH', 'Fixed report differs from the exchanged SHA-256')
    envelope = _json_object(received)
    check_envelope(envelope, target_sha, 'fixed-md')
    current = envelope.get('data')
    if not isinstance(current, dict):
        raise Failure('INVALID_REPORT', 'Fixed report data must be an object')
    if current.get('commit') != target_sha:
        raise Failure('STALE_REPORT', 'Fixed report data commit mismatch')
    if current.get('schema_version') != 'e8e10-1':
        raise Failure('SCHEMA_MISMATCH', 'Expected e8e10-1 fixed report data')
    findings = current.get('findings')
    if not isinstance(findings, list) or any(
        not isinstance(item, dict)
        or item.get('type') not in ('MISSING', 'REDUNDANT')
        or not isinstance(item.get('target'), str) or not item['target']
        or not isinstance(item.get('dependency'), str) or not item['dependency']
        for item in findings
    ):
        raise Failure('INVALID_REPORT', 'Fixed findings must contain typed target/dependency records')
    if profile is not None:
        pp.require(envelope.get('profile_sha256') == pp.profile_hash(profile),
                   'PROFILE_HASH_MISMATCH', 'Fixed envelope/profile mismatch')
        pp.check_report(current, profile)
    elif envelope.get('profile_sha256') is not None or current.get('profile_sha256') is not None:
        raise Failure('PROFILE_REQUIRED', 'Profile report requires an explicitly bound profile')
    source = envelope.get('source_report')
    if 'source_report' in envelope:
        if not isinstance(source, dict):
            raise Failure('INVALID_REPORT', 'source_report must be an object')
        for name in ('job_id', 'trace_id'):
            value = source.get(name)
            if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', value):
                raise Failure('INVALID_REPORT', 'source_report requires safe task identifiers')
        if source.get('uri') != f"artifact://{source['job_id']}/incremental-check.json":
            raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'source_report URI must identify its incremental-check stage')
        if not isinstance(source.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
            raise Failure('INVALID_REPORT', 'source_report requires its original stage SHA-256')
    binding = {'sha256': actual, 'bytes': len(received),
               'exchanged_hash_verified': 'fixed_report_sha256' in request}
    if source is not None:
        binding['source_report'] = source
    return received, envelope, binding

def command(argv, cwd, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    log.write_text(p.stdout+p.stderr, encoding='utf-8')
    if p.returncode:
        raise Failure('COMMAND_FAILED', f'{argv[0]} failed; see {log.name}')
    return p.stdout.strip()

def snapshot(repo, revision, dest, logs, profile=None):
    sha = command(['git','rev-parse','--verify',revision+'^{commit}'], repo, logs/(dest.name+'-resolve.log'))
    command(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(dest)], repo, logs/(dest.name+'-clone.log'))
    command(['git','-c','core.autocrlf=false','checkout','--detach',sha], dest, logs/(dest.name+'-checkout.log'))
    if profile is not None:
        pp.check_project(dest, profile)
        return sha
    # E8-E10 profile; fail early instead of silently ignoring other targets.
    names = {p.name for p in dest.glob('*.c')}
    if names != {'main.c','helper.c'} or not (dest/'config.h').is_file():
        raise Failure('UNSUPPORTED_PROJECT', 'Expected main.c/helper.c/config.h and explicit Make rules')
    return sha

def full(project, folder):
    from buildchecker.fullcheck import full_check
    report = full_check(project, folder)
    if report.get('status') != 'SUCCEEDED':
        raise Failure('FULL_CHECK_FAILED', str(report.get('error', report.get('error_code'))))
    return report

def normalized(findings, targets=('main.o','helper.o')):
    return sorted((f['type'],f['target'],f['dependency']) for f in findings if f['target'] in targets)

def execute(request, out, job_id=None):
    job_id = job_id or 'job-'+uuid.uuid4().hex
    trace_id = 'trace-'+uuid.uuid4().hex
    if out.exists() and any(out.iterdir()):
        raise Failure('OUTPUT_EXISTS', 'Use a fresh output directory')
    out.mkdir(parents=True, exist_ok=True)
    result = {'schema_version':'e11e12-1','job_id':job_id,'trace_id':trace_id,'status':'RUNNING','stages':[]}
    save(out/'request.json',request)
    runtime = None
    profile = None
    before = None
    do_full, do_scan, do_validate = full, scan, validate
    def stage(name, commit, payload, files=()):
        envelope = {'schema_version':'e11e12-1','job_id':job_id,'trace_id':trace_id,'kind':name,
                    'commit':commit,'status':'SUCCEEDED','data':payload,
                    'artifacts':[artifact(p,out,job_id) for p in files]}
        if profile is not None:
            envelope.update(profile_sha256=pp.profile_hash(profile), success_scope=profile['repair_targets'])
        if runtime is not None:
            envelope.update(execution_environment='draft-image', image_id=runtime.image_id,
                            image_operations=list(runtime.operations))
        save(out/(name+'.json'),envelope)
        result['stages'].append({'name':name,'artifact':artifact(out/(name+'.json'),out,job_id)})
        return envelope
    try:
        profile = pp.bind_profile(request.get('profile'), request.get('profile_sha256'))
        if profile is not None:
            pp.check_environment()
            result.update(profile_sha256=pp.profile_hash(profile), success_scope=profile['repair_targets'])
            do_full = lambda project, folder: pp.full(project, folder, profile)
            do_scan = lambda project, old=None: pp.scan(project, old, profile)
            do_validate = lambda project, patchfile, folder: pp.validate(project, patchfile, folder, profile)
        mode=request['mode']
        if mode not in ('e11-a','e11-b','e12'):
            raise Failure('INVALID_REQUEST','Unknown mode')
        repo=Path(request['repo']).resolve()
        if not repo.is_dir():
            raise Failure('INVALID_REQUEST','Repository missing')
        fixed_input = None
        target_revision = request['target']
        if mode == 'e11-b':
            if not isinstance(target_revision, str) or not target_revision:
                raise Failure('INVALID_REQUEST', 'Target must identify an existing Git commit')
            # Resolve once and use the immutable result for both validation and
            # snapshotting; a moving branch cannot change the checked target.
            target_revision = command(['git', 'rev-parse', '--verify', '--end-of-options',
                                       target_revision + '^{commit}'], repo,
                                      out/'logs/fixed-target-resolve.log')
            if not re.fullmatch(r'[0-9a-f]{40}', target_revision):
                raise Failure('INVALID_REQUEST', 'Target must resolve to a complete Git SHA')
            fixed_input = read_fixed_report(request, target_revision, profile)
            result['fixed_report_binding'] = fixed_input[2]
            # Preserve the exact verified bytes, including whitespace and any
            # upstream provenance, rather than serializing a new JSON document.
            (out/'fixed-md-input.json').write_bytes(fixed_input[0])
        base=out/'base-project'; target=out/'target-project'
        extra = {'profile': profile} if profile is not None else {}
        base_sha=snapshot(repo,request['base'],base,out/'logs', **extra)
        target_sha=snapshot(repo,target_revision,target,out/'logs', **extra)
        result.update(base_commit=base_sha,target_commit=target_sha)
        if mode in ('e11-b','e12'):
            from draft.autobuild import auto_build
            candidate=Path(request['candidate']).resolve()
            profile_output = bytes.fromhex(profile['stdout_hex']).decode('utf-8').rstrip('\r\n') if profile is not None else '1'
            expected = request.get('expected_output', profile_output)
            if profile is not None:
                pp.require(expected == profile_output, 'INVALID_REQUEST', 'Expected output differs from the frozen profile')
            draft=auto_build(target,candidate,out/'draft-build',expected,timeout=request.get('build_timeout',600))
            if draft['status']!='SUCCEEDED':
                raise Failure('DRAFT_FAILED',draft.get('error','Inspect draft-build logs'))
            image_id = draft['attempts'][-1]['image_id']
            if profile is not None:
                pp.require((out/'draft-build/verify.log').read_bytes() == bytes.fromhex(profile['stdout_hex']), 'DRAFT_OUTPUT_MISMATCH', 'Exact stdout bytes differ')
            runtime = ImageRuntime(image_id, out/'image-execution', request.get('image_probe'), **extra)
            do_full, do_scan, do_validate = runtime.full, runtime.scan, runtime.validate
            result.update(execution_environment='draft-image', draft_image_id=image_id, draft_image_reused=False)
            stage('draft',target_sha,draft,[out/'draft-build/result.json'])
        if mode in ('e11-a','e12'):
            base_full=do_full(base,out/'baseline-full')
            old=do_scan(base)
            edges=json.loads((out/'baseline-full/actual-graph.json').read_text())
            projected={t:sorted({e['dependency'] for e in edges if e['target']==t}) for t in (profile['repair_targets'] if profile is not None else ('main.o','helper.o'))}
            if projected != old['actual']:
                raise Failure('GRAPH_MISMATCH','BuildChecker baseline differs from GCC observations')
            old['actual']=projected
            save(out/'baseline-cache.json',old)
            baseline=stage('full-check',base_sha,base_full,[out/'baseline-full/actual-graph.json',out/'baseline-full/findings.json',out/'baseline-cache.json'])
            check_envelope(baseline,base_sha,'full-check')
            current=do_scan(target,old)
            save(out/'incremental-report.json',current)
            reference=do_full(target,out/'target-full')
            targets = profile['repair_targets'] if profile is not None else ('main.o','helper.o')
            if normalized(reference['findings'], targets) != normalized(current['findings'], targets):
                raise Failure('FINDINGS_MISMATCH','Incremental/full object-target findings differ')
            md_envelope=stage('incremental-check',target_sha,current,[out/'incremental-report.json',out/'target-full/findings.json'])
        else:
            # Consume the same preflighted bytes; never reopen mutable input
            # after DRAFT has run. The received original is already archived.
            envelope=fixed_input[1]
            check_envelope(envelope,target_sha,'fixed-md')
            current=envelope['data']
            md_envelope=stage('fixed-md',target_sha,current,[out/'fixed-md-input.json'])
        if mode in ('e11-b','e12'):
            reference=result['stages'][-1]['artifact']
            md_envelope=load_artifact(out/(md_envelope['kind']+'.json'),reference['sha256'])
            check_envelope(md_envelope,target_sha)
            current=md_envelope['data']
            before=(target/'Makefile').read_bytes()
            diff,edits=pp.patch(target,current,profile) if profile is not None else patch(target,current)
            if not diff:
                raise Failure('NO_MISSING_DEPENDENCY','No MD to repair')
            patchfile=out/'candidate.patch';patchfile.write_bytes(diff.encode('utf-8'))
            save(out/'repair-plan.json',edits)
            stage('repair',target_sha,{'edits':edits,'input_report':artifact(out/(md_envelope['kind']+'.json'),out,job_id)},[patchfile,out/'repair-plan.json'])
            verdict=do_validate(target,patchfile,out/'validation')
            if not verdict['accepted']:
                raise Failure('REPAIR_REJECTED',str(verdict))
            final=do_full(target,out/'final-full')
            if any(f['type']=='MISSING' and (profile is None or f['target'] in profile['repair_targets']) for f in final['findings']):
                (target/'Makefile').write_bytes(before)
                raise Failure('RECHECK_FAILED','MD remains; working-copy declaration restored')
            stage('recheck',target_sha,{'validation':verdict,'findings':final['findings'],'patched_makefile_sha256':hashlib.sha256((target/'Makefile').read_bytes()).hexdigest()},[out/'validation/validation.json',out/'final-full/findings.json'])
        result['status']='SUCCEEDED'
        if runtime is not None:
            result['draft_image_reused'] = bool(runtime.operations)
    except (Failure,ValueError,OSError,KeyError,subprocess.TimeoutExpired) as exc:
        result.update(status='TIMED_OUT' if isinstance(exc,subprocess.TimeoutExpired) else 'FAILED',error={'code':getattr(exc,'code','EXECUTION_FAILED'),'message':str(exc)})
    if result['status'] != 'SUCCEEDED' and before is not None:
        (target/'Makefile').write_bytes(before)
        result['working_copy_makefile_restored'] = True
    if runtime is not None:
        result['image_operations'] = runtime.operations
    result['artifacts']=[artifact(p,out,job_id) for p in sorted(out.rglob('*')) if p.is_file() and '.git' not in p.parts and not p.is_symlink()]
    save(out/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=execute(json.loads(a.request.read_text(encoding='utf-8')),a.out.resolve());print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='SUCCEEDED' else 1

if __name__=='__main__':raise SystemExit(main())
