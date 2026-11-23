"""Authenticated roles and restricted DRAFT broker; protocol member2-e14-1."""
import hmac,json,os,re,shutil,subprocess,sys,traceback,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
import member2_profiles as profiles
from member2_runtime import execute,fingerprint,save

ROOT=Path(__file__).resolve().parents[2]
ROLE=os.environ.get('E14_ROLE','')
RUN_ROOT=Path(os.environ.get('E14_RUN_ROOT',str(ROOT/'work/e14-member2'))).resolve()
STATE=Path(os.environ.get('E14_BROKER_STATE','/tmp/b13-e14-broker'))
PROTOCOL='member2-e14-1'

def below(value,root):
    p=Path(value)
    if not p.is_absolute() or not p.resolve().is_relative_to(root.resolve()):raise ValueError('UNSAFE_PATH')
    cursor=p
    while cursor!=root:
        if cursor.is_symlink():raise ValueError('UNSAFE_PATH')
        if cursor.parent==cursor:raise ValueError('UNSAFE_PATH')
        cursor=cursor.parent
    return p.resolve()

def manifest(project_id):
    if project_id not in ('b13-level-v1','a13-tomlc99-release-1'):raise ValueError('UNSUPPORTED_PROJECT')
    path=ROOT/'course/e13-e14/projects'/project_id/'manifest.json'
    if not path.is_file():raise ValueError('PROJECT_NOT_REGISTERED')
    return json.loads(path.read_bytes())

def context(data):
    if not isinstance(data,dict) or data.get('protocol')!=PROTOCOL:raise ValueError('PROTOCOL_REQUIRED')
    for key,prefix in [('job_id','job-'),('trace_id','trace-')]:
        if not isinstance(data.get(key),str) or not re.fullmatch(prefix+r'[A-Za-z0-9-]{8,80}',data[key]):raise ValueError('INVALID_IDENTITY')
    m=manifest(data.get('project_id'));profile=profiles.resolve(data.get('profile'),data.get('profile_sha256'))
    if data.get('profile_sha256')!=m['profile_sha256'] or profile!=m['profile']:raise ValueError('PROFILE_HASH_MISMATCH')
    for key in ('base','target'):
        if not re.fullmatch('[0-9a-f]{40}',str(data.get(key))) or data[key]!=m[key]:raise ValueError('COMMIT_MISMATCH')
    if data.get('candidate_sha256')!=m['candidate_sha256']:raise ValueError('CANDIDATE_MISMATCH')
    job=below(str(RUN_ROOT/'jobs'/data['job_id']),ROOT/'work')
    return m,profile,job

def project(data,job,m,binding=None):
    p=below(data['project'],job)
    if p not in (job/'base',job/'target'):raise ValueError('UNSUPPORTED_PROJECT_PATH')
    side=p.name
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True,timeout=10).strip()
    if head!=m[side]:raise ValueError('SOURCE_COMMIT_MISMATCH')
    if fingerprint(p)!=(binding['files'][side] if binding else m[side+'_files']):raise ValueError('SOURCE_BINDING_MISMATCH')
    profiles.check(p,m['profile'])
    return p

def output(data,job):
    out=below(data['out'],job)
    if out==job or out in (job/'base',job/'target') or (job/'base') in out.parents or (job/'target') in out.parents:raise ValueError('UNSAFE_OUTPUT')
    if out.exists():raise ValueError('OUTPUT_EXISTS')
    return out

def load_binding(data):
    path=STATE/(data['job_id']+'.json')
    if not path.is_file():raise ValueError('DRAFT_NOT_REGISTERED')
    b=json.loads(path.read_bytes())
    for key in ('trace_id','project_id','base','target','profile_sha256','candidate_sha256','image_id'):
        if data.get(key)!=b[key]:raise ValueError('DRAFT_BINDING_MISMATCH:'+key)
    return b,path

def report_payload(data,job,m):
    path=below(data['report'],job);raw=path.read_bytes()
    if profiles.digest(raw)!=data.get('report_sha256'):raise ValueError('REPORT_HASH_MISMATCH')
    sys.path.insert(0,str(ROOT/'labs/e11e12'))
    from consume_report import verify_received_bytes
    payload=below(data['payload'],job).read_bytes()
    got=verify_received_bytes(raw,data['report_sha256'],payload,data['payload_sha256'],m['target'],data['job_id'],data['trace_id'])
    for obj in (json.loads(raw),got.payload):
        if obj.get('profile_sha256')!=m['profile_sha256']:raise ValueError('PROFILE_HASH_MISMATCH')
    if any(f['target'] not in m['profile']['repair_targets'] for f in got.payload['findings']):raise ValueError('UNSUPPORTED_TARGET')
    return got.payload

def broker(data):
    if ROLE!='draft':raise ValueError('DRAFT_ONLY')
    m,profile,job=context(data);b,state=load_binding(data)
    p=project(data,job,m,b);out=output(data,job)
    operation=data.get('operation')
    if operation not in ('full','scan','validate'):raise ValueError('UNSUPPORTED_OPERATION')
    fault=data.get('fault')
    if fault not in (None,'sleep') or (fault and os.environ.get('E14_ENABLE_FAULTS')!='1'):raise ValueError('FAULT_DISABLED')
    patchfile=None;expected=None
    if operation=='validate':
        report=report_payload(data,job,m);expected,_=profiles.patch(p,report,profile)
        patchfile=below(data['patchfile'],job)
        if profiles.digest(patchfile.read_bytes())!=data['patch_sha256']:raise ValueError('PATCH_HASH_MISMATCH')
        if patchfile.read_bytes()!=expected.encode() and not (data.get('fault_patch') and os.environ.get('E14_ENABLE_FAULTS')=='1'):raise ValueError('UNSAFE_PATCH')
    old=None
    if data.get('old_path') is not None:
        oldpath=below(data['old_path'],job)
        if profiles.digest(oldpath.read_bytes())!=data.get('old_sha256'):raise ValueError('OLD_REPORT_HASH_MISMATCH')
        old=json.loads(oldpath.read_bytes())
        if old.get('commit')!=m['base'] or old.get('profile_sha256')!=m['profile_sha256']:raise ValueError('OLD_REPORT_BINDING_MISMATCH')
    result=execute(b['image_id'],p,out,profile,operation,old=old,patchfile=patchfile,
                   timeout_seconds=data.get('timeout_seconds',120),fault=fault,
                   baked_files={n:h for n,h in m['target_files'].items() if n in m.get('image_files',[]) or
                                ('image_files' not in m and (n.endswith(('.c','.h')) or n=='Makefile'))})
    if operation=='validate' and result['status']=='SUCCEEDED' and result['payload']['accepted']:
        before=(p/'Makefile').read_bytes();accepted=(out/'output/accepted.Makefile').read_bytes()
        import difflib
        actual=''.join(difflib.unified_diff(before.decode().splitlines(True),accepted.decode().splitlines(True),fromfile='a/Makefile',tofile='b/Makefile'))
        if actual!=expected or patchfile.read_bytes()!=expected.encode():raise ValueError('EXACT_PATCH_REQUIRED')
        if fingerprint(p)!=b['files'][p.name]:raise ValueError('SOURCE_CHANGED')
        (p/'Makefile').write_bytes(accepted);b['files'][p.name]=fingerprint(p)
        temp=state.with_suffix('.new');temp.write_bytes(profiles.canonical(b));os.replace(temp,state)
    result.update(job_id=data['job_id'],trace_id=data['trace_id'],profile_sha256=m['profile_sha256'],image_id=b['image_id'])
    return result

def delegate(data,**changes):
    payload=dict(data,**changes)
    req=urllib.request.Request(os.environ.get('E14_DRAFT_URL','http://draft:8080')+'/v1/worker',
        data=profiles.canonical(payload),headers={'Content-Type':'application/json','X-E14-Token':os.environ['E14_TOKEN']})
    try:
        with urllib.request.urlopen(req,timeout=720) as response:result=json.load(response)
    except urllib.error.HTTPError as exc:raise ValueError('BROKER_REJECTED:'+exc.read().decode()) from exc
    if result.get('job_id')!=data['job_id'] or result.get('trace_id')!=data['trace_id'] or result.get('image_id')!=data['image_id']:raise ValueError('BROKER_IDENTITY_MISMATCH')
    return result

def run(data):
    m,profile,job=context(data);out=output(data,job)
    if ROLE=='draft':
        p=project(data,job,m)
        if p!=job/'target':raise ValueError('DRAFT_TARGET_REQUIRED')
        candidate=below(data['candidate'],ROOT/'data')
        if profiles.digest(candidate.read_bytes())!=m['candidate_sha256']:raise ValueError('CANDIDATE_MISMATCH')
        STATE.mkdir(parents=True,exist_ok=True);state=STATE/(data['job_id']+'.json')
        if state.exists():raise ValueError('JOB_ALREADY_REGISTERED')
        project(dict(data,project=str(job/'base')),job,m)
        sys.path.insert(0,str(ROOT/'labs/e11e12/vendor'))
        from draft.autobuild import auto_build
        budget=data.get('build_timeout',900)
        if type(budget) not in (int,float) or not 1<=budget<=900:raise ValueError('INVALID_BUILD_BUDGET')
        result=auto_build(p,candidate,out,m['expected_output'],timeout=budget)
        if result['status']!='SUCCEEDED':return {'status':result['status'],'result':result,'error':'DRAFT_FAILED'}
        image=result['attempts'][-1]['image_id']
        if not re.fullmatch('sha256:[0-9a-f]{64}',image):raise ValueError('IMMUTABLE_IMAGE_REQUIRED')
        b={k:data[k] for k in ('job_id','trace_id','project_id','base','target','profile_sha256','candidate_sha256')}
        b.update(image_id=image,files={'base':fingerprint(job/'base'),'target':fingerprint(job/'target')})
        if b['files']['base']!=m['base_files'] or b['files']['target']!=m['target_files']:raise ValueError('SOURCE_CHANGED_DURING_DRAFT')
        save(state,b);save(out/'binding.json',b)
        return {'status':'SUCCEEDED','image_id':image,'binding':b,'result':result}
    if ROLE=='buildchecker':
        result=delegate(data,out=str(out/'runtime'),operation='full')
        if result['status']=='SUCCEEDED':
            shutil.copytree(Path(result['output'])/'evidence',out,dirs_exist_ok=True);result['result']=result['payload']
        save(out/'role-result.json',result);return result
    if ROLE=='echecker':
        base=below(data['base_project'],job)
        old=delegate(data,project=str(base),out=str(out/'baseline-runtime'),operation='scan')
        if old['status']!='SUCCEEDED':return old
        save(out/'baseline-cache.json',old['payload'])
        current=delegate(data,out=str(out/'target-runtime'),operation='scan',old_path=str(out/'baseline-cache.json'),old_sha256=profiles.digest((out/'baseline-cache.json').read_bytes()))
        if current['status']!='SUCCEEDED':return current
        for field in ('baseline_graph','target_findings'):
            path=below(data[field],job)
            if profiles.digest(path.read_bytes())!=data[field+'_sha256']:raise ValueError('REFERENCE_HASH_MISMATCH')
        graph=json.loads(Path(data['baseline_graph']).read_bytes());reference=json.loads(Path(data['target_findings']).read_bytes())
        targets=profile['repair_targets'];projection={t:sorted({e['dependency'] for e in graph if e['target']==t}) for t in targets}
        norm=lambda fs:sorted((f['type'],f['target'],f['dependency']) for f in fs if f['target'] in targets)
        if projection!=old['payload']['actual'] or reference['status']!='SUCCEEDED' or norm(reference['findings'])!=norm(current['payload']['findings']):raise ValueError('FULL_INCREMENTAL_MISMATCH')
        save(out/'incremental-report.json',current['payload']);raw=(out/'incremental-report.json').read_bytes()
        env={'schema_version':'e11e12-1','kind':'incremental-check','status':'SUCCEEDED','commit':m['target'],
             'job_id':data['job_id'],'trace_id':data['trace_id'],'profile_sha256':m['profile_sha256'],
             'data':current['payload'],'image_id':data['image_id'],'execution_environment':'draft-image',
             'artifacts':[{'uri':'artifact://'+data['job_id']+'/incremental-report.json','sha256':profiles.digest(raw),'bytes':len(raw)}]}
        save(out/'incremental-check.json',env)
        return {'status':'SUCCEEDED','report':str(out/'incremental-check.json'),'report_sha256':profiles.digest((out/'incremental-check.json').read_bytes()),'payload':str(out/'incremental-report.json'),'payload_sha256':profiles.digest(raw),'job_id':data['job_id'],'trace_id':data['trace_id']}
    if ROLE=='mdfixer':
        report=report_payload(data,job,m)
        p=below(data['project'],job);diff,edits=profiles.patch(p,report,profile)
        if not diff:raise ValueError('NO_REPAIR')
        out.mkdir(parents=True,exist_ok=False);save(out/'repair-plan.json',edits)
        patchfile=out/'candidate.patch';patchfile.write_bytes(diff.encode())
        if data.get('fault_patch'):
            if os.environ.get('E14_ENABLE_FAULTS')!='1':raise ValueError('FAULT_DISABLED')
            patchfile.write_bytes(b'not a patch\n')
        result=delegate(data,out=str(out/'runtime'),operation='validate',patchfile=str(patchfile),patch_sha256=profiles.digest(patchfile.read_bytes()))
        if result['status']=='SUCCEEDED' and not result['payload']['accepted']:result['status']='REJECTED'
        save(out/'role-result.json',result);return result
    raise ValueError('UNKNOWN_ROLE')

class Handler(BaseHTTPRequestHandler):
    def reply(self,code,data):
        body=profiles.canonical(data)+b'\n';self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        self.reply(200 if self.path=='/health' else 404,{'status':'ok' if self.path=='/health' else 'NOT_FOUND','role':ROLE,'protocol':PROTOCOL})
    def do_POST(self):
        if self.path not in ('/v1/run','/v1/worker'):self.reply(404,{'error':'NOT_FOUND'});return
        expected_auth=os.environ.get('E14_TOKEN','')
        if len(expected_auth)<32 or not hmac.compare_digest(self.headers.get('X-E14-Token',''),expected_auth):
            self.reply(403,{'error':'FORBIDDEN'})
            return
        data={}
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 1<=length<=100000:raise ValueError('INVALID_SIZE')
            data=json.loads(self.rfile.read(length))
            result=broker(data) if self.path=='/v1/worker' else run(data)
            self.reply(200,result)
            print(json.dumps({'role':ROLE,'job_id':data.get('job_id'),'trace_id':data.get('trace_id'),'status':result['status']}),flush=True)
        except Exception as exc:
            traceback.print_exc();self.reply(422,{'status':'FAILED','error':str(exc),'job_id':data.get('job_id') if isinstance(data,dict) else None})
    def log_message(self,fmt,*args):print(fmt%args,flush=True)

def main():
    if ROLE not in {'draft','buildchecker','echecker','mdfixer'}:raise SystemExit('INVALID_ROLE')
    if len(os.environ.get('E14_TOKEN',''))<32:raise SystemExit('TOKEN_REQUIRED')
    HTTPServer(('0.0.0.0',8080),Handler).serve_forever()
