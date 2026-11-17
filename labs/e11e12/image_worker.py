"""Run one real operation inside the selected immutable DRAFT image."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback


def main():
    bundle = Path('/tmp/m2-input')
    project = Path('/tmp/m2-project')
    output = Path('/tmp/m2-output')
    output.mkdir(exist_ok=False)
    request = json.loads((bundle / 'request.json').read_text())
    result = {'status': 'FAILED', 'operation': request['operation'], 'uid': os.getuid()}
    try:
        for name, digest in request['code_sha256'].items():
            if hashlib.sha256((bundle / name).read_bytes()).hexdigest() != digest:
                raise ValueError('WORKER_CODE_HASH_MISMATCH: ' + name)
        versions = {}
        for name in ('python3', 'git', 'gcc', 'make', 'strace'):
            if not shutil.which(name):
                raise ValueError('IMAGE_TOOL_MISSING: ' + name)
            p = subprocess.run([name, '--version'], capture_output=True, text=True, timeout=20)
            if p.returncode:
                raise ValueError('IMAGE_TOOL_FAILED: ' + name)
            versions[name] = (p.stdout + p.stderr).splitlines()[0]
        result['tools'] = versions
        probe = request.get('probe')
        if probe:
            value = Path(probe['path']).read_text().strip()
            if value != probe['value']:
                raise ValueError('IMAGE_MARKER_MISMATCH')
            result['marker'] = {'path': probe['path'], 'value': value, 'observed': True}
        subprocess.run(['git', '-c', 'safe.directory=' + str(project), 'rev-parse', 'HEAD'],
                       cwd=project, check=True, stdout=subprocess.PIPE, timeout=20)
        sys.path.insert(0, str(bundle))
        from lab import scan, validate
        from fullcheck import full_check
        kind = request['operation']
        profile = request.get('profile')
        if profile is not None or request.get('profile_sha256') is not None:
            import project_profile as pp
            profile = pp.bind_profile(profile, request.get('profile_sha256'))
            pp.check_environment()
            result['profile_sha256'] = pp.profile_hash(profile)
        if kind == 'full':
            payload = pp.full(project, output / 'evidence', profile) if profile is not None else full_check(project, output / 'evidence')
        elif kind == 'scan':
            payload = pp.scan(project, request.get('old'), profile) if profile is not None else scan(project, request.get('old'))
        elif kind == 'validate':
            payload = pp.validate(project, bundle / 'candidate.patch', output / 'evidence', profile) if profile is not None else validate(project, bundle / 'candidate.patch', output / 'evidence')
            if payload['accepted']:
                (output / 'accepted.Makefile').write_bytes((project / 'Makefile').read_bytes())
        else:
            raise ValueError('UNSUPPORTED_IMAGE_OPERATION')
        result.update(status='SUCCEEDED', payload=payload)
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc())
    (output / 'response.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result['status'] == 'SUCCEEDED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
