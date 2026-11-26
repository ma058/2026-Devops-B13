"""Frozen tomlc99 and b13-level-v1 profiles for E11/E12 project execution.

The non-target Makefile bytes must equal the received audited recipe. This is
not a general Make interpreter. Unsupported layouts/overrides fail closed.
"""
import ast
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

FLAGS = ['-std=c99', '-Wall', '-Wextra', '-fpic', '-O2', '-DNDEBUG']
PROFILE = {
    'schema_version': 'b13-project-profile-1', 'id': 'a13-tomlc99-release-1',
    'units': [['toml.o', 'toml.c']], 'repair_targets': ['toml.o'],
    'clean_argv': ['make', 'clean'], 'build_argv': ['make', 'toml_json'],
    'run_argv': ['./toml_json'], 'stdin_hex': '', 'stdout_hex': '7b7d0a',
    'exit_code': 0, 'effective_flags': FLAGS,
    'header_probe': {'path': 'toml.h', 'append_hex': '0a2f2a2065313165313220646570656e64656e63792070726f6265202a2f0a'},
    'recursive_scan': False, 'strict_sources': False,
    'makefile_template_sha256': '9247cc0f838a47456213d49d4aed2af11c6ba4c17b67dfff81d58aa486fb2c15',
}
B13_PROJECT_ID = 'b13-level-v1'
# Workers receive this module independently of the repository's profile JSON.
B13_PROFILE_SHA256 = 'f0367b454aff9cb0a5304e3e3330b61d4bbd01c3f19069eaf5930a1664d3733b'
B13_MISSING_HEADERS = {'main.o': 'config.h', 'helper.o': 'extra.h'}

OVERRIDES = ('DEBUG', 'CC', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'MAKEFLAGS',
             'GNUMAKEFLAGS', 'MAKEOVERRIDES', 'MFLAGS', 'MAKEFILES')


class ProfileError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(ok, code, message):
    if not ok:
        raise ProfileError(code, message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def resolve_profile(raw):
    if raw is None:
        return None
    require(isinstance(raw, dict), 'INVALID_PROFILE', 'Profile must be an object')
    try:
        raw_bytes = canonical(raw)
    except (TypeError, ValueError) as exc:
        raise ProfileError('INVALID_PROFILE', 'Profile must be canonical JSON') from exc
    if raw_bytes == canonical(PROFILE):
        return copy.deepcopy(PROFILE)
    require(raw.get('id') == B13_PROJECT_ID and hashlib.sha256(raw_bytes).hexdigest() == B13_PROFILE_SHA256,
            'INVALID_PROFILE', 'Expected the frozen tomlc99 or b13-level-v1 profile')
    return copy.deepcopy(raw)


def profile_hash(profile):
    return hashlib.sha256(canonical(resolve_profile(profile))).hexdigest()


def bind_profile(profile, expected_hash):
    profile = resolve_profile(profile)
    if profile is not None:
        require(expected_hash == profile_hash(profile), 'PROFILE_HASH_MISMATCH', 'Profile canonical SHA-256 differs')
    else:
        require(expected_hash is None, 'PROFILE_HASH_MISMATCH', 'Hash supplied without a profile')
    return profile


def check_environment(env=None):
    env = os.environ if env is None else env
    bad = sorted(k for k in OVERRIDES if k in env)
    require(not bad, 'UNSUPPORTED_BUILD_OVERRIDE', 'Unset unversioned build overrides: ' + ', '.join(bad))


def declarations(project, profile):
    profile = resolve_profile(profile)
    require(profile is not None, 'INVALID_PROFILE', 'Explicit real-project profile required')
    project = Path(project)
    require(not any(p.is_symlink() for p in project.rglob('*')), 'UNSAFE_PATH', 'Symlinks are not supported')
    data = (project / 'Makefile').read_bytes()
    if profile['id'] == B13_PROJECT_ID:
        from lab import declarations as teaching_declarations
        # The base recipe already declares config.h. On the target accept the
        # two corresponding header additions, independently, retaining all other bytes.
        normalized = data.replace(b'\nmain.o: main.c $(HEADERS) config.h\n', b'\nmain.o: main.c $(HEADERS)\n')
        normalized = normalized.replace(b'\nhelper.o: helper.c extra.h\n', b'\nhelper.o: helper.c\n')
        base, target = profile['makefile_templates']
        require(hashlib.sha256(data).hexdigest() == base or hashlib.sha256(normalized).hexdigest() == target,
                'UNSUPPORTED_MAKEFILE', 'Expected a frozen b13-level-v1 recipe and scoped dependencies')
        declared, _ = teaching_declarations(project)
        return declared, None
    matches = list(re.finditer(rb'^toml\.o: ([^\r\n]*)\n', data, re.M))
    require(len(matches) == 1, 'UNSUPPORTED_MAKEFILE', 'Exactly one standalone toml.o rule required')
    match = matches[0]
    template = data[:match.start()] + b'toml.o: toml.c\n' + data[match.end():]
    require(hashlib.sha256(template).hexdigest() == profile['makefile_template_sha256'],
            'UNSUPPORTED_MAKEFILE', 'Non-target Makefile bytes differ from the audited template')
    try:
        deps = match[1].decode('ascii').split()
    except UnicodeError:
        raise ProfileError('UNSAFE_PATH', 'Dependencies must be audited ASCII paths')
    require(bool(deps) and deps[0] == 'toml.c' and len(deps) == len(set(deps)),
            'UNSUPPORTED_DECLARATION', 'Source first; no duplicate dependencies')
    for name in deps:
        require(re.fullmatch(r'[A-Za-z0-9_-]+\.(?:c|h)', name) is not None,
                'UNSAFE_PATH', 'Only root C/header paths are supported')
        require((project / name).is_file(), 'MISSING_INPUT', name)
    return {'toml.o': deps}, match


def check_project(project, profile):
    declarations(project, profile)
    required = ('toml.c', 'toml.h', 'toml_json.c')
    if profile['id'] == B13_PROJECT_ID:
        require({path.name for path in Path(project).glob('*.c')} == {unit[1] for unit in profile['units']},
                'UNSUPPORTED_PROJECT', 'Unexpected b13-level-v1 compilation units')
        required = ('config.h', 'extra.h', 'unused.h')
    for name in required:
        require((Path(project) / name).is_file(), 'UNSUPPORTED_PROJECT', 'Missing ' + name)
    return True


def run(argv, project, folder=None, label=None, input_bytes=b''):
    p = subprocess.run(argv, cwd=project, input=input_bytes, capture_output=True, timeout=120)
    if folder is not None:
        folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
        (folder / (label + '.command.json')).write_bytes(canonical({'argv': argv, 'stdin_hex': input_bytes.hex()}))
        (folder / (label + '.stdout')).write_bytes(p.stdout)
        (folder / (label + '.stderr')).write_bytes(p.stderr)
        (folder / (label + '.exit.txt')).write_bytes((str(p.returncode) + '\n').encode())
    require(p.returncode == 0, 'COMMAND_FAILED', repr(argv) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout


def effective_toolchain(project, profile, folder=None):
    check_environment(); check_project(project, profile)
    query = b'\n.PHONY: __m2_profile_vars\n__m2_profile_vars:\n\t@printf "%s\\n%s\\n" "$(CFLAGS)" "$(CC)"\n'
    raw = run(['make', '--no-print-directory', '-s', '-f', 'Makefile', '-f', '-', '__m2_profile_vars'],
              project, folder, 'effective-flags', query)
    flags = profile['effective_flags']
    require(raw.splitlines() == [(' '.join(flags)).encode(), b'cc'],
            'UNSUPPORTED_FLAGS', 'Effective Make CFLAGS/CC differ from the versioned release profile')
    cc, gcc = shutil.which('cc'), shutil.which('gcc')
    require(cc is not None and gcc is not None and Path(cc).resolve() == Path(gcc).resolve(),
            'UNSUPPORTED_COMPILER', 'This profile requires cc resolving to the installed GCC')
    version = run(['cc', '--version'], project, folder, 'compiler-version').decode('utf-8')
    return {'compiler': str(Path(cc).resolve()), 'compiler_version': version, 'effective_flags': flags[:],
            'profile_sha256': profile_hash(profile), 'build_argv': profile['build_argv'], 'targets': profile['units']}


def scan(project, old=None, profile=None):
    profile = resolve_profile(profile); check_environment(); check_project(project, profile)
    project = Path(project)
    if profile['id'] == B13_PROJECT_ID:
        from lab import scan as teaching_scan
        digest = profile_hash(profile)
        if old and old.get('profile_sha256') != digest:
            old = None
        report = teaching_scan(project, old)
        report.update(profile=profile['id'], profile_sha256=digest)
        return report
    declared, _ = declarations(project, profile)
    key = effective_toolchain(project, profile)
    # Conservative byte fingerprints; configuration/flags/compiler are part of the key.
    key['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(project.iterdir()) if p.suffix in ('.c', '.h')}
    key['makefile_sha256'] = hashlib.sha256((project / 'Makefile').read_bytes()).hexdigest()
    argv = ['cc', *FLAGS, '-MM', '-MT', 'toml.o', 'toml.c']
    reuse = bool(old and old.get('key') == key and old.get('profile_sha256') == profile_hash(profile)
                 and isinstance(old.get('actual'), dict) and 'toml.o' in old['actual'])
    if reuse:
        actual = copy.deepcopy(old['actual'])
    else:
        raw = run(argv, project).decode('utf-8').replace('\\\n', ' ')
        require(raw.startswith('toml.o:'), 'INVALID_COMPILER_OUTPUT', 'Missing object dependency output')
        deps = raw.split(':', 1)[1].split()
        require(all(re.fullmatch(r'[A-Za-z0-9_-]+\.(?:c|h)', n) for n in deps), 'UNSAFE_PATH', 'Unsupported observed path')
        actual = {'toml.o': sorted(set(deps))}
    findings = []
    for kind, values in [('MISSING', set(actual['toml.o']) - set(declared['toml.o'])),
                         ('REDUNDANT', set(declared['toml.o']) - set(actual['toml.o']))]:
        findings.extend({'type': kind, 'target': 'toml.o', 'dependency': n} for n in sorted(values))
    current = {(f['type'], f['target'], f['dependency']) for f in findings}
    previous = {(f['type'], f['target'], f['dependency']) for f in old.get('findings', [])} if old else set()
    return {'schema_version': 'e8e10-1', 'profile': profile['id'], 'profile_sha256': profile_hash(profile),
            'commit': run(['git', 'rev-parse', 'HEAD'], project).decode().strip(),
            'key': key, 'compiler_argv': argv, 'declared': declared, 'actual': actual, 'findings': findings,
            'added': sorted(current - previous), 'resolved': sorted(previous - current),
            'refreshed': [] if reuse else ['toml.o'], 'reused': ['toml.o'] if reuse else []}


def check_report(report, profile):
    require(isinstance(report, dict) and report.get('schema_version') == 'e8e10-1', 'SCHEMA_MISMATCH', 'Expected e8e10-1')
    require(report.get('profile_sha256') == profile_hash(profile), 'PROFILE_HASH_MISMATCH', 'Report/profile binding differs')
    fs = report.get('findings')
    require(isinstance(fs, list), 'INVALID_REPORT', 'Findings must be a list')
    for f in fs:
        require(isinstance(f, dict) and f.get('type') in ('MISSING', 'REDUNDANT'), 'INVALID_REPORT', 'Invalid finding type')
        require(f.get('target') in profile['repair_targets'], 'UNSUPPORTED_TARGET', 'Only scoped object findings accepted for repair')
        require(isinstance(f.get('dependency'), str) and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:c|h)', f['dependency']),
                'UNSAFE_PATH', 'Unsupported dependency')
        if profile['id'] == B13_PROJECT_ID and f['type'] == 'MISSING':
            require(f['dependency'] == B13_MISSING_HEADERS[f['target']], 'UNSUPPORTED_DEPENDENCY',
                    'Missing header does not belong to this frozen object target')


def patch(project, report, profile):
    profile = resolve_profile(profile); check_report(report, profile)
    project = Path(project)
    require(report.get('commit') == run(['git', 'rev-parse', 'HEAD'], project).decode().strip(), 'STALE_REPORT', 'Report is not for this commit')
    if profile['id'] == B13_PROJECT_ID:
        from lab import patch as teaching_patch
        check_project(project, profile)
        return teaching_patch(project, report)
    declared, match = declarations(project, profile)
    original = (project / 'Makefile').read_bytes()
    missing = sorted({f['dependency'] for f in report['findings'] if f['type'] == 'MISSING'} - set(declared['toml.o']))
    # Complete validation before generating any candidate; original is never modified.
    for name in missing:
        require((project / name).is_file() and not (project / name).is_symlink(), 'MISSING_INPUT', name)
    if not missing:
        return '', []
    changed = original[:match.end()-1] + b' ' + ' '.join(missing).encode() + original[match.end()-1:]
    diff = ''.join(difflib.unified_diff(original.decode().splitlines(True), changed.decode().splitlines(True),
                                        fromfile='a/Makefile', tofile='b/Makefile'))
    return diff, [{'target': 'toml.o', 'dependency': d, 'style': 'audited-explicit-tomlc99'} for d in missing]


def full(project, folder, profile):
    profile = resolve_profile(profile)
    effective = effective_toolchain(project, profile)
    try:
        from fullcheck import full_check
    except ImportError:
        from buildchecker.fullcheck import full_check
    result = full_check(project, folder, clean_command=' '.join(profile['clean_argv']),
                        build_command=' '.join(profile['build_argv']))
    result.update(profile_sha256=profile_hash(profile), effective_toolchain=effective,
                  success_scope=profile['repair_targets'], whole_project_findings=result.get('findings', []))
    result['scoped_findings'] = [f for f in result.get('findings', []) if f['target'] in profile['repair_targets']]
    Path(folder, 'findings.json').write_bytes(canonical(result) + b'\n')
    require(result.get('status') == 'SUCCEEDED', 'FULL_CHECK_FAILED', str(result.get('error')))
    return result


def observed_recompile(trace_dir, profile=None):
    """Require successful compiler exec with the exact versioned argv, not stdout."""
    try:
        from fullcheck import trace_events
    except ImportError:
        from buildchecker.fullcheck import trace_events
    profile = PROFILE if profile is None else resolve_profile(profile)
    target, source = profile['units'][0]
    if profile['id'] == B13_PROJECT_ID:
        expected_args = [*profile['effective_flags'], '-c', source, '-o', target]
        compilers = ('gcc',)
    else:
        expected_args = [*profile['effective_flags'], '-c', '-o', target, source]
        compilers = ('cc', 'gcc')
    found = []
    for path in sorted(Path(trace_dir).glob('t.*')):
        for event in trace_events(path):
            if event['call'] != 'execve' or event['return'] != 0:
                continue
            argv = ast.literal_eval(event['args'][1])
            if isinstance(argv, list) and argv[1:] == expected_args:
                exe = ast.literal_eval(event['args'][0])
                if Path(exe).name in compilers:
                    found.append({'trace': path.name, 'line': event['line'], 'executable': exe, 'argv': argv})
    return found


def validate(project, patchfile, evidence, profile):
    profile = resolve_profile(profile); check_environment(); check_project(project, profile)
    project, evidence = Path(project), Path(evidence)
    before = (project / 'Makefile').read_bytes()
    evidence.mkdir(parents=True, exist_ok=False)
    checks = {}; error = None
    try:
        expected, _ = patch(project, scan(project, profile=profile), profile)
        require(bool(expected) and Path(patchfile).read_bytes() == expected.encode(), 'UNSAFE_PATCH', 'Candidate must be exact scoped missing-dependency patch')
        sandbox = evidence / 'sandbox'
        shutil.copytree(project, sandbox, ignore=shutil.ignore_patterns('.git', '*.o', Path(profile['run_argv'][0]).name,
                                                                        'libtoml.a', 'libtoml.so*', 'toml_cat', 'toml_sample'))
        run(['git', 'init', '-b', 'main'], sandbox, evidence, 'git-init')
        run(['git', 'config', 'user.name', 'ValidationSandbox'], sandbox)
        run(['git', 'config', 'user.email', 'fixture@localhost'], sandbox)
        run(['git', 'add', '.'], sandbox); run(['git', 'commit', '-m', 'sandbox input'], sandbox)
        run(['git', 'apply', '--check', str(Path(patchfile).resolve())], sandbox, evidence, 'patch-check')
        run(['git', 'apply', str(Path(patchfile).resolve())], sandbox, evidence, 'patch-apply'); checks['patch_applies'] = True
        effective_toolchain(sandbox, profile, evidence)
        run(profile['clean_argv'], sandbox, evidence, 'clean')
        run(profile['build_argv'], sandbox, evidence, 'build'); checks['build'] = True
        if 'test_argv' in profile:
            run(profile['test_argv'], sandbox, evidence, 'project-tests')
        checks['test'] = run(profile['run_argv'], sandbox, evidence, 'run-before') == bytes.fromhex(profile['stdout_hex'])
        obj = sandbox / profile['units'][0][0]; old_ns = obj.stat().st_mtime_ns
        time.sleep(1.1)
        header_probe = profile['header_probe']
        header = sandbox / header_probe['path']
        if 'content_hex' in header_probe:
            header.write_bytes(bytes.fromhex(header_probe['content_hex']))
        else:
            header.write_bytes(header.read_bytes() + bytes.fromhex(header_probe['append_hex']))
        require(header.stat().st_mtime_ns > old_ns, 'PROBE_CLOCK', 'Header must be newer than the object')
        traces = evidence / 'incremental-trace'; traces.mkdir()
        argv = ['strace', '-ff', '-s', '4096', '-o', str(traces.resolve() / 't'), '-e', 'trace=execve', *profile['build_argv']]
        run(argv, sandbox, evidence, 'incremental-build')
        observed = observed_recompile(traces, profile)
        probe = {'before_mtime_ns': old_ns, 'after_mtime_ns': obj.stat().st_mtime_ns,
                 'successful_compiler_execs': observed, 'header_sha256': hashlib.sha256(header.read_bytes()).hexdigest()}
        (evidence / 'header-probe.json').write_bytes(canonical(probe) + b'\n')
        checks['header_change'] = bool(observed) and obj.stat().st_mtime_ns > old_ns
        after_stdout = run(profile['run_argv'], sandbox, evidence, 'run-after')
        checks['test'] = checks['test'] and after_stdout == bytes.fromhex(header_probe.get('stdout_hex', profile['stdout_hex']))
        recheck = scan(sandbox, profile=profile)
        (evidence / 'recheck.json').write_bytes(canonical(recheck) + b'\n')
        checks['no_missing'] = not any(f['type'] == 'MISSING' for f in recheck['findings'])
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        error = str(exc)
    accepted = set(checks) == {'patch_applies', 'build', 'test', 'header_change', 'no_missing'} and all(checks.values()) and error is None
    if accepted:
        require((project / 'Makefile').read_bytes() == before, 'SOURCE_CHANGED', 'Source changed during validation')
        (project / 'Makefile').write_bytes((sandbox / 'Makefile').read_bytes())
    unchanged = (project / 'Makefile').read_bytes() == before
    result = {'accepted': accepted, 'checks': checks, 'error': error, 'source_unchanged': unchanged,
              'rollback': not accepted and unchanged, 'profile_sha256': profile_hash(profile), 'success_scope': profile['repair_targets']}
    (evidence / 'validation.json').write_bytes(canonical(result) + b'\n')
    return result
