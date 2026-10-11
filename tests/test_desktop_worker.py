import unittest
from unittest.mock import Mock,patch
from desktop_worker import DesktopSession

class DesktopWorkerTests(unittest.TestCase):
    def setUp(self):
        self.session=DesktopSession.__new__(DesktopSession)
        self.window=Mock();self.window.process_id.return_value=123;self.window.window_text.return_value='Spotify Free'
        self.control=Mock();self.control.window_text.return_value='Play'
        self.control.element_info.control_type='Button'
        self.control.element_info.element.CurrentIsPassword=False
        parent=Mock();parent.window_text.return_value='Search results'
        parent.parent.return_value=parent;self.control.parent.return_value=parent
        self.session.windows={'window':self.window}
        self.session.controls={'observed':('window',self.control)}
        self.session.apps={}
        self.process=patch('desktop_worker.process_name',return_value='spotify.exe')
        self.process.start()
    def tearDown(self): self.process.stop()

    def test_observed_action_invalidates_all_control_ids(self):
        result=self.session.activate_control('observed')
        self.assertTrue(result['ok']);self.assertFalse(result['verified'])
        self.control.invoke.assert_called_once()
        with self.assertRaisesRegex(ValueError,'Stale'): self.session.activate_control('observed')

    def test_failed_action_also_invalidates_ids(self):
        self.control.invoke.side_effect=RuntimeError('failed')
        with self.assertRaises(RuntimeError): self.session.activate_control('observed')
        self.assertEqual(self.session.controls,{})

    def test_publish_controls_cannot_be_invoked(self):
        self.control.window_text.return_value='Send'
        with self.assertRaisesRegex(ValueError,'dedicated confirmed tool'):
            self.session.activate_control('observed')
        self.control.invoke.assert_not_called()

    def test_power_controls_cannot_bypass_confirmation(self):
        for label in ['Sleep','Shut down','Restart','Hibernate']:
            self.control.window_text.return_value=label
            with self.assertRaisesRegex(ValueError,'dedicated confirmed tool'):
                self.session.activate_control('observed')
        self.control.invoke.assert_not_called()
    def test_power_shortcut_cannot_bypass_confirmation(self):
        self.session.apps={'power-id':'Restart laptop'}
        with patch('desktop_worker.subprocess.Popen') as launch:
            result=self.session.launch_app('power-id')
        self.assertFalse(result['ok']);launch.assert_not_called()

    def test_terminal_and_password_fields_are_blocked(self):
        with patch('desktop_worker.process_name',return_value='powershell.exe'):
            with self.assertRaisesRegex(ValueError,'cannot be automated'):
                self.session.enter_text('observed','anything')
        self.control.element_info.element.CurrentIsPassword=True
        with self.assertRaises(ValueError): self.session.enter_text('observed','anything')
        self.control.iface_value.SetValue.assert_not_called()

    def test_only_discovered_app_ids_can_launch(self):
        with patch('desktop_worker.subprocess.Popen') as launch:
            result=self.session.launch_app('invented-id')
        self.assertFalse(result['ok']);launch.assert_not_called()

if __name__=='__main__': unittest.main()
