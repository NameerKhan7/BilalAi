"""Explicit window handoff: account preservation, scope, revocation and IPC."""
import os,tempfile,time,unittest,uuid,subprocess,sys
from pathlib import Path
from unittest.mock import Mock,patch
from window_grants import WindowGrants,validate_identity
from selected_browser import SelectedBrowser
from task_store import TaskStore
from task_engine import TaskEngine
from tool_policy import PolicyGate,ToolContext,LEGACY_SPECS


class FakeWindows:
    def __init__(self):
        self.info={'handle':123,'pid':10,'process_created':100.,'process':'chrome.exe','window_class':'Chrome_WidgetWin_1','title':'University Gmail'};self.tags={}
    def describe(self,handle):return dict(self.info)
    def tag(self,handle,name,value):self.tags[(handle,name)]=value
    def property(self,handle,name):return self.tags.get((handle,name))
    def untag(self,handle,name):self.tags.pop((handle,name),None)


class GrantTests(unittest.TestCase):
    def setUp(self):self.native=FakeWindows();self.now=10.;self.grants=WindowGrants(self.native,lambda:self.now)
    def test_grant_is_task_bound_and_title_can_change(self):
        token=self.grants.issue(123);identity=self.grants.bind(token,'task1');self.native.info['title']='Search results'
        validate_identity(identity,self.native)
        with self.assertRaisesRegex(ValueError,'different task'):self.grants.bind(token,'task2')
    def test_expiration(self):
        token=self.grants.issue(123,seconds=2);self.now=13
        with self.assertRaisesRegex(ValueError,'expired'):self.grants.bind(token,'one')
    def test_reused_handle_or_process_is_rejected(self):
        for field in ('pid','process_created','window_class'):
            with self.subTest(field=field):
                token=self.grants.issue(123);original=self.native.info[field];self.native.info[field]='changed'
                with self.assertRaises(ValueError):self.grants.bind(token,'one')
                self.native.info[field]=original;self.grants.revoke(token)
    def test_revocation_invalidates_worker_identity(self):
        token=self.grants.issue(123);identity=self.grants.bind(token,'one');self.grants.revoke(token)
        with self.assertRaises(ValueError):validate_identity(identity,self.native)
        self.assertEqual(self.native.tags,{})
    def test_destroyed_window_property_rejects_reuse(self):
        token=self.grants.issue(123);self.native.tags.clear()
        with self.assertRaises(ValueError):self.grants.bind(token,'one')
    def test_two_tasks_cannot_control_one_window(self):
        one=self.grants.issue(123);two=self.grants.issue(123);self.grants.bind(one,'one')
        with self.assertRaisesRegex(ValueError,'already controls'):self.grants.bind(two,'two')
        self.grants.revoke(one);self.grants.bind(two,'two')


def page(url,items=()):return {'ok':True,'verified':True,'url':url,'title':'Gmail','items':list(items)}


class SelectedMailTests(unittest.TestCase):
    def setUp(self):
        self.browser=SelectedBrowser(Mock());self.browser.navigate=Mock()
        self.sleep=patch('selected_browser.time.sleep');self.sleep.start();self.addCleanup(self.sleep.stop)
        self.before=page('https://mail.google.com/mail/u/2/#inbox')
        self.result_url='https://mail.google.com/mail/u/2/#search/loan'
        self.items=[{'type':'Edit','name':'Search mail','value':'loan'},{'type':'Text','name':'University loan application update','value':None}]
    def test_preserves_selected_account_and_observes_results(self):
        self.browser.state=Mock(side_effect=[self.before,page(self.result_url,self.items)])
        result=self.browser.search_gmail('loan');self.assertTrue(result['verified'])
        self.browser.navigate.assert_called_once_with(self.result_url)
        self.assertEqual(result['visible_matches'],['University loan application update'])
    def test_query_is_encoded_without_changing_account(self):
        self.browser.state=Mock(return_value=self.before);self.browser.search_gmail('from:university "loan & aid"')
        self.assertEqual(self.browser.navigate.call_args.args[0],'https://mail.google.com/mail/u/2/#search/from%3Auniversity%20%22loan%20%26%20aid%22')
    def test_url_change_alone_is_not_search_verification(self):
        self.browser.state=Mock(side_effect=[self.before]+[page(self.result_url)]*4)
        self.assertFalse(self.browser.search_gmail('loan')['verified'])
    def test_wrong_account_does_not_verify(self):
        self.browser.state=Mock(side_effect=[self.before]+[page(self.result_url.replace('/u/2/','/u/0/'),self.items)]*4)
        self.assertFalse(self.browser.search_gmail('loan')['verified'])
    def test_explicit_empty_result_is_verified(self):
        self.browser.state=Mock(side_effect=[self.before,page(self.result_url,[self.items[0],{'type':'Text','name':'No conversations found','value':None}])])
        result=self.browser.search_gmail('loan');self.assertTrue(result['verified']);self.assertTrue(result['no_results'])
    def test_no_current_account_requests_manual_handoff(self):
        self.browser.state=Mock(return_value=page('https://accounts.google.com/signin'))
        self.assertIn('window_request',self.browser.search_gmail('loan'));self.browser.navigate.assert_not_called()
    def test_navigation_stops_if_browser_loses_focus(self):
        window=Mock(handle=123);window.handle=123;self.browser.window=Mock(return_value=window)
        with patch('selected_browser.validate_url'),patch('win32gui.GetForegroundWindow',return_value=999):
            with self.assertRaisesRegex(ValueError,'not in focus'):SelectedBrowser.navigate(self.browser,'https://mail.google.com/')
        window.type_keys.assert_not_called()


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=TaskStore(Path(self.temp.name)/'test.db');self.policy=PolicyGate(self.store)
    def test_selected_scope_cannot_open_other_profiles_or_connectors(self):
        context=ToolContext(window_target={'handle':123})
        for tool in ('open_url','browser_open','launch_app','gmail_create_draft','notion_read'):
            with self.subTest(tool=tool):self.assertFalse(self.policy.decide(LEGACY_SPECS[tool],{},context)['ok'])
        for tool in ('selected_browser_state','selected_browser_open_gmail','selected_gmail_search'):
            self.assertIsNone(self.policy.decide(LEGACY_SPECS[tool],{'query':'loan'} if tool.endswith('search') else {},context))
    def test_untrusted_read_still_requires_approval_for_generic_input(self):
        context=ToolContext(window_target={'handle':123},untrusted_observation=True)
        self.assertTrue(self.policy.decide(LEGACY_SPECS['enter_text'],{'control_id':'x','text':'draft'},context)['policy_approval'])
    def test_default_gmail_open_requests_user_window_without_launching(self):
        from agent_tools import AgentToolExecutor
        from memory import LocalState
        browser=Mock();executor=AgentToolExecutor(browser=browser,desktop=Mock(),state=LocalState(self.store.path),policy=self.policy,context=ToolContext())
        result=executor._execute_impl('open_url',{'url':'https://mail.google.com'})
        self.assertIn('window_request',result);self.assertFalse(result['verified']);browser.open_url.assert_not_called()
    def test_window_request_blocks_task_instead_of_claiming_done(self):
        events=[];engine=TaskEngine(self.store,lambda *args:{'ok':False,'verified':False,'window_request':{'question':'Select your browser.'}},on_event=lambda name,data:events.append(name))
        try:
            task=engine.submit('Search university Gmail for loan');deadline=time.monotonic()+3
            while time.monotonic()<deadline and 'task_window' not in events:time.sleep(.01)
            self.assertEqual(self.store.task(task)['state'],'blocked');self.assertIn('task_window',events);self.assertNotIn('task_finished',events)
        finally:engine.close();engine.pool.shutdown(wait=True)
    def test_linked_handoff_finishes_and_revokes_window(self):
        self.run_handoff(True)
    def test_reading_window_alone_cannot_complete_inbox_search(self):
        self.run_handoff(False)
    def run_handoff(self,searched):
        from task_runtime import TaskRuntime
        from memory import LocalState
        grants=WindowGrants(FakeWindows());token=grants.issue(123);desktop=Mock();desktop.call.return_value={'ok':True,'verified':True}
        brain=Mock()
        def run(query,executor,**kwargs):
            executor.trace=[{'tool':'selected_gmail_search' if searched else 'selected_browser_state','arguments':{},'result':{'ok':True,'verified':True}}]
            return 'Observed results.'
        brain.run.side_effect=run
        runtime=TaskRuntime(LocalState(self.store.path),store=self.store,planner=Mock(),brain_factory=lambda:brain,grants=grants)
        source=self.store.create_task('Search university Gmail for loan emails');self.store.set_state(source,'failed')
        try:
            with patch('agent_tools.DesktopBridge',return_value=desktop):
                task=runtime.submit_handoff('Search university Gmail for loan emails',token,source);deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    if self.store.task(task)['state'] in {'done','blocked'}:break
                    time.sleep(.01)
                self.assertEqual(self.store.task(task)['parent'],source)
                self.assertEqual(self.store.task(task)['state'],'done' if searched else 'blocked')
                if searched:
                    deadline=time.monotonic()+1
                    while token in grants.entries and time.monotonic()<deadline:time.sleep(.01)
                    self.assertNotIn(token,grants.entries);desktop.close.assert_called()
                else:self.assertIn('window_request',self.store.task(task)['result'])
        finally:runtime.close();runtime.engine.pool.shutdown(wait=True)


class HandoffUItests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_local_command_only_opens_handoff_ui(self):
        from handoff_ipc import HandoffServer,request_handoff
        from PySide6.QtTest import QTest
        calls=[];name='BilalAI.test.'+uuid.uuid4().hex;server=HandoffServer(lambda:calls.append(True),server_name=name)
        try:
            script='from PySide6.QtCore import QCoreApplication; from handoff_ipc import request_handoff; app=QCoreApplication([]); raise SystemExit(0 if request_handoff('+repr(name)+') else 1)'
            client=subprocess.Popen([sys.executable,'-c',script])
            deadline=time.monotonic()+8
            while time.monotonic()<deadline and client.poll() is None:QTest.qWait(20);time.sleep(.01)
            if client.poll() is None:client.kill()
            self.assertEqual(client.wait(timeout=3),0)
            self.assertEqual(calls,[True])
        finally:server.close()
    def test_cancelled_selector_does_not_open_delayed_menu(self):
        from window_handoff import WindowSelector
        selector=WindowSelector(Mock());selector.close()
        with patch('win32gui.WindowFromPoint') as hit:
            selector.show_menu(None,(10,10));hit.assert_not_called()


if __name__=='__main__':unittest.main()
