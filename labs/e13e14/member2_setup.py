"""Generate private personal Compose/config; never starts Docker or uses GitHub."""
import argparse,json,os,secrets,shlex,shutil,socket,subprocess,uuid
from pathlib import Path
from member2_faults import SCENARIOS, fault_environment
from member2_profiles import canonical
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--image',required=True)
    ap.add_argument('--project', choices=('b13-level-v1', 'b13-tomlc99-full-preview-v1'), default='b13-level-v1')
    ap.add_argument('--port-start',type=int,default=28081)
    ap.add_argument('--shared',action='store_true',help='use the shared four-role Compose file plus a protocol override')
    ap.add_argument('--scenario',choices=SCENARIOS,default='normal')
    a=ap.parse_args()
    if os.name!='posix' or os.getuid()==0 or os.getuid()!=os.geteuid():raise SystemExit('NONROOT_LINUX_REQUIRED')
    import pwd
    owner=pwd.getpwuid(os.getuid())
    if Path.home()!=Path(owner.pw_dir) or ROOT.stat().st_uid!=os.getuid() or Path.home().stat().st_uid!=os.getuid():
        raise SystemExit('OWNED_HOME_AND_REPO_REQUIRED')
    if not a.shared and (owner.pw_name!='m2_241880091' or Path.home()!=Path('/home/m2_241880091')):
        raise SystemExit('MEMBER2_IDENTITY_REQUIRED')
    os.umask(0o077)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise SystemExit('CLEAN_SOURCE_REQUIRED')
    image=json.loads(subprocess.check_output(['docker','image','inspect',a.image]))[0]['Id']
    ports={role:a.port_start+i for i,role in enumerate(['buildchecker','echecker','draft','mdfixer'])}
    for port in ports.values():
        if port in (8081,8082) or not 1024<=port<=65535:raise SystemExit('INVALID_PERSONAL_PORT')
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    name='m2-e14-'+uuid.uuid4().hex[:12];run=ROOT/'work'/name;run.mkdir(parents=True)
    data=ROOT/'data'/name;data.mkdir(parents=True)
    shutil.copyfile(ROOT/'course/e13-e14/projects'/a.project/'candidate.Dockerfile',data/'candidate.Dockerfile')
    auth_file=run/'token.secret'
    auth_file.write_text(secrets.token_hex(32))
    auth_file.chmod(0o600)
    # Token is kept in a private env file and is excluded from evidence exports.
    envfile=run/'roles.secret.env'
    env_entry='{}={}\n'.format('E14_TOKEN',auth_file.read_text())
    envfile.write_text(env_entry)
    envfile.chmod(0o600)
    services={}
    docker_gid=str(os.stat('/var/run/docker.sock').st_gid)
    for role in ports:
        protocol_env={'E14_PROTOCOL':'member2-e14-1','E14_RUN_ROOT':'/course/work/'+name,
                      'E14_DRAFT_URL':'http://draft:8080',**fault_environment(role,a.scenario)}
        if a.project == 'b13-tomlc99-full-preview-v1':
            protocol_env['E14_TOMLC99_FULL_PREVIEW'] = '1'
        if a.shared:
            services[role]={'env_file':[str(envfile)],'environment':protocol_env,'restart':'no'}
            continue
        value={'image':image,'pull_policy':'never','user':f'{os.getuid()}:{os.getgid()}',
               'working_dir':'/course','command':['python3','labs/e13e14/service.py'],
               'env_file':[str(envfile)],'environment':{'E14_ROLE':role,**protocol_env,'HOME':'/tmp','PYTHONDONTWRITEBYTECODE':'1'},
               'volumes':[str(ROOT)+':/course:ro',str(ROOT/'work')+':/course/work',str(ROOT/'data')+':/course/data:ro'],
               'ports':[f'127.0.0.1:{ports[role]}:8080'],'cpus':1.0,'mem_limit':'768m','pids_limit':256,
               'security_opt':['no-new-privileges:true'],'restart':'no',
               'healthcheck':{'test':['CMD','python3','-c',"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)"],'interval':'5s','timeout':'3s','retries':12}}
        if role=='draft':value['volumes'].append('/var/run/docker.sock:/var/run/docker.sock');value['group_add']=[docker_gid]
        services[role]=value
    compose=run/'compose.json';compose.write_bytes(canonical({'services':services}))
    config={'run_name':name,'run_relative':'work/'+name,'compose':str(compose),'ports':ports,'token_file':str(auth_file),
            'image_id':image,'project_id':a.project,'scenario':a.scenario,'shared_compose':a.shared,'operator':owner.pw_name,'uid':os.getuid()}
    (run/'config.json').write_bytes(canonical(config))
    (run/'source-commit.txt').write_bytes(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT))
    variables={'M2_E14_REPO':ROOT,'M2_E14_CONFIG':run/'config.json','M2_E14_RUN':run,
               'M2_E14_COMPOSE':compose,'M2_E14_PROJECT':name}
    if a.shared:
        variables.update(E14_ROOT=ROOT,E14_IMAGE=image,E14_UID=os.getuid(),E14_GID=os.getgid(),
                         E14_DOCKER_GID=docker_gid,M2_E14_BASE_COMPOSE=ROOT/'labs/e13e14/compose.yaml')
        variables.update({'E14_PORT_'+role.upper():port for role,port in ports.items()})
    session=''.join(f'export {key}={shlex.quote(str(value))}\n' for key,value in variables.items())+'cd "$M2_E14_REPO"\n'
    (run/'session.sh').write_text(session);(run/'session.sh').chmod(0o600)
    print('M2_E14_SESSION='+str(run/'session.sh'))
    print('M2_E14_SETUP=PASS')

if __name__=='__main__':main()
