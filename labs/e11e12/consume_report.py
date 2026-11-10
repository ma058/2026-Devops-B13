"""Consume a separately delivered A report without rerunning A detection.

The caller must exchange both SHA-256 values and task identifiers before use.
Only an isolated clone is patched. Execution currently uses the orchestrator
environment, not DRAFT's image; that environment handoff remains separate work.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import Failure, artifact, check_envelope, full, patch, save, snapshot, validate


@dataclass(frozen=True)
class ReceivedReport:
    envelope: dict
    payload: dict
    envelope_bytes: bytes
    payload_bytes: bytes
    payload_uri: str


def _object_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise Failure('INVALID_REPORT', 'Duplicate JSON key: ' + name)
        result[name] = value
    return result


def _json_object(data):
    try:
        def invalid_constant(value):
            raise Failure('INVALID_REPORT', 'Non-JSON numeric constant: ' + value)
        value = json.loads(data, object_pairs_hook=_object_pairs,
                           parse_constant=invalid_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Failure('INVALID_REPORT', 'Report must contain valid JSON') from exc
    if not isinstance(value, dict):
        raise Failure('INVALID_REPORT', 'Report must be a JSON object')
    return value


def _hash_bytes(path, expected):
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise Failure('INVALID_REQUEST', 'Expected SHA-256 must be 64 lowercase hex digits')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise Failure('ARTIFACT_HASH_MISMATCH', 'Received file does not match exchanged SHA-256')
    return data


def verify_received(envelope_path, envelope_sha256, payload_path, payload_sha256,
                    target, job_id, trace_id):
    """Validate both immutable input byte strings; never create or write files."""
    if not isinstance(target, str) or not re.fullmatch(r'[0-9a-f]{40}', target):
        raise Failure('INVALID_REQUEST', 'Target must be a complete 40-digit Git commit SHA')
    for value in (job_id, trace_id):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', value):
            raise Failure('INVALID_REQUEST', 'Expected job_id and trace_id must be nonempty safe identifiers')
    envelope_bytes = _hash_bytes(envelope_path, envelope_sha256)
    payload_bytes = _hash_bytes(payload_path, payload_sha256)
    envelope = _json_object(envelope_bytes)
    payload = _json_object(payload_bytes)
    check_envelope(envelope, target, 'incremental-check')
    if envelope.get('job_id') != job_id:
        raise Failure('JOB_ID_MISMATCH', 'Envelope job_id differs from exchanged task')
    if envelope.get('trace_id') != trace_id:
        raise Failure('TRACE_ID_MISMATCH', 'Envelope trace_id differs from exchanged trace')
    if payload.get('commit') != target:
        raise Failure('STALE_REPORT', 'Inner payload commit differs from repair target')
    if payload.get('schema_version') != 'e8e10-1':
        raise Failure('SCHEMA_MISMATCH', 'Expected e8e10-1 incremental payload')
    findings = payload.get('findings')
    if not isinstance(findings, list) or any(
        not isinstance(item, dict)
        or item.get('type') not in ('MISSING', 'REDUNDANT')
        or not isinstance(item.get('target'), str) or not item['target']
        or not isinstance(item.get('dependency'), str) or not item['dependency']
        for item in findings
    ):
        raise Failure('INVALID_REPORT', 'Payload findings must contain typed target/dependency records')
    # Canonical JSON preserves distinctions such as True versus 1 that Python's
    # ordinary dictionary equality would otherwise treat as equal.
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if canonical(envelope.get('data')) != canonical(payload):
        raise Failure('REPORT_DATA_MISMATCH', 'Envelope data differs from downloaded payload')
    uri = f'artifact://{job_id}/incremental-report.json'
    references = envelope.get('artifacts')
    if not isinstance(references, list) or any(not isinstance(item, dict) for item in references):
        raise Failure('INVALID_REPORT', 'Envelope artifacts must be a list of objects')
    matches = [item for item in references if item.get('uri') == uri]
    if len(matches) != 1:
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'Expected exactly one incremental-report.json reference for this job')
    reference = matches[0]
    if reference.get('sha256') != payload_sha256:
        raise Failure('ARTIFACT_HASH_MISMATCH', 'Envelope payload hash differs from exchanged hash')
    if type(reference.get('bytes')) is not int or reference['bytes'] != len(payload_bytes):
        raise Failure('ARTIFACT_SIZE_MISMATCH', 'Envelope payload size differs from received bytes')
    return ReceivedReport(envelope, payload, envelope_bytes, payload_bytes, uri)


def consume(envelope_path, envelope_sha256, payload_path, payload_sha256, repo,
            target, job_id, trace_id, out, source_label='unconfirmed-external-report'):
    # All report checks precede creating an output or cloning a repair target.
    received = verify_received(envelope_path, envelope_sha256, payload_path,
                               payload_sha256, target, job_id, trace_id)
    repo = Path(repo).resolve()
    out = Path(out).resolve()
    if not repo.is_dir():
        raise Failure('INVALID_REQUEST', 'Repository directory is missing')
    if out == repo or repo in out.parents:
        raise Failure('INVALID_REQUEST', 'Output must be outside the source repository')
    if out.exists():
        raise Failure('OUTPUT_EXISTS', 'Use a new output directory, including for retries')
    resolved = subprocess.run(['git', 'rev-parse', '--verify', target + '^{commit}'],
                              cwd=repo, capture_output=True, text=True, timeout=30)
    if resolved.returncode or resolved.stdout.strip() != target:
        raise Failure('STALE_REPORT', 'Target commit is not available in the supplied repository')
    out.mkdir(parents=True, exist_ok=False)
    result = {'schema_version': 'e11e12-1', 'kind': 'b-report-consumption',
              'job_id': job_id, 'trace_id': trace_id, 'commit': target,
              'status': 'RUNNING', 'execution_environment': 'orchestrator',
              'draft_image_reused': False, 'source_label': source_label,
              'stages': [], 'upstream': {'kind': 'incremental-check',
                  'envelope_sha256': envelope_sha256, 'payload_sha256': payload_sha256,
                  'payload_uri': received.payload_uri}}
    (out / 'received').mkdir()
    (out / 'received' / 'incremental-check.json').write_bytes(received.envelope_bytes)
    (out / 'received' / 'incremental-report.json').write_bytes(received.payload_bytes)
    save(out / 'request.json', {'repo': str(repo), 'target': target,
        'expected_job_id': job_id, 'expected_trace_id': trace_id,
        'expected_envelope_sha256': envelope_sha256,
        'expected_payload_sha256': payload_sha256, 'source_label': source_label})

    def stage(name, data, files):
        envelope = {'schema_version': 'e11e12-1', 'kind': name, 'status': 'SUCCEEDED',
                    'commit': target, 'job_id': job_id, 'trace_id': trace_id,
                    'execution_environment': 'orchestrator', 'draft_image_reused': False,
                    'data': data, 'artifacts': [artifact(file, out, job_id) for file in files]}
        save(out / (name + '.json'), envelope)
        result['stages'].append({'name': name, 'artifact': artifact(out / (name + '.json'), out, job_id)})

    working_copy = out / 'target-project'
    before = None
    try:
        snapshot(repo, target, working_copy, out / 'logs')
        before = (working_copy / 'Makefile').read_bytes()
        (out / 'source-before.Makefile').write_bytes(before)
        diff, edits = patch(working_copy, received.payload)
        if not diff:
            raise Failure('NO_MISSING_DEPENDENCY', 'Received report has no repairable missing dependency')
        if (working_copy / 'Makefile').read_bytes() != before:
            raise Failure('SOURCE_CHANGED', 'Candidate generation changed its input')
        patchfile = out / 'candidate.patch'
        patchfile.write_text(diff, encoding='utf-8')
        save(out / 'repair-plan.json', edits)
        stage('repair', {'edits': edits, 'input_report': result['upstream']},
              [patchfile, out / 'repair-plan.json'])
        verdict = validate(working_copy, patchfile, out / 'validation')
        if not verdict['accepted']:
            raise Failure('REPAIR_REJECTED', 'Candidate did not pass sandbox validation')
        final = full(working_copy, out / 'final-full')
        if any(item['type'] == 'MISSING' for item in final['findings']):
            raise Failure('RECHECK_FAILED', 'Dynamic recheck still reports missing dependencies')
        (out / 'source-after.Makefile').write_bytes((working_copy / 'Makefile').read_bytes())
        stage('recheck', {'validation': verdict, 'findings': final['findings'],
                         'patched_makefile_sha256': hashlib.sha256((working_copy / 'Makefile').read_bytes()).hexdigest()},
              [out / 'validation' / 'validation.json', out / 'final-full' / 'findings.json'])
        result['status'] = 'SUCCEEDED'
    except (Failure, ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        if before is not None:
            (working_copy / 'Makefile').write_bytes(before)
            result['working_copy_makefile_restored'] = True
        result.update(status='TIMED_OUT' if isinstance(exc, subprocess.TimeoutExpired) else 'FAILED',
                      error={'code': getattr(exc, 'code', 'EXECUTION_FAILED'), 'message': str(exc)})
    result['artifacts'] = [artifact(file, out, job_id) for file in sorted(out.rglob('*'))
                           if file.is_file() and '.git' not in file.parts and not file.is_symlink()]
    save(out / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('envelope', 'payload', 'repo', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('envelope-sha256', 'payload-sha256', 'target', 'job-id', 'trace-id'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--source-label', default='unconfirmed-external-report')
    args = parser.parse_args()
    try:
        result = consume(args.envelope, args.envelope_sha256, args.payload, args.payload_sha256,
                         args.repo, args.target, args.job_id, args.trace_id, args.out, args.source_label)
    except (Failure, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {'status': 'FAILED', 'execution_environment': 'orchestrator',
                  'draft_image_reused': False,
                  'error': {'code': getattr(exc, 'code', 'INVALID_REQUEST'), 'message': str(exc)}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'SUCCEEDED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
