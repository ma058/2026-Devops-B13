"""DRAFT-only Docker execution. Other roles use the authenticated delegation API.

Derived from E11/E12 ImageRuntime's copy/inspect/writeback design. This variant
adds per-operation budgets and confirms daemon-side cleanup even after timeout.
"""
import difflib,json,os,re,shutil,subprocess,uuid
from datetime import datetime,timezone
from pathlib import Path
import member2_profiles as profiles

ROOT=Path(__file__).resolve().parents[2]

def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(obj,stream,ensure_ascii=False,indent=2)

def fingerprint(project):
    project=Path(project)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=project).split(b'\0')
    names={n.decode('utf-8') for n in tracked if n}
    names.update(p.relative_to(project).as_posix() for p in project.rglob('*') if p.suffix in ('.c','.h') and '.git' not in p.parts)
    result={}
    for n in sorted(names):
        path=project/n
        if path.is_symlink() or not path.is_file():raise ValueError('SOURCE_MISSING_OR_SYMLINK')
        result[n]=profiles.digest(path.read_bytes())
    return result

def execute(image,project,out,profile,operation,*,old=None,patchfile=None,timeout_seconds=120,fault=None,baked_files=None):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise ValueError('IMMUTABLE_IMAGE_REQUIRED')
    if operation not in ('full','scan','validate'):raise ValueError('UNSUPPORTED_OPERATION')
    if type(timeout_seconds) not in (int,float) or not 0.01<=timeout_seconds<=600:raise ValueError('INVALID_TIMEOUT')
    if os.name!='posix' or os.getuid()==0:raise ValueError('NONROOT_LINUX_REQUIRED')
    profile=profiles.resolve(profile);profiles.check(project,profile)
    project=Path(project);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    before=fingerprint(project);save(out/'source-before.json',before)
    nonce=uuid.uuid4().hex
    number=0
    cid=None
    primary=None
    response=None
    witness=None
    def command(args,timeout=30,checked=True):
        nonlocal number
        number+=1;prefix=out/f'{number:02d}-{args[1]}'
        save(prefix.with_suffix('.command.json'),{'argv':args})
        with prefix.with_suffix('.stdout.log').open('wb') as stdout,prefix.with_suffix('.stderr.log').open('wb') as stderr:
            try:p=subprocess.run(args,stdout=stdout,stderr=stderr,timeout=timeout)
            except subprocess.TimeoutExpired:
                save(prefix.with_suffix('.exit.json'),{'timed_out':True,'timeout_seconds':timeout})
                raise TimeoutError('WORKER_TIMED_OUT')
        save(prefix.with_suffix('.exit.json'),{'exit_code':p.returncode})
        if checked and p.returncode:raise ValueError('DOCKER_COMMAND_FAILED:'+str(prefix))
        return p.returncode,prefix.with_suffix('.stdout.log').read_bytes()
    bundle=out/'input';bundle.mkdir()
    sources={'member2_worker.py':Path(__file__).with_name('member2_worker.py'),
             'member2_profiles.py':Path(__file__).with_name('member2_profiles.py'),
             'b13-profile.json':ROOT/'course/e13-e14/projects/b13-level-v1/profile.json',
             'project_profile.py':ROOT/'labs/e11e12/project_profile.py',
             'lab.py':ROOT/'labs/e8e10/lab.py',
             'fullcheck.py':ROOT/'labs/e11e12/environment/services/buildchecker/buildchecker/fullcheck.py'}
    hashes={}
    for n,p in sources.items():shutil.copyfile(p,bundle/n);hashes[n]=profiles.digest(p.read_bytes())
    if patchfile:shutil.copyfile(patchfile,bundle/'candidate.patch')
    save(bundle/'request.json',{'operation':operation,'old':old,'fault':fault,'profile':profile,
         'profile_sha256':profiles.digest(profiles.canonical(profile)),'code_sha256':hashes,'timeout_seconds':timeout_seconds,
         'source_files':before,'baked_files':baked_files or {}})
    try:
        _,raw=command(['docker','image','inspect',image]);assert json.loads(raw)[0]['Id']==image
        _,raw=command(['docker','create','--network','none','--cpus','1','--memory','512m','--pids-limit','256',
                      '--cap-drop','ALL','--cap-add','SYS_PTRACE','--security-opt','no-new-privileges',
                      '--user',f'{os.getuid()}:{os.getgid()}','--label','b13.e14.operation='+nonce,
                      '--entrypoint','python3',image,'/tmp/m2-input/member2_worker.py'])
        cid=raw.decode().strip()
        if not re.fullmatch('[0-9a-f]{64}',cid):raise ValueError('INVALID_CONTAINER_ID')
        save(out/'container-id.json',{'container_id':cid,'ownership_label':nonce})
        command(['docker','cp','-a',str(bundle),cid+':/tmp/m2-input'])
        command(['docker','cp','-a',str(project),cid+':/tmp/m2-project'])
        _,raw=command(['docker','inspect',cid]);info=json.loads(raw)[0]
        if info['Image']!=image or info['Config']['Labels'].get('b13.e14.operation')!=nonce:raise ValueError('IMAGE_BINDING_MISMATCH')
        code,_=command(['docker','start','--attach',cid],timeout_seconds,False)
        _,raw=command(['docker','inspect',cid]);info=json.loads(raw)[0]
        command(['docker','cp','-a',cid+':/tmp/m2-output',str(out/'output')],checked=False)
        if code or info['State']['Running'] or info['State']['ExitCode']:raise ValueError('WORKER_FAILED')
        response=json.loads((out/'output/response.json').read_bytes())
        if (response['status']!='SUCCEEDED' or response['operation']!=operation or response['uid']!=os.getuid()
            or response['profile_sha256']!=profiles.digest(profiles.canonical(profile))
            or response['input_source_sha256']!=before
            or response['baked_source_sha256']!=(baked_files or {})):raise ValueError('WORKER_RESPONSE_MISMATCH')
        if operation=='full' and response['payload']['status']!='SUCCEEDED':raise ValueError('FULL_CHECK_FAILED')
        witness={'operation':operation,'image_id':image,'actual_container_image':info['Image'],'container_id':cid,
                 'container_exit_code':info['State']['ExitCode'],'code_sha256':hashes,'ownership_label':nonce,
                 'profile_sha256':response['profile_sha256'],'input_source_sha256':response['input_source_sha256'],
                 'baked_source_sha256':response['baked_source_sha256'],'transport':'docker cp; no host bind mount'}
        save(out/'execution.json',witness)
    except Exception as exc:primary=exc
    finally:
        cleanup={'ownership_label':nonce,'removed':[],'verified_no_owned_containers':False}
        try:
            _,raw=command(['docker','ps','-aq','--no-trunc','--filter','label=b13.e14.operation='+nonce])
            ids=raw.decode().split()
            for owned in ids:
                if not re.fullmatch('[0-9a-f]{64}',owned):raise ValueError('INVALID_CLEANUP_ID')
                _,raw=command(['docker','inspect',owned]);info=json.loads(raw)[0]
                if info['Config']['Labels'].get('b13.e14.operation')!=nonce:raise ValueError('CLEANUP_OWNER_MISMATCH')
                if info['State']['Running']:
                    command(['docker','kill',owned])
                    _,raw=command(['docker','inspect',owned]);assert not json.loads(raw)[0]['State']['Running']
                if not (out/'output').exists():command(['docker','cp','-a',owned+':/tmp/m2-output',str(out/'output')],checked=False)
                command(['docker','rm','-f',owned]);cleanup['removed'].append(owned)
            _,raw=command(['docker','ps','-aq','--filter','label=b13.e14.operation='+nonce])
            cleanup['verified_no_owned_containers']=not raw.strip()
            if not cleanup['verified_no_owned_containers']:raise ValueError('OWNED_CONTAINER_REMAINS')
        except Exception as exc:
            cleanup['error']=str(exc);primary=ValueError('CLEANUP_UNVERIFIED:'+str(exc))
        cleanup['observed_at_utc']=datetime.now(timezone.utc).isoformat()
        save(out/'cleanup.json',cleanup)
    after=fingerprint(project);save(out/'source-after.json',after)
    if before!=after:primary=ValueError('SOURCE_CHANGED_DURING_WORKER')
    if primary:
        result={'status':'TIMED_OUT' if isinstance(primary,TimeoutError) else 'FAILED','error':str(primary),'operation':operation,
                'container_id':cid,'cleanup_verified':cleanup['verified_no_owned_containers'],'source_unchanged':before==after}
        save(out/'result.json',result);return result
    # Caller performs exact-patch writeback only after all validation and cleanup.
    result={'status':'SUCCEEDED','payload':response['payload'],'execution':witness,
            'cleanup_verified':True,'source_unchanged':True,'output':str(out/'output')}
    save(out/'result.json',result);return result
