"""Real Docker acceptance on the preserved red fixture; no mocks or prepare.

Run host mode as member2. The worker creates only fresh outputs; it uses the
original red fixture/marker and independently inspects every execution witness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback
import uuid


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(root).parts}


def run(argv, folder, name, checked=True):
    folder.mkdir(parents=True, exist_ok=True)
    save(folder / (name + '.command.json'), {'argv': argv})
    with (folder / (name + '.stdout.log')).open('wb') as stdout, (folder / (name + '.stderr.log')).open('wb') as stderr:
        p = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=600)
    save(folder / (name + '.exit.json'), {'exit_code': p.returncode})
    require(not checked or p.returncode == 0, 'Command failed: ' + str(folder / name))
    return (folder / (name + '.stdout.log')).read_bytes()


def host(args):
    import pwd
    root = Path(__file__).resolve().parents[2]
    require(os.getuid() == os.geteuid() != 0 and pwd.getpwuid(os.getuid()).pw_name == 'm2_241880091', 'Wrong identity')
    require(root == (Path.home()/'241880091/2026-Devops-B13-e11-e12').resolve(), 'Wrong worktree')
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
    require(branch == 'student/241880091/e11-e12', 'Wrong branch')
    red, out = args.red_out.resolve(), args.out.resolve()
    require(root/'work' in red.parents and root/'work' in out.parents and not out.exists(), 'Use new OUT below work')
    require(red not in out.parents, 'Do not write below red evidence')
    out.mkdir(parents=True)
    image = json.loads(run(['docker', 'image', 'inspect', args.orchestrator_image], out/'host-logs', 'image'))[0]['Id']
    require(re.fullmatch('sha256:[0-9a-f]{64}', image), 'Invalid orchestrator ID')
    save(out/'implementation.json', {'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'files': {p.relative_to(root).as_posix(): digest(p) for folder in ('labs/e11e12','labs/e8e10','course/e11-e12')
                  for p in (root/folder).rglob('*.py')},
        'orchestrator_image_id': image, 'note': 'Uncommitted implementation identified by per-file SHA256; not a new Git SHA'})
    container = lambda p: '/course/' + p.relative_to(root).as_posix()
    cmd = ['docker','run','--rm','--network','bridge','--cap-add','SYS_PTRACE',
        '--user',f'{os.getuid()}:{os.getgid()}','--group-add',str(Path('/var/run/docker.sock').stat().st_gid),
        '-e','HOME=/tmp','-e','PYTHONDONTWRITEBYTECODE=1',
        '-e','PYTHONPATH=/course/labs/e11e12:/course/labs/e8e10:/course/labs/e11e12/vendor:/app',
        '-v',str(root)+':/course:ro','-v',str(root/'data')+':/course/data:ro',
        '-v',str(root/'work')+':/course/work:rw','-v','/var/run/docker.sock:/var/run/docker.sock','-w','/course',image,
        'python3',container(Path(__file__).resolve()),'worker','--red-out',container(red),'--out',container(out),
        '--orchestrator-image',image]
    save(out/'orchestrator-command.json', {'argv': cmd})
    code = subprocess.call(cmd)
    save(out/'worker-exit.json', {'exit_code':code})
    print('MEMBER2_IMAGE_TEST_OUT=' + str(out))
    return code


def worker(args):
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root/'labs/e11e12'),str(root/'labs/e8e10')]
    import pipeline
    from consume_report import consume
    from image_runtime import ImageFailure
    red, out = args.red_out.resolve(), args.out.resolve()
    before = tree(red)
    result = {'status':'RUNNING','scope':'Member2 controlled image reuse; not real-project or A13 acceptance',
              'source_red_out':str(red), 'tests':[], 'limitations':['Real-project configuration/adaptation pending',
              'A13 original delivery pending','HTTP/CI and final-head review require separate runs']}
    try:
        summary = read(red/'summary.json')
        require(summary['status']=='EXPECTED_RED' and summary['expected_red_observed'] is True, 'Expected real red evidence')
        dataset = read(red/'probe-dataset.json')
        require(digest(red/'candidate.Dockerfile') == dataset['candidate_sha256'], 'Red candidate changed')
        require(tree(red/'probe-project') == read(red/'probe-source-hashes-before.json'), 'Red project changed')
        probe = {'path':summary['marker_path'], 'value':summary['marker_token']}
        require(not Path(probe['path']).exists(), 'Marker exists in orchestrator; invalid control')
        request = dict(read(red/'probe-request.json'), image_probe=probe)
        save(out/'green-request.json', request)

        def check(folder, expected_operations, commits):
            report = read(folder/'result.json')
            require(report['status']=='SUCCEEDED' and report['draft_image_reused'] is True, str(report.get('error')))
            ops = report['image_operations']
            require([o['operation'] for o in ops]==expected_operations, 'Missing/wrong image operation sequence')
            require([o['project_commit'] for o in ops]==commits, 'Wrong base/target execution version')
            for index, op in enumerate(ops, 1):
                require(op['image_id']==op['actual_container_image']==report['draft_image_id'], 'Actual image mismatch')
                require(op['container_exit_code']==0 and op['marker']==dict(probe, observed=True), 'Missing observed marker')
                raw = folder/'image-execution'/('%02d-' % index + op['operation'])
                inspected = [read(p)[0] for p in raw.glob('*-inspect.stdout.log')]
                require(len(inspected)==2 and all(x['Image']==op['image_id'] for x in inspected), 'Missing raw Docker inspect')
                require(inspected[-1]['State']['ExitCode']==0, 'Container exit failed')
                response = read(raw/'output/response.json')
                require(response['marker']==op['marker'] and response['tools']==op['tools'], 'Witness/worker mismatch')
            result['tests'].append({'case':folder.name,'status':'PASS','image_id':report['draft_image_id'],
                                    'operations':expected_operations})
            return report

        actual = pipeline.execute(request,out/'e12')
        require(actual['status']=='SUCCEEDED', 'E12: '+str(actual.get('error')))
        c0,c1 = dataset['base_commit'], dataset['target_commit']
        e12 = check(out/'e12',['full','scan','scan','full','validate','full'],[c0,c0,c1,c1,c1,c1])
        require([x['name'] for x in e12['stages']]==['draft','full-check','incremental-check','repair','recheck'], 'E12 stages incomplete')
        for name in ('full-check','incremental-check','repair','recheck'):
            envelope=read(out/'e12'/(name+'.json'))
            require(envelope['job_id']==e12['job_id'] and envelope['trace_id']==e12['trace_id'], 'Envelope identity mismatch')
            require(envelope['commit']==(c0 if name=='full-check' else c1), 'Envelope commit mismatch')
        md=out/'e12/incremental-check.json'
        consumed_ref=read(out/'e12/repair.json')['data']['input_report']
        require(consumed_ref['sha256']==digest(md), 'Repair did not reference actual incremental envelope')

        # Fixed E11-B report retains its target and originates from the saved real local scan.
        payload=read(red/'local-report-delivery/incremental-report.json')
        fixed=out/'fixed-md.json'
        save(fixed,{'schema_version':'e11e12-1','kind':'fixed-md','status':'SUCCEEDED','commit':c1,'data':payload})
        fixed_request=dict(request,mode='e11-b',fixed_report=str(fixed))
        pipeline.execute(fixed_request,out/'e11-b')
        check(out/'e11-b',['validate','full'],[c1,c1])

        env=read(md); payload_file=out/'e12/incremental-report.json'
        def consume_to(folder,image,marker=probe):
            return consume(md,digest(md),payload_file,digest(payload_file),Path(request['repo']),c1,
                env['job_id'],env['trace_id'],folder,source_label='local-member2-image-acceptance-not-A13',
                image_id=image,image_probe=marker)
        consume_to(out/'consumer',e12['draft_image_id'])
        check(out/'consumer',['validate','full'],[c1,c1])
        for name in ('incremental-check.json','incremental-report.json'):
            require((out/'consumer/received'/name).read_bytes()==(out/'e12'/name).read_bytes(), 'Received raw bytes changed')

        for label,image in [('mutable-tag','python:latest'),('missing-id',None)]:
            folder=out/label
            try:
                consume_to(folder,image)
            except ImageFailure as exc:
                require(exc.code=='INVALID_IMAGE_ID' and not folder.exists(), 'Invalid image was not rejected before output creation')
                result['tests'].append({'case':label,'status':'PASS','rejection':exc.code})
            else:
                raise ValueError('Invalid image accepted')
        for label,image in [('absent-image','sha256:'+'0'*64),('wrong-environment',args.orchestrator_image)]:
            rejected=consume_to(out/label,image)
            require(rejected['status']=='FAILED' and rejected['working_copy_makefile_restored'] is True
                    and rejected['draft_image_reused'] is False, 'Negative environment was accepted')
            require(not rejected['image_operations'], 'Unexpected successful operation in negative control')
            if label=='wrong-environment':
                response=read(out/label/'image-execution/01-validate/output/response.json')
                require(probe['path'] in response['error'], 'Wrong-environment failure was unrelated to marker')
            result['tests'].append({'case':label,'status':'PASS','rejection':rejected['error']})

        # Derive a separate local image with strace removed. Never mutate the successful image.
        context=out/'missing-tool-build'; context.mkdir()
        base_tag='member2-missing-tool-base:'+uuid.uuid4().hex
        run(['docker','image','tag',e12['draft_image_id'],base_tag],context,'tag')
        inspected=json.loads(run(['docker','image','inspect',base_tag],context,'inspect'))[0]
        require(inspected['Id']==e12['draft_image_id'], 'Negative build base does not match DRAFT image')
        (context/'Dockerfile').write_text('FROM '+base_tag+'\nUSER root\nRUN rm /usr/bin/strace\n')
        run(['docker','build','--network','none','--iidfile',str(context/'image.id'),str(context)],context,'build')
        missing_id=(context/'image.id').read_text().strip()
        require(missing_id != e12['draft_image_id'], 'Negative image equals successful image')
        rejected=consume_to(out/'missing-tool',missing_id)
        response=read(out/'missing-tool/image-execution/01-validate/output/response.json')
        require(rejected['status']=='FAILED' and rejected['working_copy_makefile_restored'] is True
                and rejected['draft_image_reused'] is False and response['error']=='IMAGE_TOOL_MISSING: strace',
                'Missing tool silently fell back or failed for another reason')
        result['tests'].append({'case':'missing-tool','status':'PASS','image_id':missing_id,'error':response['error']})
        require(tree(red)==before, 'Red evidence changed')
        require(not Path(probe['path']).exists(), 'Marker appeared in orchestrator')
        result.update(status='PASS',red_evidence_unchanged=True,orchestrator_marker_absent=True,
                      draft_image_id=e12['draft_image_id'])
    except Exception as exc:
        result.update(status='FAIL',error=str(exc),traceback=traceback.format_exc())
    finally:
        result['red_evidence_unchanged']=tree(red)==before
        if not result['red_evidence_unchanged']:
            result['status']='FAIL'
        save(out/'summary.json',result)
        print(json.dumps(result,indent=2),flush=True)
    return 0 if result['status']=='PASS' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['host','worker'])
    p.add_argument('--red-out',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--orchestrator-image',required=True)
    args=p.parse_args()
    try:
        return host(args) if args.mode=='host' else worker(args)
    except Exception as exc:
        print('STOP: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
