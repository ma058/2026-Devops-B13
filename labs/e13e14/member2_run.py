"""Member2 normal/C4/C5 runner; actual Linux four-role service execution only."""
import argparse,json,os,shutil,subprocess,tarfile,tempfile,time,urllib.request,urllib.error,uuid
from pathlib import Path
from member2_faults import SCENARIOS
from member2_profiles import canonical,digest
from member2_runtime import fingerprint,save

ROOT=Path(__file__).resolve().parents[2]

def scenario_config(path, scenario):
    conf=json.loads(Path(path).read_bytes())
    if conf.get('scenario')!=scenario:
        raise ValueError(f'CONFIG_SCENARIO_MISMATCH: prepare a fresh {scenario} stack')
    return conf

def health(ports):
    checks={}
    for role,port in ports.items():
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=5) as response:
            value=json.load(response)
        if (value.get('status'),value.get('role'),value.get('protocol'))!=('ok',role,'member2-e14-1'):
            raise ValueError(f'HEALTH_PROTOCOL_OR_ROLE_MISMATCH: {role}')
        checks[role]=value
    return checks

def project_inputs(config):
    project_id = config.get('project_id', 'b13-level-v1')
    if project_id not in ('b13-level-v1', 'b13-tomlc99-full-preview-v1'):
        raise ValueError('UNSUPPORTED_PROJECT')
    directory = ROOT / 'course/e13-e14/projects' / project_id
    return directory, json.loads((directory / 'manifest.json').read_bytes())


def restore_sources(directory, manifest, folder):
    def git(*argv):
        subprocess.run(['git', *map(str, argv)], check=True, stdout=subprocess.PIPE)
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        source = directory / 'project.bundle'
        if manifest['project_id'] == 'b13-tomlc99-full-preview-v1':
            archive = directory.parent / 'a13-tomlc99-release-1' / 'project.git.tar.gz'
            if digest(archive.read_bytes()) != manifest['source_archive_sha256']:
                raise ValueError('SOURCE_ARCHIVE_MISMATCH')
            # The frozen archive holds a shallow bare Git repository.
            with tarfile.open(archive, 'r:gz') as tar:
                for member in tar:
                    path = Path(member.name)
                    if path.parts[:1] != ('project.git',) or '..' in path.parts:
                        raise ValueError('INVALID_SOURCE_ARCHIVE_PATH')
                    target = Path(temporary) / path
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with tar.extractfile(member) as contents, target.open('xb') as output:
                            shutil.copyfileobj(contents, output)
                    else:
                        raise ValueError('INVALID_SOURCE_ARCHIVE_ENTRY')
            source = Path(temporary) / 'project.git'
        for side in ('base', 'target'):
            dest = folder / side
            git('clone', '--no-checkout', '--no-hardlinks', source, dest)
            git('-C', dest, 'config', 'core.autocrlf', 'false')
            git('-C', dest, 'checkout', '--detach', manifest[side])
            if fingerprint(dest) != manifest[side + '_files']:
                raise ValueError('SOURCE_FINGERPRINT_MISMATCH')


def run(config,scenario):
    conf=scenario_config(config,scenario);runroot=ROOT/conf['run_relative']
    directory,m=project_inputs(conf)
    token=Path(conf['token_file']).read_text().strip()
    if os.name!='posix' or os.getuid()==0 or os.getuid()!=os.geteuid():raise ValueError('NONROOT_LINUX_REQUIRED')
    if conf['uid']!=os.getuid():raise ValueError('CONFIG_OWNER_MISMATCH')
    uid=os.getuid();job='job-'+uuid.uuid4().hex;trace='trace-'+uuid.uuid4().hex
    folder=runroot/'jobs'/job;folder.mkdir(parents=True,exist_ok=False)
    save(folder/'health.json',health(conf['ports']))
    http=folder/'http';http.mkdir();counter=0
    def cpath(p):return '/course/'+Path(p).resolve().relative_to(ROOT.resolve()).as_posix()
    def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.STDOUT)
    restore_sources(directory,m,folder)
    data={k:m[k] for k in ['base','target','profile','profile_sha256','candidate_sha256']}
    data.update(protocol='member2-e14-1',project_id=m['project_id'],job_id=job,trace_id=trace)
    source=ROOT/'data'/conf['run_name']/'candidate.Dockerfile'
    before=fingerprint(folder/'target');git_before=git('-C',str(folder/'target'),'status','--porcelain','--untracked-files=all')
    save(folder/'source-before.json',before);(folder/'git-before.txt').write_bytes(git_before)
    def snapshot(name, entries):
        destination=folder/name;destination.mkdir(exist_ok=False)
        for relative,expected in entries.items():
            source=folder/'target'/relative
            raw=source.read_bytes()
            if digest(raw)!=expected:raise ValueError('SOURCE_CHANGED_DURING_SNAPSHOT')
            output=destination/relative;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
    snapshot('source-before-bytes',before)
    def call(role,name,project='target',**extra):
        nonlocal counter
        counter+=1
        payload=dict(data,project=cpath(folder/project),out=cpath(folder/name),**extra)
        save(http/f'{counter:02d}-{name}-request.json',payload)
        req=urllib.request.Request(f"http://127.0.0.1:{conf['ports'][role]}/v1/run",data=canonical(payload),
             headers={'Content-Type':'application/json','X-E14-Token':token})
        start=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=2000) as response:raw=response.read();status=response.status
        except urllib.error.HTTPError as exc:raw=exc.read();status=exc.code
        (http/f'{counter:02d}-{name}-response.json').write_bytes(raw)
        save(http/f'{counter:02d}-{name}-http.json',{'status':status,'elapsed_seconds':time.monotonic()-start})
        result=json.loads(raw)
        if status!=200:raise ValueError(f'{name}: HTTP {status}: '+str(result))
        return result
    result={'project_id':m['project_id'],'status':'FAILED','scenario':scenario,'job_id':job,'trace_id':trace,'uid':uid,
            'implementation_sha':git('-C',str(ROOT),'rev-parse','HEAD').decode().strip(),
            'profile_sha256':m['profile_sha256'],'candidate_sha256':m['candidate_sha256'],'base':m['base'],'target':m['target']}
    try:
        draft=call('draft','draft',candidate=cpath(source),build_timeout=900)
        assert draft['status']=='SUCCEEDED',draft
        data['image_id']=draft['image_id'];result['image_id']=draft['image_id']
        if scenario=='C4':
            timed=call('buildchecker','timeout-full',fault='sleep',timeout_seconds=1)
            assert timed['status']=='TIMED_OUT' and timed['cleanup_verified'] and timed['source_unchanged'],timed
            cleanup=json.loads((folder/'timeout-full/runtime/cleanup.json').read_bytes())
            assert cleanup['verified_no_owned_containers'] and cleanup['removed']
            ps=subprocess.run(['docker','ps','-aq','--filter','label=b13.e14.operation='+cleanup['ownership_label']],capture_output=True,check=True)
            (folder/'timeout-daemon-residual.txt').write_bytes(ps.stdout)
            assert not ps.stdout.strip()
            assert fingerprint(folder/'target')==before
            result.update(status='EXPECTED_TIMEOUT_VERIFIED',cleanup=cleanup,source_unchanged=True,recovery='REQUIRES_NEW_NORMAL_JOB')
        else:
            basefull=call('buildchecker','baseline-full',project='base');assert basefull['status']=='SUCCEEDED',basefull
            targetfull=call('buildchecker','target-full');assert targetfull['status']=='SUCCEEDED',targetfull
            graph=folder/'baseline-full/actual-graph.json';findings=folder/'target-full/findings.json'
            increment=call('echecker','incremental',base_project=cpath(folder/'base'),baseline_graph=cpath(graph),baseline_graph_sha256=digest(graph.read_bytes()),target_findings=cpath(findings),target_findings_sha256=digest(findings.read_bytes()))
            assert increment['status']=='SUCCEEDED',increment
            refs={k:increment[k] for k in ['report','report_sha256','payload','payload_sha256']}
            if scenario=='C5':
                bad=call('mdfixer','bad-repair',fault_patch=True,**refs)
                assert bad['status']=='REJECTED' and not bad['payload']['accepted'],bad
                assert bad['payload']['rollback'] and bad['payload']['source_unchanged']
                after=fingerprint(folder/'target');git_after=git('-C',str(folder/'target'),'status','--porcelain','--untracked-files=all')
                save(folder/'after-bad-source.json',after);(folder/'after-bad-git.txt').write_bytes(git_after)
                snapshot('source-after-bad-bytes',after)
                assert before==after and git_before==git_after
                stderr=folder/'bad-repair/runtime/output/evidence/apply-check.stderr'
                assert stderr.is_file() and stderr.read_bytes()
                result['C5']={'accepted':False,'complete_source_unchanged':True,'git_status_unchanged':True,'stderr':str(stderr.relative_to(folder))}
            good=call('mdfixer','repair',**refs)
            assert good['status']=='SUCCEEDED' and good['payload']['accepted'] and all(good['payload']['checks'].values()),good
            final=call('buildchecker','final-full');assert final['status']=='SUCCEEDED',final
            remaining=[f for f in final['result']['findings'] if f['type']=='MISSING']
            assert not remaining,remaining
            changed=[n for n,h in before.items() if fingerprint(folder/'target').get(n)!=h]
            assert changed==['Makefile'],changed
            snapshot('source-after-good-bytes',fingerprint(folder/'target'))
            result.update(status='PASS',remaining_missing=remaining,changed_sources=changed)
    except Exception as exc:result.update(status='FAILED',error=str(exc))
    save(folder/'summary.json',result)
    refs={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
          for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink() and '.git' not in p.parts}
    save(folder/'MANIFEST.json',refs)
    print(json.dumps(result,indent=2),flush=True)
    return result,folder

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--scenario',choices=(*SCENARIOS,'all'),default='normal')
    parser.add_argument('--c4-config',help='separate C4 deployment for an explicit matrix')
    parser.add_argument('--c5-config',help='separate C5 deployment for an explicit matrix')
    args=parser.parse_args()
    jobs=[(args.config,args.scenario)]
    if args.scenario=='all':
        if not args.c4_config or not args.c5_config:
            parser.error('--scenario all requires independent --c4-config and --c5-config')
        jobs=[(args.config,'normal'),(args.c4_config,'C4'),(args.config,'normal'),(args.c5_config,'C5')]
    for config,scenario in jobs:
        scenario_config(config,scenario)
    records=[]
    for config,scenario in jobs:
        result,folder=run(config,scenario);records.append({'scenario':scenario,'path':str(folder),'result':result})
        if result['status'] not in ('PASS','EXPECTED_TIMEOUT_VERIFIED'):return 1
    conf=json.loads(Path(args.config).read_bytes())
    out=ROOT/conf['run_relative']/('matrix-'+uuid.uuid4().hex+'.json')
    scope='B13_SHARED_COMPOSE_RUN' if conf.get('shared_compose') else 'MEMBER2_PERSONAL_SERVER_RUN_NOT_A13_ACCEPTANCE'
    save(out,{'status':'PASS','scope':scope,'operator':conf['operator'],'records':records,
              'C4_recovered_in_new_job':args.scenario=='all' and records[1]['result']['job_id']!=records[2]['result']['job_id']})
    print('MEMBER2_MATRIX='+str(out))
    return 0

if __name__=='__main__':raise SystemExit(main())
