"""Restricted E14 in-image worker. Copied by the DRAFT broker; not an HTTP service."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path

def main():
    bundle=Path('/tmp/m2-input');project=Path('/tmp/m2-project');out=Path('/tmp/m2-output')
    out.mkdir(exist_ok=False)
    request=json.loads((bundle/'request.json').read_bytes())
    response={'status':'FAILED','operation':request['operation'],'uid':os.getuid()}
    try:
        for n,h in request['code_sha256'].items():
            if hashlib.sha256((bundle/n).read_bytes()).hexdigest()!=h:raise ValueError('WORKER_HASH_MISMATCH')
        sys.path.insert(0,str(bundle))
        import member2_profiles as profiles
        profile=profiles.resolve(request['profile'],request['profile_sha256']);profiles.check(project,profile)
        for n,h in request['source_files'].items():
            if hashlib.sha256((project/n).read_bytes()).hexdigest()!=h:raise ValueError('INPUT_SOURCE_MISMATCH')
        for n,h in request['baked_files'].items():
            if hashlib.sha256((Path('/work')/n).read_bytes()).hexdigest()!=h:raise ValueError('BAKED_SOURCE_MISMATCH')
        response['input_source_sha256']=request['source_files']
        response['baked_source_sha256']=request['baked_files']
        if request.get('fault')=='sleep':time.sleep(60)
        versions={}
        for tool in ['python3','git','gcc','make','strace']:
            p=subprocess.run([tool,'--version'],capture_output=True,timeout=15,check=True)
            versions[tool]=(p.stdout+p.stderr).decode(errors='replace').splitlines()[0]
        kind=request['operation']
        if kind=='full':payload=profiles.full(project,out/'evidence',profile,request['timeout_seconds'])
        elif kind=='scan':payload=profiles.scan(project,request.get('old'),profile)
        elif kind=='validate':
            payload=profiles.validate(project,bundle/'candidate.patch',out/'evidence',profile)
            if payload['accepted']:(out/'accepted.Makefile').write_bytes((project/'Makefile').read_bytes())
        else:raise ValueError('UNSUPPORTED_OPERATION')
        response.update(status='SUCCEEDED',payload=payload,profile_sha256=request['profile_sha256'],tools=versions)
    except Exception as exc:response.update(error=str(exc),traceback=traceback.format_exc())
    (out/'response.json').write_text(json.dumps(response,indent=2)+'\n')
    print(json.dumps(response),flush=True)
    return 0 if response['status']=='SUCCEEDED' else 1

if __name__=='__main__':raise SystemExit(main())
