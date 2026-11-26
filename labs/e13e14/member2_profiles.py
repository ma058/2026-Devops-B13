"""Closed profile registry for E14; preserves E11/E12 implementations unchanged."""
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT/'labs/e11e12', ROOT/'labs/e8e10', ROOT/'labs/e11e12/environment/services/buildchecker'):
    sys.path.insert(0, str(path))
import project_profile as legacy
import lab

FULL_PREVIEW_ID = 'b13-tomlc99-full-preview-v1'
PREVIEW_ENV = 'E14_TOMLC99_FULL_PREVIEW'


def full_preview_enabled():
    return os.environ.get(PREVIEW_ENV) == '1'


def full_preview_profile():
    if not full_preview_enabled():
        raise ValueError('UNSUPPORTED_PROFILE')
    bundled = Path(__file__).with_name('tomlc99-full-preview.json')
    path = bundled if bundled.is_file() else ROOT/'course/e13-e14/projects'/FULL_PREVIEW_ID/'profile.json'
    registered = json.loads(path.read_bytes())
    if digest(canonical(registered)) != 'b051e3169de0d482692c18f35204bd54b19ebe32cc9cbfa4e5eef9d4ae5d4368':
        raise ValueError('PROFILE_HASH_MISMATCH')
    return registered

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()

def digest(value):
    return hashlib.sha256(value).hexdigest()

def b_profile():
    bundled = Path(__file__).with_name('b13-profile.json')
    return json.loads((bundled if bundled.exists() else ROOT/'course/e13-e14/projects/b13-level-v1/profile.json').read_bytes())

def resolve(raw, expected=None):
    if not isinstance(raw, dict):
        raise ValueError('PROFILE_REQUIRED')
    if raw.get('id') == FULL_PREVIEW_ID:
        if canonical(raw) != canonical(full_preview_profile()):
            raise ValueError('UNSUPPORTED_PROFILE')
    elif canonical(raw) not in (canonical(b_profile()), canonical(legacy.PROFILE)):
        raise ValueError('UNSUPPORTED_PROFILE')
    if expected is not None and expected != digest(canonical(raw)):
        raise ValueError('PROFILE_HASH_MISMATCH')
    return copy.deepcopy(raw)

def check(project, profile):
    profile = resolve(profile)
    legacy.check_environment()
    project = Path(project)
    if any(p.is_symlink() for p in project.rglob('*')):
        raise ValueError('UNSAFE_PATH')
    if profile['id'] == FULL_PREVIEW_ID:
        import member2_tomlc99_full
        return member2_tomlc99_full.check(project, profile)
    if profile['id'] == legacy.PROFILE['id']:
        return legacy.check_project(project, profile)
    if {p.name for p in project.glob('*.c')} != {'main.c', 'helper.c'}:
        raise ValueError('UNSUPPORTED_LAYOUT')
    if not all((project/n).is_file() for n in ('config.h', 'extra.h', 'unused.h')):
        raise ValueError('UNSUPPORTED_LAYOUT')
    raw = (project/'Makefile').read_bytes()
    # Normalize only optional missing-header insertions, preserving macros/recipes.
    normalized = re.sub(rb'^main\.o: main\.c(?: config\.h)? \$\(HEADERS\)(?: config\.h)?$',
                        b'main.o: main.c $(HEADERS)', raw, flags=re.M)
    normalized = re.sub(rb'^helper\.o: helper\.c(?: extra\.h)?$', b'helper.o: helper.c', normalized, flags=re.M)
    # Base has a different check recipe, so normalize its original header too.
    base = profile['makefile_templates'][0]
    target = profile['makefile_templates'][1]
    if digest(raw) != base and digest(normalized) != target:
        raise ValueError('UNSUPPORTED_MAKEFILE')
    declarations, flags = lab.declarations(project)
    if flags != '-O0' or set(declarations) != {'main.o','helper.o'}:
        raise ValueError('UNSUPPORTED_FLAGS_OR_TARGETS')
    return True

def scan(project, old, profile):
    check(project, profile)
    if profile['id'] == FULL_PREVIEW_ID:
        import member2_tomlc99_full
        report = member2_tomlc99_full.scan(project, old, profile)
        report['profile_sha256'] = digest(canonical(profile))
        return report
    report = legacy.scan(project, old, profile) if profile['id'] == legacy.PROFILE['id'] else lab.scan(project, old)
    report['profile_sha256'] = digest(canonical(profile))
    return report

def patch(project, report, profile):
    check(project, profile)
    if report.get('profile_sha256') != digest(canonical(profile)):
        raise ValueError('PROFILE_HASH_MISMATCH')
    if report.get('commit') != subprocess.check_output(['git','rev-parse','HEAD'],cwd=project,text=True).strip():
        raise ValueError('STALE_REPORT')
    if profile['id'] == FULL_PREVIEW_ID:
        import member2_tomlc99_full
        return member2_tomlc99_full.patch(project, report, profile)
    if any(f.get('target') not in profile['repair_targets'] for f in report.get('findings', [])):
        raise ValueError('UNSUPPORTED_TARGET')
    return legacy.patch(project, report, profile) if profile['id'] == legacy.PROFILE['id'] else lab.patch(Path(project), report)

def full(project, out, profile, timeout):
    check(project, profile)
    from fullcheck import full_check
    result = full_check(project, out, clean_command=' '.join(profile['clean_argv']),
                        build_command=' '.join(profile['build_argv']), timeout=timeout)
    findings = result.get('findings')
    targets = profile['products'] if profile['id'] == FULL_PREVIEW_ID else profile['repair_targets']
    result.update(profile_sha256=digest(canonical(profile)), success_scope=targets,
                  whole_project_findings=findings, findings_by_scope=None)
    if result['status'] == 'SUCCEEDED':
        if profile['id'] == FULL_PREVIEW_ID and set(result.get('observed_targets', [])) != set(targets):
            raise ValueError('INVALID_FULL_FINDINGS')
        if not isinstance(findings, list) or any(
            not isinstance(item, dict) or item.get('type') not in ('MISSING', 'REDUNDANT')
            or not all(isinstance(item.get(key), str) and item[key] for key in ('target', 'dependency'))
            for item in findings
        ):
            raise ValueError('INVALID_FULL_FINDINGS')
        inside = [item for item in findings if item['target'] in targets]
        outside = [item for item in findings if item['target'] not in targets]
        result['findings_by_scope'] = {
            'in_scope': inside, 'out_of_scope': outside,
            'in_scope_missing': sum(item['type'] == 'MISSING' for item in inside),
            'out_of_scope_missing': sum(item['type'] == 'MISSING' for item in outside),
        }
    (Path(out)/'findings.json').write_bytes(canonical(result)+b'\n')
    return result

def validate(project, patchfile, out, profile):
    check(project, profile)
    if profile['id'] == FULL_PREVIEW_ID:
        import member2_tomlc99_full
        return member2_tomlc99_full.validate(project, patchfile, out, profile)
    if profile['id'] == legacy.PROFILE['id']:
        return legacy.validate(project, patchfile, out, profile)
    project, out = Path(project), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    sandbox = out/'sandbox'
    shutil.copytree(project, sandbox, ignore=shutil.ignore_patterns('.git', '*.o', 'app', 'app.exe'))
    before = (project/'Makefile').read_bytes()
    checks = {}; error = None
    def command(label, argv):
        p = subprocess.run(argv, cwd=sandbox, capture_output=True, timeout=120)
        (out/(label+'.stdout')).write_bytes(p.stdout);(out/(label+'.stderr')).write_bytes(p.stderr)
        (out/(label+'.command.json')).write_bytes(canonical({'argv':argv,'exit_code':p.returncode}))
        if p.returncode: raise ValueError(label+': '+p.stderr.decode(errors='replace'))
        return p.stdout
    try:
        command('init',['git','init','-q'])
        command('apply-check',['git','apply','--check',str(Path(patchfile).resolve())])
        command('apply',['git','apply',str(Path(patchfile).resolve())]);checks['patch_applies']=True
        check(sandbox, profile)
        command('clean',profile['clean_argv']);command('build',profile['build_argv']);checks['build']=True
        command('self-tests',profile['test_argv'])
        checks['test']=command('run-before',profile['run_argv'])==bytes.fromhex(profile['stdout_hex'])
        obj=sandbox/'main.o';old_ns=obj.stat().st_mtime_ns;time.sleep(1.1)
        (sandbox/'config.h').write_bytes(bytes.fromhex(profile['header_probe']['content_hex']))
        command('rebuild',profile['build_argv'])
        checks['header_change']=(obj.stat().st_mtime_ns>old_ns and command('run-after',profile['run_argv'])==b'2\n')
        # lab.scan only needs the commit for identity, preserved separately by the worker.
        command('git-name',['git','config','user.name','ValidationSandbox'])
        command('git-email',['git','config','user.email','sandbox@example.invalid'])
        command('git-add',['git','add','.']);command('git-commit',['git','commit','-qm','validation sandbox'])
        result=scan(sandbox,None,profile)
        checks['no_missing']=not any(f['type']=='MISSING' for f in result['findings'])
        (out/'recheck.json').write_bytes(canonical(result)+b'\n')
        (out/'header-probe.json').write_bytes(canonical({'before_mtime_ns':old_ns,'after_mtime_ns':obj.stat().st_mtime_ns}))
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        error=str(exc)
    accepted=len(checks)==5 and all(checks.values()) and error is None
    if accepted:
        if (project/'Makefile').read_bytes()!=before:raise ValueError('SOURCE_CHANGED')
        (project/'Makefile').write_bytes((sandbox/'Makefile').read_bytes())
    result={'accepted':accepted,'checks':checks,'error':error,'rollback':not accepted,
            'source_unchanged':(project/'Makefile').read_bytes()==before,
            'profile_sha256':digest(canonical(profile)),'success_scope':profile['repair_targets']}
    (out/'validation.json').write_bytes(canonical(result)+b'\n')
    return result
