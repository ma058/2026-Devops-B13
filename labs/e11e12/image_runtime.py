"""Immutable-image execution with explicit copies, never orchestrator fallback.

docker cp addresses the daemon's container filesystem; no orchestrator path is
misinterpreted as a host bind source. Only an accepted, exact Makefile patch is
copied back. All commands, image inspection, worker results and raw evidence stay.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import project_profile as pp

ROOT = Path(__file__).resolve().parents[2]


class ImageFailure(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(ok, code, message):
    if not ok:
        raise ImageFailure(code, message)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def validate_image_id(image):
    require(isinstance(image, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', image),
            'INVALID_IMAGE_ID', 'An immutable sha256 image ID is required; tags are not accepted')


def validate_probe(probe):
    if probe is None:
        return
    require(isinstance(probe, dict) and set(probe) == {'path', 'value'}
            and isinstance(probe['path'], str)
            and re.fullmatch(r'/opt/m2-draft-marker-[0-9a-f]{32}', probe['path'])
            and isinstance(probe['value'], str)
            and re.fullmatch(r'[0-9a-f]{32}', probe['value'])
            and probe['path'].endswith(probe['value']),
            'INVALID_IMAGE_PROBE', 'Expected the controlled member2 image marker')


class ImageRuntime:
    def __init__(self, image_id, out, probe=None, profile=None):
        validate_image_id(image_id)
        validate_probe(probe)
        self.profile = pp.resolve_profile(profile)
        if self.profile is not None:
            pp.check_environment()
        require(os.name == 'posix' and os.getuid() != 0, 'IMAGE_EXECUTION_IDENTITY',
                'Image operations require a non-root Linux caller')
        self.image_id, self.out, self.probe = image_id, Path(out), probe
        self.out.mkdir(parents=True, exist_ok=False)
        self.operations = []

    def run(self, kind, project, folder=None, old=None, patchfile=None):
        project = Path(project).resolve()
        number = len(self.operations) + 1
        op = self.out / ('%02d-' % number + kind)
        op.mkdir(exist_ok=False)
        log_number = 0

        def command(args, checked=True, timeout=60):
            nonlocal log_number
            log_number += 1
            prefix = op / ('%02d-%s' % (log_number, args[1]))
            save(prefix.with_suffix('.command.json'), {'argv': args})
            with prefix.with_suffix('.stdout.log').open('wb') as stdout, prefix.with_suffix('.stderr.log').open('wb') as stderr:
                try:
                    p = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=timeout)
                except subprocess.TimeoutExpired:
                    save(prefix.with_suffix('.exit.json'), {'timed_out': True, 'timeout': timeout})
                    raise
            save(prefix.with_suffix('.exit.json'), {'exit_code': p.returncode})
            require(not checked or p.returncode == 0, 'IMAGE_COMMAND_FAILED', 'Inspect ' + str(prefix))
            return p.returncode, prefix.with_suffix('.stdout.log').read_bytes()

        require(kind in ('full', 'scan', 'validate'), 'INVALID_IMAGE_OPERATION', kind)
        require(not any(p.is_symlink() for p in project.rglob('*')), 'UNSUPPORTED_PROJECT', 'Symlinks are unsupported')
        before = (project / 'Makefile').read_bytes()
        _, raw = command(['docker', 'image', 'inspect', self.image_id])
        require(json.loads(raw)[0]['Id'] == self.image_id, 'IMAGE_ID_MISMATCH', 'Docker resolved a different image')
        bundle = op / 'input'
        bundle.mkdir()
        sources = {'image_worker.py': Path(__file__).with_name('image_worker.py'),
                   'lab.py': ROOT / 'labs/e8e10/lab.py',
                   'fullcheck.py': ROOT / 'labs/e11e12/environment/services/buildchecker/buildchecker/fullcheck.py'}
        if self.profile is not None:
            sources['project_profile.py'] = Path(__file__).with_name('project_profile.py')
        hashes = {}
        for name, source in sources.items():
            shutil.copyfile(source, bundle / name)
            hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        if patchfile:
            shutil.copyfile(patchfile, bundle / 'candidate.patch')
        save(bundle / 'request.json', {'operation': kind, 'old': old, 'probe': self.probe, 'code_sha256': hashes,
            'profile': self.profile, 'profile_sha256': pp.profile_hash(self.profile) if self.profile is not None else None})
        token = uuid.uuid4().hex
        create = ['docker', 'create', '--network', 'none', '--cpus', '1', '--memory', '512m',
                  '--pids-limit', '256', '--cap-drop', 'ALL', '--cap-add', 'SYS_PTRACE',
                  '--security-opt', 'no-new-privileges', '--user', f'{os.getuid()}:{os.getgid()}',
                  '--label', 'devops.member2.operation=' + token, '-e', 'HOME=/tmp',
                  '-e', 'PYTHONDONTWRITEBYTECODE=1', '--workdir', '/tmp',
                  '--entrypoint', 'python3', self.image_id, '/tmp/m2-input/image_worker.py']
        _, raw = command(create)
        cid = raw.decode().strip()
        require(re.fullmatch('[0-9a-f]{64}', cid), 'INVALID_CONTAINER_ID', 'Docker returned invalid container ID')
        try:
            command(['docker', 'cp', '-a', str(bundle), cid + ':/tmp/m2-input'])
            command(['docker', 'cp', '-a', str(project), cid + ':/tmp/m2-project'])
            _, raw = command(['docker', 'inspect', cid])
            info = json.loads(raw)[0]
            require(info['Image'] == self.image_id and info['Config']['Labels'].get('devops.member2.operation') == token,
                    'IMAGE_ID_MISMATCH', 'Actual container image/ownership mismatch')
            code, _ = command(['docker', 'start', '--attach', cid], checked=False, timeout=600)
            _, raw = command(['docker', 'inspect', cid])
            info = json.loads(raw)[0]
            # Copy diagnostic evidence even if the operation failed.
            copy_code, _ = command(['docker', 'cp', '-a', cid + ':/tmp/m2-output', str(op / 'output')], checked=False)
            require(code == 0 and info['State']['ExitCode'] == 0 and not info['State']['Running'] and copy_code == 0,
                    'IMAGE_OPERATION_FAILED', 'Container failed; inspect ' + str(op))
            response = json.loads((op / 'output/response.json').read_bytes())
            require(response['status'] == 'SUCCEEDED' and response['operation'] == kind
                    and response['uid'] == os.getuid(), 'IMAGE_OPERATION_FAILED', str(response))
            if self.profile is not None:
                require(response.get('profile_sha256') == pp.profile_hash(self.profile) and response['payload'].get('profile_sha256') == pp.profile_hash(self.profile),
                        'PROFILE_HASH_MISMATCH', 'Worker/profile response binding differs')
            witness = {'operation': kind, 'project_commit': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip(),
                'image_id': self.image_id, 'actual_container_image': info['Image'], 'container_id': cid,
                'container_exit_code': info['State']['ExitCode'], 'tools': response['tools'],
                'marker': response.get('marker'), 'code_sha256': hashes,
                'profile_sha256': response.get('profile_sha256'),
                'transport': 'docker cp -a; no host bind mounts'}
            save(op / 'execution.json', witness)
            self.operations.append(witness)
            if folder:
                shutil.copytree(op / 'output/evidence', folder)
            payload = response['payload']
            if kind == 'validate' and payload['accepted']:
                accepted = (op / 'output/accepted.Makefile').read_bytes()
                exact = ''.join(difflib.unified_diff(before.decode().splitlines(True), accepted.decode().splitlines(True),
                                                    fromfile='a/Makefile', tofile='b/Makefile'))
                require(exact == Path(patchfile).read_text(), 'IMAGE_PATCH_MISMATCH', 'Only the exact candidate may be written back')
                require((project / 'Makefile').read_bytes() == before, 'SOURCE_CHANGED', 'Input changed during validation')
                (project / 'Makefile').write_bytes(accepted)
            return payload
        finally:
            command(['docker', 'rm', '-f', cid], checked=False)

    def full(self, project, folder):
        result = self.run('full', project, folder=folder)
        require(result.get('status') == 'SUCCEEDED', 'FULL_CHECK_FAILED', str(result.get('error')))
        return result

    def scan(self, project, old=None):
        return self.run('scan', project, old=old)

    def validate(self, project, patchfile, folder):
        return self.run('validate', project, folder=folder, patchfile=patchfile)
