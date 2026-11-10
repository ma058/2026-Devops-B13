"""Member 1 macro integration and real historical-report evidence driver.

Run INSIDE the E11-E12 Linux teaching environment, with Docker socket for run.
This generates an explicitly labelled teaching extension, not a real project.
No successful Docker, compiler, detector or pipeline result is simulated.

python3 course/e11-e12/member1_cases.py prepare
python3 course/e11-e12/member1_cases.py run --out work/member1-cases-UNIQUE
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'labs/e11e12'))
import pipeline
from lab import commit, fixture, run, scan


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_bytes(project):
    return {name: (project / name).read_bytes()
            for name in run(['git', 'ls-files'], project).splitlines()}


def snapshot(project, destination):
    files = source_bytes(project)
    for name, content in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    pipeline.save(destination / 'sha256.json', {
        name: hashlib.sha256(content).hexdigest() for name, content in files.items()})
    return files


def prepare(destination):
    require(not destination.exists(), 'Preserve existing data; choose a new --data path')
    project = destination / 'repo'
    fixture(project, 'macro')
    broken = ('FROM python:3.13-slim\nWORKDIR /work\n'
              'COPY main.c helper.c config.h extra.h unused.h Makefile ./\n'
              'RUN make app\nCMD ["./app"]\n')
    (project / 'Dockerfile.broken').write_text(broken, encoding='utf-8')
    base = commit(project, 'member1 macro C0 with build environment fault')
    old = scan(project)
    pipeline.save(destination / 'old-fixed-md.json', {
        'schema_version': 'e11e12-1', 'kind': 'fixed-md', 'status': 'SUCCEEDED',
        'commit': base, 'data': old})
    (project / 'main.c').write_text('#include "extra.h"\n' + (project / 'main.c').read_text())
    target = commit(project, 'member1 macro C1 adds actual extra.h dependency')
    current = scan(project)
    require(base != target, 'Expected distinct real Git commits')
    require({(f['type'], f['target'], f['dependency']) for f in current['findings']} == {
        ('MISSING', 'main.o', 'config.h'), ('MISSING', 'main.o', 'extra.h'),
        ('REDUNDANT', 'main.o', 'unused.h')}, 'Unexpected macro fixed input')
    pipeline.save(destination / 'fixed-md.json', {
        'schema_version': 'e11e12-1', 'kind': 'fixed-md', 'status': 'SUCCEEDED',
        'commit': target, 'data': current})
    pinned = ('FROM python:3.13-slim@sha256:'
              '70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f')
    candidate = broken.replace('FROM python:3.13-slim', pinned).replace(
        'RUN make app', 'RUN apt-get update && apt-get install -y --no-install-recommends '
        'build-essential && rm -rf /var/lib/apt/lists/*\nRUN make app')
    (destination / 'candidate.Dockerfile').write_text(candidate, encoding='utf-8')
    request = {'mode': 'e11-b', 'repo': str(project), 'base': base, 'target': target,
               'candidate': str(destination / 'candidate.Dockerfile'),
               'fixed_report': str(destination / 'fixed-md.json'),
               'expected_output': '1', 'build_timeout': 600}
    pipeline.save(destination / 'e11-b.json', request)
    pipeline.save(destination / 'e11-stale.json', dict(request, fixed_report=str(destination / 'old-fixed-md.json')))
    pipeline.save(destination / 'e12.json', dict(request, mode='e12'))
    snapshot(project, destination / 'source-before')
    pipeline.save(destination / 'dataset.json', {
        'source': 'course-generated macro extension by member1; NOT a real project',
        'base_commit': base, 'target_commit': target, 'student': '241880054',
        'style': 'macro', 'old_report_source': 'actual scan at C0 before C1 commit',
        'candidate_source': 'Saved teaching dependency-install pattern; no online model call',
        'scope': 'Controlled fixture integration; real-project and A13 acceptance remain separate'})


def verify_manifest(result, out):
    for item in result['artifacts']:
        prefix = 'artifact://' + result['job_id'] + '/'
        require(item['uri'].startswith(prefix), 'Foreign job artifact URI')
        path = (out / item['uri'][len(prefix):]).resolve()
        require(path.is_relative_to(out.resolve()) and path.is_file(), 'Invalid artifact location')
        content = path.read_bytes()
        require(len(content) == item['bytes'], 'Artifact size mismatch')
        require(hashlib.sha256(content).hexdigest() == item['sha256'], 'Artifact SHA mismatch')


def verify_success(result, out, request):
    require(result['status'] == 'SUCCEEDED', 'Pipeline failed: ' + str(result.get('error')))
    stage_names = ['draft', 'fixed-md', 'repair', 'recheck'] if request['mode'] == 'e11-b' else [
        'draft', 'full-check', 'incremental-check', 'repair', 'recheck']
    require([s['name'] for s in result['stages']] == stage_names, 'Unexpected stage sequence')
    for name in stage_names:
        env = json.loads((out / (name + '.json')).read_text())
        require(env['job_id'] == result['job_id'] and env['trace_id'] == result['trace_id'],
                'Stage job/trace mismatch')
        pipeline.check_envelope(env, request['base'] if name == 'full-check' else request['target'], name)
    draft = json.loads((out / 'draft-build/result.json').read_text())
    require(draft['status'] == 'SUCCEEDED' and len(draft['attempts']) == 2, 'Wrong DRAFT outcome')
    require(draft['attempts'][0]['build_exit_code'] != 0
            and draft['attempts'][0]['failure_class'] == 'MISSING_MAKE', 'Wrong baseline failure')
    require(draft['attempts'][1]['build_exit_code'] == 0 and draft['verification']['exit_code'] == 0
            and draft['verification']['actual_output'].strip() == '1', 'Image did not run correctly')
    input_name = 'fixed-md' if request['mode'] == 'e11-b' else 'incremental-check'
    repair = json.loads((out / 'repair.json').read_text())
    require(repair['data']['input_report'] == pipeline.artifact(out / (input_name + '.json'), out, result['job_id']),
            'Repair did not reference this exact report artifact')
    require(repair['data']['edits'] == [
        {'target': 'main.o', 'dependency': 'config.h', 'style': 'macro'},
        {'target': 'main.o', 'dependency': 'extra.h', 'style': 'macro'}], 'Wrong macro plan')
    before = (Path(request['repo']) / 'Makefile').read_text()
    expected = before.replace('DEPS = main.c unused.h\n', 'DEPS = main.c unused.h config.h extra.h\n')
    require((out / 'target-project/Makefile').read_text() == expected, 'Changed non-macro declaration/recipe/RD')
    verdict = json.loads((out / 'validation/validation.json').read_text())
    require(verdict['accepted'] and all(verdict['checks'].values()) and verdict['error'] is None,
            'Candidate acceptance checks incomplete')
    final = json.loads((out / 'final-full/findings.json').read_text())
    require(not any(f['type'] == 'MISSING' for f in final['findings']), 'Final dynamic MD remains')
    require(any(f['type'] == 'REDUNDANT' and f['dependency'] == 'unused.h' for f in final['findings']),
            'Expected preserved RD absent')
    verify_manifest(result, out)
    return {'job_id': result['job_id'], 'trace_id': result['trace_id'], 'status': result['status'],
            'stages': stage_names, 'artifacts_verified': len(result['artifacts']),
            'accepted': True, 'macro_definition_only': True, 'rd_preserved': True}


def execute_cases(data, out):
    require(not out.exists(), 'Use a new evidence output directory')
    out.mkdir(parents=True)
    project = data / 'repo'
    before = snapshot(project, out / 'source-before')
    report_bytes = {name: (data / name).read_bytes() for name in ('fixed-md.json', 'old-fixed-md.json')}
    summary = {'student': '241880054', 'passed': False, 'cases': {},
               'scope': 'Local controlled macro integration; not real-project or A13 remote evidence'}
    try:
        for name in ('e11-b', 'e11-stale', 'e12'):
            request = json.loads((data / (name + '.json')).read_text())
            result = pipeline.execute(request, out / name)
            if name == 'e11-stale':
                require(result['status'] == 'FAILED' and result['error']['code'] == 'STALE_REPORT',
                        'Historical report was not rejected for version mismatch')
                require([stage['name'] for stage in result['stages']] == ['draft'],
                        'Stale input reached repair stages')
                require(not (out / name / 'candidate.patch').exists(), 'Stale input generated a patch')
                require((out / name / 'target-project/Makefile').read_bytes() == before['Makefile'],
                        'Stale rejection changed copied target source')
                verify_manifest(result, out / name)
                summary['cases'][name] = {'passed': True, 'expected_failure': result['error'],
                                         'job_id': result['job_id'], 'trace_id': result['trace_id']}
            else:
                summary['cases'][name] = verify_success(result, out / name, request)
            require(source_bytes(project) == before, 'Pipeline changed original data repository')
            require(all((data / name).read_bytes() == content for name, content in report_bytes.items()),
                    'Fixed report was relabelled or changed')
            print('PASS ' + name, flush=True)
        snapshot(project, out / 'source-after')
        summary['passed'] = True
        summary['source_unchanged'] = True
        summary['fixed_reports_unchanged'] = True
    finally:
        pipeline.save(out / 'summary.json', summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'run'])
    parser.add_argument('--data', type=Path, default=ROOT / 'data/member1-macro')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    data = args.data.resolve()
    require(data.is_relative_to((ROOT / 'data').resolve()) and data != ROOT / 'data',
            'Data must be a fresh child of repository data/')
    if args.stage == 'prepare':
        prepare(data)
    else:
        parser.error('--out is required for run') if args.out is None else None
        out = args.out.resolve()
        require(out.is_relative_to((ROOT / 'work').resolve()) and out != ROOT / 'work',
                'Output must be a fresh child of repository work/')
        execute_cases(data, out)


if __name__ == '__main__':
    main()
