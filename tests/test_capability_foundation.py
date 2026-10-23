"""Text-injected capability checks. No microphone, accounts or desktop effects."""
import json,sqlite3,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from literal_slots import LiteralVault,redact,looks_secret
from task_store import TaskStore
from task_engine import TaskEngine,TaskControl,TaskCancelled
from tool_policy import PolicyGate,ToolSpec,ToolContext
from file_tools import FileTools
from task_runtime import TaskRuntime
from memory import LocalState


def wait_for(function,seconds=3):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if function():return
        time.sleep(.01)
    raise AssertionError('Timed out waiting for task state.')


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=TaskStore(self.root/'state.db');self.policy=PolicyGate(self.store)
    def tearDown(self):self.temp.cleanup()
    def test_QIN_exact_strings_and_unicode_roundtrip(self):
        samples=['hello','a\r\nb\n','  padded  ','I/l/1 O/0','Muhammad@example.com','https://example.com/a?q=x&b=2','a"b\'c','漢字','اردو','😀','tabs\tstay','{ "v": 1 }','a\\b','--literal','<script>x</script>','line\n\nend','a=foo+b','résumé','0.001','', '🧑🏽‍💻']
        vault=LiteralVault()
        for text in samples:
            if not text:continue
            token=vault.add(text);self.assertEqual(vault.resolve(token).encode(),text.encode());self.assertEqual(vault.mask(text),token)
        clone=vault.clone();vault.clear();self.assertEqual(clone.resolve(token),samples[-1])
    def test_QIN_secrets_never_in_descriptors_or_redacted_artifacts(self):
        secret='gsk_'+'x'*35;vault=LiteralVault();token=vault.add(secret,'API value',secret=False)
        self.assertTrue(vault.contains_secret(token));self.assertNotIn(secret,json.dumps(vault.descriptors()));self.assertNotIn(secret,vault.redact_secrets(secret))
        self.assertTrue(looks_secret('4111 1111 1111 1111'));self.assertNotIn('4111',redact('card 4111 1111 1111 1111'))
    def test_QIN_token_like_literals_are_never_recursively_rewritten(self):
        vault=LiteralVault();first=vault.add('A');second=vault.add(first+' and [[LIT_NOT_A_SLOT]]')
        self.assertEqual(vault.resolve(second),first+' and [[LIT_NOT_A_SLOT]]')
        self.assertEqual(vault.mask(first+' and [[LIT_NOT_A_SLOT]]'),second)
        self.assertEqual(vault.mask(first),first)
        self.assertEqual(vault.resolve(vault.mask('A')),'A')
    def test_SAF_policy_dry_run_has_no_approval_or_effect(self):
        context=ToolContext(dry_run=True);result=self.policy.decide(ToolSpec('write',level=2,mutates=True),{'text':'a'},context)
        self.assertTrue(result['dry_run']);self.assertEqual(self.policy.pending(),[])
    def test_SAF_approval_exact_task_args_one_use(self):
        spec=ToolSpec('write',level=2,mutates=True);context=ToolContext(task_id='one')
        result=self.policy.decide(spec,{'text':'a'},context);approval=result['approval_id'];self.policy.resolve(approval,True);context.approval_id=approval
        self.assertIsNone(self.policy.decide(spec,{'text':'a'},context))
        self.assertTrue(self.policy.decide(spec,{'text':'a'},context)['policy_approval'])
        self.assertFalse(self.policy.consume(approval,'another',{'tool':'write','args':{'text':'a'}}))
    def test_SAF_L3_requires_typed_confirmation_and_level_match(self):
        call={'tool':'power','args':{}};approval=self.policy.request('t',[call],3)
        with self.assertRaises(ValueError):self.policy.resolve(approval,True)
        self.policy.resolve(approval,True,'CONFIRM');self.assertTrue(self.policy.consume(approval,'t',call,3))
        approval=self.policy.request('t',[call],2);self.policy.resolve(approval,True);self.assertFalse(self.policy.consume(approval,'t',call,3))
    def test_SAF_untrusted_content_cannot_trigger_mutation_without_review(self):
        result=self.policy.decide(ToolSpec('launch',mutates=True),{'app':'calc'},ToolContext(untrusted_observation=True))
        self.assertTrue(result['policy_approval']);self.assertEqual(result['level'],2)
    def test_SAF_folder_allowlist_blocks_outside_and_traversal(self):
        allowed=self.root/'allowed';allowed.mkdir();self.store.set_setting('allowed_folders',[str(allowed)])
        spec=ToolSpec('file_write',path_fields=('path',));context=ToolContext()
        self.assertFalse(self.policy.decide(spec,{'path':str(allowed/'../escape')},context)['ok'])
        files=FileTools(self.store)
        for path in [allowed/'.git/config',allowed/'.env',self.root/'escape']:
            with self.assertRaises(ValueError):files.read(str(path))
    def test_SAF_audit_append_only_and_tamper_chain(self):
        self.store.audit('test',{'secret':'should not persist'});self.assertTrue(self.store.verify_audit())
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db() as db:db.execute('UPDATE audit SET event="changed"')
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db() as db:db.execute('DELETE FROM audit')
        self.assertNotIn('should not persist',json.dumps(self.store.audit_rows()))
    def test_MEM_search_and_history_survive_reopen(self):
        task=self.store.create_task('email');artifact=self.store.artifact(task,'Draft about the restaurant website','email','Restaurant draft');self.store.remember_turn('user','Draft an email')
        reopened=TaskStore(self.store.path);self.assertEqual(reopened.search('restaurant website')[0]['id'],artifact);self.assertEqual(reopened.history()[0]['text'],'Draft an email')
    def test_TSK_unverified_step_is_failed(self):
        task=self.store.create_task('write');step=self.store.step(task,'file_write',{},0)
        self.assertEqual(self.store.finish_step(step,{'ok':True,'verified':False}),'failed')
    def test_TSK_cancel_is_terminal_despite_late_completion(self):
        task=self.store.create_task('job');self.store.set_state(task,'cancelled');self.assertFalse(self.store.set_state(task,'done'));self.assertEqual(self.store.task(task)['state'],'cancelled')
    def test_CTL_file_write_exact_bytes_and_undo(self):
        self.store.set_setting('allowed_folders',[str(self.root)]);files=FileTools(self.store);path=self.root/'example.txt'
        first='  café\r\n😀\tend  ';self.assertTrue(files.write(str(path),first)['verified']);result=files.write(str(path),'changed')
        self.assertTrue(result['version_id']);self.assertTrue(files.restore(result['version_id'])['verified']);self.assertEqual(path.read_bytes(),first.encode('utf-8'))
    def test_QIN_secret_substitution_executes_only_after_review_without_database_leak(self):
        vault=LiteralVault();secret='gsk_'+'z'*35;token=vault.add(secret,'Local env value');path=self.root/'.env';self.store.set_setting('allowed_folders',[str(self.root)])
        planner=Mock();runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=planner)
        task=self.store.create_task('Write local env slot');call={'tool':'file_write','args':{'path':str(path),'content':'KEY='+token}}
        result=self.policy.decide(ToolSpec('file_write',2,mutates=True,path_fields=('path',)),call['args'],ToolContext(task_id=task,literals=vault))
        runtime.engine.contexts[task]={'literals':vault,'continuation':call};self.store.set_state(task,'waiting_approval')
        try:
            self.assertFalse(path.exists());runtime.approve(result['approval_id'],True);wait_for(lambda:self.store.task(task)['state'] in {'done','failed'})
            self.assertEqual(path.read_bytes(),('KEY='+secret).encode());self.assertNotIn(secret.encode(),self.store.path.read_bytes());self.assertNotIn(secret,json.dumps(self.store.audit_rows()))
        finally:runtime.close();runtime.engine.pool.shutdown(wait=True)
    def test_CTL_twenty_exact_literal_payloads_arrive_in_files(self):
        self.store.set_setting('allowed_folders',[str(self.root)]);files=FileTools(self.store);vault=LiteralVault()
        samples=['a+b@Example.com','https://x.test/A?b=1&c=%20','I1l O0','  left and right  ','a\r\nb\n','line\tend','漢字','café','😀','MixedCASE','{"x": "a"}','a\\b','<tag>','null','0.0001','a=b+c','x\n\n','a"b\'c','اردو','🧑🏽‍💻']
        for index,value in enumerate(samples):
            token=vault.add(value);path=self.root/f'literal-{index}.txt';self.assertTrue(files.write(str(path),vault.resolve(token))['verified']);self.assertEqual(path.read_bytes(),value.encode())
    def test_CTL_copy_never_overwrites_existing_destination(self):
        self.store.set_setting('allowed_folders',[str(self.root)]);files=FileTools(self.store);a=self.root/'a.txt';b=self.root/'b.txt';a.write_text('a');b.write_text('b')
        with self.assertRaises(ValueError):files.copy(str(a),str(b))
        self.assertEqual(b.read_text(),'b')
    def test_TSK_three_active_fourth_queued_and_cancel(self):
        started=[];release=threading.Event()
        def run(task,control,context):
            started.append(task['id'])
            while not release.wait(.01):control.checkpoint()
            return {'ok':True,'verified':True}
        engine=TaskEngine(self.store,run,concurrency=3)
        try:
            ids=[engine.submit(str(i)) for i in range(4)];wait_for(lambda:len(started)==3)
            self.assertEqual(self.store.task(ids[3])['state'],'queued');engine.cancel(ids[0]);release.set();wait_for(lambda:self.store.task(ids[3])['state']=='done')
            self.assertEqual(self.store.task(ids[0])['state'],'cancelled')
        finally:release.set();engine.close();engine.pool.shutdown(wait=True)
    def test_TSK_dependencies_and_three_intents(self):
        order=[];planner=Mock();planner.plan.return_value=[{'goal':'a','owner':'bilal','dependency':-1},{'goal':'b','owner':'bilal','dependency':0},{'goal':'c','owner':'bilal','dependency':1}]
        def run(task,control,context):order.append(task['goal']);return {'ok':True,'verified':True}
        engine=TaskEngine(self.store,run,planner=planner)
        try:
            task=engine.submit_command('a and b and c');wait_for(lambda:len(order)==3);self.assertEqual(order,['a','b','c']);self.assertEqual(len(self.store.task(task)['result']['tasks']),3)
        finally:engine.close();engine.pool.shutdown(wait=True)
    def test_TSK_crash_recovery_does_not_rerun(self):
        task=self.store.create_task('interrupted');self.store.set_state(task,'running');run=Mock();engine=TaskEngine(self.store,run)
        try:self.assertEqual(self.store.task(task)['state'],'interrupted');run.assert_not_called()
        finally:engine.close()
    def test_TSK_pause_cancel_releases_checkpoint(self):
        control=TaskControl();control.running.clear();control.stop()
        with self.assertRaises(TaskCancelled):control.checkpoint()
    def test_TSK_schedule_persisted_with_explicit_timezone(self):
        engine=TaskEngine(self.store,Mock())
        try:
            with self.assertRaises(ValueError):engine.schedule('brief me','2027-01-01T09:00:00')
            schedule=engine.schedule('brief me','2027-01-01T09:00:00+05:00',interval_seconds=86400,weekdays=True)
            with self.store.db() as db:row=db.execute('SELECT * FROM schedules WHERE id=?',(schedule,)).fetchone()
            self.assertEqual(row['goal'],'brief me');self.assertEqual(row['weekdays_only'],1)
        finally:engine.close()
    def test_TSK_runtime_answers_persist_and_status_matches_store(self):
        brain=Mock();brain.run.return_value='An answer.';planner=Mock();planner.plan.return_value=[{'goal':'question','owner':'bilal','dependency':-1}]
        runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=planner,brain_factory=lambda:brain)
        try:
            runtime.submit('question');wait_for(lambda:bool(self.store.search('answer')))
            self.assertEqual(self.store.search('answer')[0]['content'],'An answer.');self.assertIn('reply',runtime.submit('what are you doing?'))
        finally:runtime.close();runtime.engine.pool.shutdown(wait=True)
    def test_TSK_approved_step_keeps_id_and_never_replays_goal(self):
        planner=Mock();runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=planner)
        self.store.set_setting('allowed_folders',[str(self.root)]);path=self.root/'approved.txt';task=self.store.create_task('create file');call={'tool':'file_write','args':{'path':str(path),'content':'exact'}}
        approval=self.policy.request(task,[call]);self.store.set_state(task,'waiting_approval');runtime.engine.contexts[task]={'continuation':call}
        try:
            resumed=runtime.approve(approval,True);self.assertEqual(resumed,task);wait_for(lambda:self.store.task(task)['state'] in {'done','failed'})
            self.assertEqual(path.read_text(),'exact');self.assertEqual(len(self.store.steps(task)),1);planner.plan.assert_not_called()
        finally:runtime.close();runtime.engine.pool.shutdown(wait=True)
    def test_SAF_batch_plan_requires_one_review_and_executes_exact_steps(self):
        from capability_tools import CapabilityTools
        runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=Mock());self.store.set_setting('allowed_folders',[str(self.root)])
        task=self.store.create_task('two files');context=ToolContext(task_id=task);tools=CapabilityTools(self.store,runtime.engine,self.policy,context)
        plan=[{'tool':'file_write','args':{'path':str(self.root/name),'content':name}} for name in ('one.txt','two.txt')]
        result=tools.execute('propose_plan',{'plan':json.dumps(plan),'description':'Write two files'});self.assertEqual(len(self.policy.pending()),1);self.assertFalse((self.root/'one.txt').exists())
        self.store.set_state(task,'waiting_approval');runtime.engine.contexts[task]={'continuation_plan':plan}
        try:
            runtime.approve(result['approval_id'],True);wait_for(lambda:self.store.task(task)['state'] in {'done','failed'})
            self.assertEqual(self.store.task(task)['state'],'done');self.assertEqual((self.root/'one.txt').read_text(),'one.txt');self.assertEqual((self.root/'two.txt').read_text(),'two.txt');self.assertEqual(len(self.store.steps(task)),2)
        finally:runtime.close();runtime.engine.pool.shutdown(wait=True)
    def test_SAF_edited_plan_invalidates_original_review(self):
        runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=Mock());task=self.store.create_task('edit');call={'tool':'file_write','args':{'path':str(self.root/'a.txt'),'content':'a'}};approval=self.policy.request(task,[call]);self.store.set_state(task,'waiting_approval');runtime.engine.contexts[task]={'continuation':call}
        try:
            changed={'tool':'file_write','args':{'path':str(self.root/'b.txt'),'content':'b'}};replacement=runtime.replace_plan(approval,[changed]);self.assertNotEqual(approval,replacement)
            with self.assertRaises(ValueError):self.policy.resolve(approval,True)
            self.assertEqual(json.loads(self.policy.pending()[0]['plan']),[changed])
        finally:runtime.close()
    def test_TSK_pending_nonsecret_plan_survives_shutdown_without_replaying_writes(self):
        runtime=TaskRuntime(LocalState(self.root/'state.db'),store=self.store,planner=Mock());self.store.set_setting('allowed_folders',[str(self.root)]);task=self.store.create_task('restart');call={'tool':'file_write','args':{'path':str(self.root/'after-restart.txt'),'content':'reviewed'}};approval=self.policy.request(task,[call]);self.store.set_state(task,'waiting_approval');runtime.close()
        reopened=TaskRuntime(LocalState(self.root/'state.db'),store=TaskStore(self.store.path),planner=Mock())
        try:
            self.assertEqual(reopened.store.task(task)['state'],'waiting_approval');reopened.approve(approval,True);wait_for(lambda:reopened.store.task(task)['state'] in {'done','failed'});self.assertEqual((self.root/'after-restart.txt').read_text(),'reviewed')
        finally:reopened.close();reopened.engine.pool.shutdown(wait=True)
    def test_SAF_stop_all_revokes_policy_and_business_approvals(self):
        state=LocalState(self.root/'state.db');runtime=TaskRuntime(state,store=self.store,planner=Mock());task=self.store.create_task('pending');approval=self.policy.request(task,[{'tool':'file_write','args':{}}]);self.store.set_state(task,'waiting_approval');pending=state.propose('memory',{'key':'city','value':'Karachi'})
        try:
            runtime.stop_all();self.assertEqual(self.store.task(task)['state'],'cancelled');self.assertEqual(self.policy.pending(),[]);self.assertEqual(state.get(pending['id'])['status'],'cancelled')
            with self.assertRaises(ValueError):self.policy.resolve(approval,True)
        finally:runtime.close()


if __name__=='__main__':unittest.main()
