"""Verify an E11-A result and derive B's fixed-md without editing A originals.

For formal exchange, supply --result-sha256, --expected-job-id and
--expected-trace-id from the separately received delivery record. Without
those options this validates internal consistency only, as the teaching API
make_handoff(result_path, target_sha) historically did; it does not establish
the sender's identity. Both source and derived hashes must be archived.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'e11e12'))
from consume_report import _json_object, _validate_identity, verify_received_bytes
from pipeline import Failure


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return _json_object(path.read_bytes())


def _sha(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise Failure('INVALID_REQUEST', f'{label} must be 64 lowercase hex digits')
    return value


def _artifact_bytes(run_dir: Path, item: dict, job_id: str, cache: dict):
    if not isinstance(item, dict):
        raise Failure('INVALID_REPORT', 'Artifact reference must be an object')
    prefix = f'artifact://{job_id}/'
    uri = item.get('uri')
    if not isinstance(uri, str) or not uri.startswith(prefix):
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'Artifact belongs to another job')
    name = uri[len(prefix):]
    # Artifact URIs are literal relative POSIX paths, never URLs to decode.
    if (not name or '\\' in name or ':' in name
            or any(part in ('', '.', '..') for part in name.split('/'))):
        raise Failure('UNSAFE_PATH', 'Artifact path is missing or outside the run')
    path = run_dir.joinpath(*name.split('/'))
    cursor = run_dir
    for part in name.split('/'):
        cursor = cursor / part
        if cursor.is_symlink():
            raise Failure('UNSAFE_PATH', 'Artifact symlinks are not supported')
    if not path.resolve().is_relative_to(run_dir) or not path.is_file():
        raise Failure('UNSAFE_PATH', 'Artifact path is missing or outside the run')
    expected = _sha(item.get('sha256'), 'Artifact SHA-256')
    size = item.get('bytes')
    if type(size) is not int or size < 0:
        raise Failure('INVALID_REPORT', 'Artifact bytes must be a nonnegative integer')
    if name not in cache:
        cache[name] = path.read_bytes()
    data = cache[name]
    if hashlib.sha256(data).hexdigest() != expected or len(data) != size:
        raise Failure('ARTIFACT_HASH_MISMATCH', f'Artifact hash or size mismatch: {path.name}')
    return path, data


def checked_artifact(run_dir: Path, item: dict, job_id: str) -> Path:
    """Compatibility helper; the converter uses one byte cache for the whole run."""
    return _artifact_bytes(run_dir.resolve(), item, job_id, {})[0]


def _references(value, label):
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise Failure('INVALID_REPORT', f'{label} must be a list of objects')
    uris = [x.get('uri') for x in value]
    if any(not isinstance(uri, str) for uri in uris) or len(set(uris)) != len(uris):
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', f'{label} has invalid or duplicate URIs')
    return value


def make_handoff(result_path: Path, target_sha: str, *, result_sha256=None,
                 expected_job_id=None, expected_trace_id=None) -> dict:
    if not isinstance(target_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', target_sha):
        raise Failure('INVALID_REQUEST', 'Target must be a complete lowercase Git SHA')
    result_path = Path(result_path)
    if result_path.is_symlink() or not result_path.is_file():
        raise Failure('UNSAFE_PATH', 'Result must be an ordinary file')
    run_dir = result_path.resolve().parent
    result_bytes = result_path.read_bytes()
    actual_result_sha = hashlib.sha256(result_bytes).hexdigest()
    if result_sha256 is not None and actual_result_sha != _sha(result_sha256, 'Result SHA-256'):
        raise Failure('ARTIFACT_HASH_MISMATCH', 'Result differs from independently exchanged SHA-256')
    result = _json_object(result_bytes)
    if result.get('schema_version') != 'e11e12-1' or result.get('status') != 'SUCCEEDED':
        raise Failure('UPSTREAM_FAILED', 'A task did not succeed with the expected schema')
    if result.get('target_commit') != target_sha:
        raise Failure('STALE_REPORT', 'A task belongs to another target commit')
    job_id, trace_id = result.get('job_id'), result.get('trace_id')
    _validate_identity(target_sha, job_id, trace_id)
    if expected_job_id is not None and expected_job_id != job_id:
        raise Failure('JOB_ID_MISMATCH', 'Result job_id differs from exchanged task')
    if expected_trace_id is not None and expected_trace_id != trace_id:
        raise Failure('TRACE_ID_MISMATCH', 'Result trace_id differs from exchanged trace')
    stages = result.get('stages')
    if not isinstance(stages, list) or any(not isinstance(x, dict) for x in stages):
        raise Failure('INVALID_REPORT', 'Result stages must be a list of objects')
    matches = [x for x in stages if x.get('name') == 'incremental-check']
    if len(matches) != 1:
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'Expected one incremental-check stage')
    cache = {result_path.resolve().name: result_bytes}
    # Verify other declared stage/global references as well, without rereading
    # an already verified file when the same artifact occurs in several lists.
    for entry in stages:
        _artifact_bytes(run_dir, entry.get('artifact'), job_id, cache)
    for item in _references(result.get('artifacts', []), 'Result artifacts'):
        _artifact_bytes(run_dir, item, job_id, cache)
    stage_item = matches[0]['artifact']
    stage_path, stage_bytes = _artifact_bytes(run_dir, stage_item, job_id, cache)
    if stage_path != run_dir / 'incremental-check.json':
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'Unexpected stage artifact path')
    stage = _json_object(stage_bytes)
    references = _references(stage.get('artifacts'), 'Incremental artifacts')
    for item in references:
        _artifact_bytes(run_dir, item, job_id, cache)
    payload_uri = f'artifact://{job_id}/incremental-report.json'
    payload_refs = [x for x in references if x['uri'] == payload_uri]
    if len(payload_refs) != 1:
        raise Failure('ARTIFACT_REFERENCE_MISMATCH', 'Expected one incremental-report.json reference')
    payload_ref = payload_refs[0]
    _, payload_bytes = _artifact_bytes(run_dir, payload_ref, job_id, cache)
    received = verify_received_bytes(stage_bytes, stage_item['sha256'], payload_bytes,
                                     payload_ref['sha256'], target_sha, job_id, trace_id)
    bindings = [result.get('profile_sha256'), stage.get('profile_sha256'),
                received.payload.get('profile_sha256')]
    if any(value is not None for value in bindings):
        if (any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                for value in bindings) or len(set(bindings)) != 1):
            raise Failure('PROFILE_HASH_MISMATCH', 'Result, envelope and payload profile hashes differ')
    report = {
        'schema_version': 'e11e12-1', 'kind': 'fixed-md', 'status': 'SUCCEEDED',
        'commit': target_sha, 'data': received.payload,
        'source_report': {
            'job_id': job_id, 'trace_id': trace_id,
            'uri': stage_item['uri'], 'sha256': stage_item['sha256'],
            'payload_uri': payload_uri, 'payload_sha256': payload_ref['sha256'],
            'result_sha256': actual_result_sha,
            'exchanged_result_sha256_verified': result_sha256 is not None,
            'exchanged_job_id_verified': expected_job_id is not None,
            'exchanged_trace_id_verified': expected_trace_id is not None,
        },
    }
    if bindings[0] is not None:
        report['profile_sha256'] = bindings[0]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a-result', required=True, type=Path)
    parser.add_argument('--target-sha', required=True)
    parser.add_argument('--result-sha256', help='SHA-256 received independently from A')
    parser.add_argument('--expected-job-id', help='Source job ID from A delivery record')
    parser.add_argument('--expected-trace-id', help='Source trace ID from A delivery record')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output already exists; preserve earlier evidence')
    report = make_handoff(args.a_result, args.target_sha, result_sha256=args.result_sha256,
                          expected_job_id=args.expected_job_id, expected_trace_id=args.expected_trace_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('HANDOFF_READY', f'sha256={digest(args.out)}', f"source_job={report['source_report']['job_id']}")


if __name__ == '__main__':
    main()
