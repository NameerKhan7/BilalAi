import os,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from memory import LocalState
from business_tools import BusinessWorkflows
from power_tools import PowerActions,WindowsPower,suspend_windows
from agent_tools import AgentToolExecutor,TOOL_DECLARATIONS

class PowerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.state=LocalState(Path(self.temp.name)/'state.db')
        self.backend=Mock();self.backend.execute.return_value={'ok':True,'verified':False,'reply':'Windows accepted the request.'}
        self.power=PowerActions(self.state,self.backend);self.work=BusinessWorkflows(self.state,power=self.power)
    def tearDown(self):self.temp.cleanup()
    def test_all_actions_are_proposals_until_exact_confirmation(self):
        for action in ['sleep','shutdown','restart']:
            proposal=self.power.request(action);self.assertTrue(proposal['power_confirmation'])
            self.backend.execute.assert_not_called() if action=='sleep' else None
            row=self.state.get(proposal['approval_id']);self.assertEqual(row['payload'],{'action':action})
            with self.assertRaises(ValueError):self.work.resolve(row['id'],'wrong',True)
            self.work.resolve(row['id'],row['digest'],True)
            self.assertEqual(self.backend.execute.call_args.args,(action,))
            with self.assertRaises(ValueError):self.work.resolve(row['id'],row['digest'],True)
        self.assertEqual(self.backend.execute.call_count,3)
    def test_rejection_and_cancel_never_call_windows(self):
        for approve in [False,True]:
            row=self.state.get(self.power.request('shutdown')['approval_id']);cancel=threading.Event();cancel.set()
            self.work.resolve(row['id'],row['digest'],approve,cancel)
        self.backend.execute.assert_not_called()
    def test_expired_confirmation_cannot_power_off_later(self):
        row=self.state.get(self.power.request('restart')['approval_id'])
        with self.state.db() as db:db.execute('UPDATE pending SET created=? WHERE id=?',(time.time()-121,row['id']))
        with self.assertRaises(RuntimeError):self.work.resolve(row['id'],row['digest'],True)
        self.backend.execute.assert_not_called();self.assertEqual(self.state.get(row['id'])['status'],'failed')
    def test_tool_schema_only_proposes_whitelisted_actions(self):
        executor=AgentToolExecutor(state=self.state,business=self.work)
        for action in ['sleep','shutdown','restart']:
            result=executor.execute('request_system_power',{'action':action});self.assertTrue(result['ok'])
        for action in ['hibernate','shutdown /f','restart remote-machine']:
            self.assertFalse(executor.execute('request_system_power',{'action':action})['ok'])
        self.backend.execute.assert_not_called()
        names={t.name for t in TOOL_DECLARATIONS};self.assertNotIn('execute_power',names)
    def test_shutdown_restart_use_fixed_local_non_forcing_commands(self):
        with patch('power_tools.system_directory',return_value=Path('C:/Windows/System32')),patch('power_tools.subprocess.run',return_value=Mock(returncode=0)) as run:
            for action,flag in [('shutdown','/s'),('restart','/r')]:
                result=WindowsPower().execute(action)
                command=run.call_args.args[0]
                self.assertEqual(command[1:],[flag,'/t','0'])
                self.assertNotIn('/f',command);self.assertFalse(run.call_args.kwargs['shell'])
                self.assertFalse(result['verified'])
    def test_sleep_uses_suspend_not_hibernation_or_disabled_wake_events(self):
        library=Mock();library.SetSuspendState.return_value=1
        with patch('power_tools.ctypes.WinDLL',return_value=library),patch('power_tools.shutdown_privilege'):
            suspend_windows()
        library.SetSuspendState.assert_called_once_with(False,False,False)
    def test_windows_failure_is_not_reported_successful(self):
        with patch('power_tools.system_directory',return_value=Path('C:/Windows/System32')),patch('power_tools.subprocess.run',return_value=Mock(returncode=5)):
            with self.assertRaises(RuntimeError):WindowsPower().execute('restart')
    def test_uncertain_failure_cannot_be_replayed(self):
        row=self.state.get(self.power.request('sleep')['approval_id']);self.backend.execute.side_effect=RuntimeError('failure')
        with self.assertRaises(RuntimeError):self.work.resolve(row['id'],row['digest'],True)
        self.assertEqual(self.state.get(row['id'])['status'],'uncertain')
        with self.assertRaises(ValueError):self.work.resolve(row['id'],row['digest'],True)
        self.assertEqual(self.backend.execute.call_count,1)
