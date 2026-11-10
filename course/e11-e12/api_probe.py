"""Real HTTP E12 client; archive responses and verify downloaded bytes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def safe_download_target(downloads, relative):
    """Validate an artifact's POSIX path before any local directory/file write.

    Reject Windows separators/drives even when this client runs on Linux, so
    the same server response cannot escape a Windows client's evidence root.
    """
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative or '\x00' in relative:
        raise ValueError('Unsafe artifact path')
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ('', '.', '..', '.git') for part in relative.split('/')):
        raise ValueError('Unsafe artifact path')
    downloads = Path(downloads)
    target = downloads.joinpath(*path.parts)
    current = downloads
    for part in (None, *path.parts):
        if part is not None:
            current = current / part
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError('Artifact path contains a symbolic link or junction')
    try:
        target.resolve().relative_to(downloads.resolve())
    except ValueError as error:
        raise ValueError('Artifact path escapes the download directory') from error
    return target


def read_request(path):
    # Windows editors may save UTF-8 JSON with a BOM; preserve its original
    # bytes separately for the request SHA while decoding its content here.
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',required=True)
    p.add_argument('--request',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--key',required=True)
    p.add_argument('--timeout',type=int,default=1500)
    a=p.parse_args()
    if a.out.exists():p.error('Use a new evidence directory')
    a.out.mkdir(parents=True)
    def save(name,value):
        (a.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def request(path,body=None):
        raw=None if body is None else json.dumps(body).encode()
        req=Request(a.base_url.rstrip('/')+path,data=raw,headers={'Content-Type':'application/json'})
        try:
            with urlopen(req,timeout=30) as response:return response.status,dict(response.headers),response.read()
        except HTTPError as response:return response.code,dict(response.headers),response.read()
    source=read_request(a.request)
    body={'idempotency_key':a.key,'input':source}
    save('request.json',body)
    status,_,raw=request('/health');assert status==200
    save('health.json',json.loads(raw))
    status,_,raw=request('/v1/jobs',body);assert status==202,(status,raw)
    submitted=json.loads(raw);save('submit.json',submitted)
    jid=submitted['job_id']
    status,_,raw=request('/v1/jobs',body);assert status==202
    repeated=json.loads(raw);save('duplicate.json',repeated)
    assert repeated['job_id']==jid
    conflict={'idempotency_key':a.key,'input':dict(source,expected_output='not-the-same-input')}
    status,_,raw=request('/v1/jobs',conflict)
    assert status==409 and json.loads(raw)['error']=='IDEMPOTENCY_CONFLICT'
    save('conflict.json',{'http_status':status,'response':json.loads(raw)})
    deadline=time.monotonic()+a.timeout
    with (a.out/'polls.jsonl').open('w',encoding='utf-8') as log:
        while True:
            status,_,raw=request('/v1/jobs/'+jid);assert status==200
            state=json.loads(raw);log.write(json.dumps(state)+'\n');log.flush()
            if state['status'] in ('SUCCEEDED','FAILED','TIMED_OUT'):break
            if time.monotonic()>deadline:raise TimeoutError('API task did not complete within client budget')
            time.sleep(2)
    save('state.json',state)
    status,_,raw=request('/v1/jobs/'+jid+'/artifacts');assert status==200
    result=json.loads(raw);save('result.json',result)
    assert state['status']=='SUCCEEDED',result.get('error')
    assert result['status']=='SUCCEEDED' and result['job_id']==jid and result['trace_id']==state['trace_id']
    assert [s['name'] for s in result['stages']]==['draft','full-check','incremental-check','repair','recheck']
    checks=[]
    for ref in result['artifacts']:
        prefix='artifact://'+jid+'/'
        assert ref['uri'].startswith(prefix)
        relative=ref['uri'][len(prefix):]
        target=safe_download_target(a.out/'downloads',relative)
        status,headers,content=request('/v1/jobs/'+jid+'/files/'+quote(relative,safe='/'))
        digest=hashlib.sha256(content).hexdigest()
        header={k.lower():v for k,v in headers.items()}.get('x-content-sha256')
        assert status==200 and digest==ref['sha256']==header and len(content)==ref['bytes'],relative
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        checks.append({'path':relative,'sha256':digest,'header_sha256':header,'bytes':len(content)})
    save('download-checks.json',checks)
    save('summary.json',{'passed':True,'job_id':jid,'trace_id':result['trace_id'],
         'files_verified':len(checks),'same_key_same_job':True,'conflict_status':409,
         'request_sha256':hashlib.sha256(a.request.read_bytes()).hexdigest(),
         'base_commit':result['base_commit'],'target_commit':result['target_commit'],
         'scope':'Actual HTTP API client; this run alone is not proof of an A13 client session'})
    print(json.dumps({'passed':True,'job_id':jid,'files_verified':len(checks)}))


if __name__=='__main__':main()
