"""Portable contract tests, not evidence of Docker or server C4/C5 execution."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'labs/e13e14'))
import member2_profiles as pp
import member2_service as service
import member2_runtime as runtime
from member2_runtime import fingerprint

class Member2Boundaries(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.run=self.root/'work/run';self.job=self.run/'jobs/job-12345678'
        self.job.mkdir(parents=True)
        self.m=service.manifest('b13-level-v1')
        self.data={'protocol':service.PROTOCOL,'job_id':'job-12345678','trace_id':'trace-12345678',
                   'project_id':'b13-level-v1','base':self.m['base'],'target':self.m['target'],
                   'profile':self.m['profile'],'profile_sha256':self.m['profile_sha256'],
                   'candidate_sha256':self.m['candidate_sha256'],'image_id':'sha256:'+'a'*64,
                   'project':str(self.job/'target'),'out':str(self.job/'result')}
        self.addCleanup(patch.stopall)
        patch.object(service,'ROOT',self.root).start();patch.object(service,'RUN_ROOT',self.run).start()
        patch.object(service,'manifest',return_value=self.m).start();patch.object(service,'STATE',self.root/'private').start()
        source=ROOT/'course/e13-e14/projects/b13-level-v1'
        for side in ['base','target']:
            clone=subprocess.run(['git','clone','-q','--no-checkout','--no-hardlinks',str(source/'project.bundle'),str(self.job/side)],capture_output=True)
            self.assertEqual(clone.returncode,0,clone.stderr.decode(errors='replace'))
            subprocess.run(['git','-C',str(self.job/side),'config','core.autocrlf','false'],check=True)
            subprocess.run(['git','-C',str(self.job/side),'checkout','-q','--detach',self.m[side]],check=True)
        self.binding={k:self.data[k] for k in ['trace_id','project_id','base','target','profile_sha256','candidate_sha256','image_id']}
        self.binding['files']={side:fingerprint(self.job/side) for side in ['base','target']}
        service.STATE.mkdir();(service.STATE/'job-12345678.json').write_text(json.dumps(self.binding))
    def test_valid_project_and_context(self):
        self.assertEqual(service.context(self.data)[2],self.job)
        self.assertEqual(service.project(self.data,self.job,self.m),self.job/'target')
    def test_unknown_profile(self):
        p=copy.deepcopy(self.m['profile']);p['repair_targets']=['other.o']
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PROFILE'):pp.resolve(p)
    def test_wrong_profile_hash(self):
        with self.assertRaisesRegex(ValueError,'PROFILE_HASH_MISMATCH'):service.context(dict(self.data,profile_sha256='0'*64))
    def test_short_commit(self):
        with self.assertRaisesRegex(ValueError,'COMMIT_MISMATCH'):service.context(dict(self.data,target=self.m['target'][:7]))
    def test_candidate_mismatch(self):
        with self.assertRaisesRegex(ValueError,'CANDIDATE_MISMATCH'):service.context(dict(self.data,candidate_sha256='0'*64))
    def test_legacy_unbound_request_rejected(self):
        d=dict(self.data);d.pop('protocol')
        with self.assertRaisesRegex(ValueError,'PROTOCOL_REQUIRED'):service.context(d)
    def test_job_traversal(self):
        with self.assertRaisesRegex(ValueError,'INVALID_IDENTITY'):service.context(dict(self.data,job_id='job-../../data'))
    def test_outside_path(self):
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):service.below(str(self.root/'other'),self.job)
    def test_output_inside_source(self):
        with self.assertRaisesRegex(ValueError,'UNSAFE_OUTPUT'):service.output(dict(self.data,out=str(self.job/'target/new')),self.job)
    def test_existing_output(self):
        (self.job/'result').mkdir()
        with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):service.output(self.data,self.job)
    def test_image_tag_or_other_job_image(self):
        with self.assertRaisesRegex(ValueError,'DRAFT_BINDING_MISMATCH'):service.load_binding(dict(self.data,image_id='image:latest'))
    def test_source_tamper_including_ignored_header(self):
        (self.job/'target/hidden.h').write_text('/* ignored or untracked is still protected */')
        with self.assertRaisesRegex(ValueError,'SOURCE_BINDING_MISMATCH'):service.project(self.data,self.job,self.m,self.binding)
    def test_source_commit_mismatch(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_COMMIT_MISMATCH'):service.project(dict(self.data,project=str(self.job/'base')),self.job,dict(self.m,base=self.m['target']))
    def test_recipe_override_refused(self):
        p=self.job/'target/Makefile';p.write_bytes(p.read_bytes().replace(b'-O0',b'-O1'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_MAKEFILE'):pp.check(self.job/'target',self.m['profile'])
    def test_extra_translation_unit_refused(self):
        (self.job/'target/new.c').write_text('int new(void){return 0;}')
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_LAYOUT'):pp.check(self.job/'target',self.m['profile'])
    def test_patch_preserves_macro_and_recipe(self):
        report={'schema_version':'e8e10-1','commit':self.m['target'],'profile_sha256':self.m['profile_sha256'],'findings':self.m['expected_missing']}
        before=(self.job/'target/Makefile').read_bytes()
        diff,edits=pp.patch(self.job/'target',report,self.m['profile'])
        self.assertEqual(len(edits),2);self.assertIn('$(HEADERS)',diff)
        self.assertNotIn('-HEADERS',diff);self.assertNotIn('-\tgcc',diff)
        self.assertEqual((self.job/'target/Makefile').read_bytes(),before)
    def test_patch_outside_target_refused(self):
        report={'commit':self.m['target'],'profile_sha256':self.m['profile_sha256'],'findings':[{'type':'MISSING','target':'app','dependency':'config.h'}]}
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_TARGET'):pp.patch(self.job/'target',report,self.m['profile'])
    def test_broker_wrong_role_no_docker(self):
        with patch.object(service,'ROLE','echecker'),patch.object(service,'execute') as execute:
            with self.assertRaisesRegex(ValueError,'DRAFT_ONLY'):service.broker(self.data)
            execute.assert_not_called()
    def test_broker_fault_disabled_no_execution(self):
        with patch.object(service,'ROLE','draft'),patch.object(service.os,'environ',dict(os.environ,E14_ENABLE_FAULTS='0')),patch.object(service,'execute') as execute:
            with self.assertRaisesRegex(ValueError,'FAULT_DISABLED'):service.broker(dict(self.data,operation='full',fault='sleep'))
            execute.assert_not_called()
    def test_arbitrary_worker_command_refused(self):
        with patch.object(service,'ROLE','draft'),patch.object(service,'execute') as execute:
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_OPERATION'):service.broker(dict(self.data,operation='shell'))
            execute.assert_not_called()
    def test_invalid_patch_rejected_with_stderr_and_all_source_unchanged(self):
        p=self.job/'target';before=fingerprint(p)
        bad=self.job/'bad.patch';bad.write_bytes(b'not a patch\n')
        result=pp.validate(p,bad,self.job/'bad-validation',self.m['profile'])
        self.assertFalse(result['accepted']);self.assertTrue(result['rollback'])
        self.assertEqual(fingerprint(p),before)
        self.assertTrue((self.job/'bad-validation/apply-check.stderr').read_bytes())
    def test_existing_tomlc99_profile_hash_preserved(self):
        self.assertEqual(pp.digest(pp.canonical(pp.resolve(pp.legacy.PROFILE))),
                         '0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1')
    def test_timeout_cleanup_queries_only_owned_label(self):
        # Simulated Docker transport tests control flow; never counts as real C4.
        import types
        calls=[];state={'removed':False,'token':None};cid='c'*64;image='sha256:'+'a'*64
        def fake(args,stdout,stderr,timeout):
            calls.append(args)
            raw=b''
            if args[1:3]==['image','inspect']:raw=json.dumps([{'Id':image}]).encode()
            elif args[1]=='create':
                state['token']=args[args.index('--label')+1].split('=',1)[1];raw=cid.encode()
            elif args[1]=='inspect':raw=json.dumps([{'Image':image,'Config':{'Labels':{'b13.e14.operation':state['token']}},'State':{'Running':False}}]).encode()
            elif args[1]=='start':raise subprocess.TimeoutExpired(args,timeout)
            elif args[1]=='ps':raw=b'' if state['removed'] else cid.encode()
            elif args[1]=='rm':self.assertEqual(args,['docker','rm','-f',cid]);state['removed']=True
            stdout.write(raw);return types.SimpleNamespace(returncode=0)
        with patch.object(runtime,'os',types.SimpleNamespace(name='posix',getuid=lambda:1001,getgid=lambda:1001)),patch.object(runtime,'fingerprint',return_value={'Makefile':'fixed'}),patch.object(runtime.subprocess,'run',side_effect=fake):
            result=runtime.execute(image,self.job/'target',self.job/'timeout-unit',self.m['profile'],'full',timeout_seconds=0.1)
        self.assertEqual(result['status'],'TIMED_OUT');self.assertTrue(result['cleanup_verified'])
        self.assertTrue(state['removed'])
        for args in calls:
            if args[1]=='ps':self.assertIn('label=b13.e14.operation='+state['token'],args)

if __name__=='__main__':unittest.main()
