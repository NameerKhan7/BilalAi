"""Screen privacy and DOM stale/blocked controls; no real screenshot or click."""
import os,tempfile,unittest,json
from pathlib import Path
from unittest.mock import Mock,patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from screen_awareness import PointerOverlay,guard_capture,ScreenAwareness
from task_store import TaskStore
from dom_worker import DOMSession


class ScreenDOMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=TaskStore(Path(self.temp.name)/'s.db')
    def tearDown(self):self.temp.cleanup()
    def test_SAF_sensitive_overlap_blocks_capture(self):
        window={'title':'My Bitwarden vault','process':'bitwarden.exe','rect':(0,0,600,600)}
        with patch('screen_awareness.visible_windows',return_value=[window]):
            with self.assertRaisesRegex(ValueError,'sensitive'):guard_capture((10,10,200,200),self.store)
            guard_capture((700,700,800,800),self.store)
    def test_SCR_idle_or_cancelled_session_never_captures(self):
        runtime=Mock();runtime.store=self.store;service=ScreenAwareness(runtime)
        with patch('PIL.ImageGrab.grab') as grab:
            service.capture((0,0,200,200),None,'describe',None,None);grab.assert_not_called()
            service.close();service.begin((0,0,200,200),None,'describe',None);grab.assert_not_called()
    def test_SCR_pointer_event_is_consumed_without_forwarding_to_underlying_button(self):
        button=QPushButton('Delete');clicks=[];button.clicked.connect(lambda:clicks.append(True));button.show();selected=[]
        overlay=PointerOverlay(lambda point,region:selected.append((point,region)));overlay.show()
        try:
            QTest.mouseClick(overlay,Qt.MouseButton.LeftButton,pos=QPoint(250,200))
            for _ in range(50):
                if selected:break
                QTest.qWait(20)
            self.assertEqual(clicks,[]);self.assertEqual(len(selected),1);self.assertFalse(overlay.isVisible())
        finally:overlay.close();button.close();overlay.deleteLater();button.deleteLater();self.app.processEvents()
    def test_CTL_browser_unknown_tab_does_not_click(self):
        session=DOMSession();session.context=Mock();session.check=Mock()
        with self.assertRaisesRegex(ValueError,'Unknown tab'):session.execute('browser_click',{'tab_id':'missing','element_id':'x'})
    def test_CTL_browser_reading_unstarted_tabs_does_not_launch(self):
        session=DOMSession();session.start=Mock();self.assertEqual(session.execute('browser_tabs',{})['tabs'],[]);session.start.assert_not_called()
    def test_CTL_browser_outside_allowlist_is_denied_before_launch(self):
        session=DOMSession();session.start=Mock()
        with patch('task_store.TaskStore',return_value=self.store):
            with self.assertRaisesRegex(ValueError,'Domain'):session.execute('browser_open',{'url':'https://example.com/'})
        session.start.assert_not_called()
    def test_CTL_DOM_changed_or_sensitive_element_is_never_invoked(self):
        session=DOMSession();session.context=Mock();page=Mock();page.url='https://example.com/';page.is_closed.return_value=False;session.tabs={'tab':page};session.check=Mock()
        element=Mock();element.get_attribute.side_effect=lambda key:'Send' if key=='aria-label' else '';element.inner_text.return_value='Send'
        session.elements={'e':(page,element,'','Send',page.url)}
        with self.assertRaisesRegex(ValueError,'dedicated'):session.execute('browser_click',{'tab_id':'tab','element_id':'e'})
        element.click.assert_not_called()
    def test_AGT_Claude_missing_key_never_starts_process(self):
        from delegation import HeadlessAgents
        from task_engine import TaskControl
        agents=HeadlessAgents(self.store)
        with patch.object(agents,'executable',return_value='claude.exe'),patch('provider_keys.get_key',return_value=None),patch('delegation.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'ANTHROPIC'):agents.run('claude','plan',TaskControl())
        spawn.assert_not_called()


if __name__=='__main__':unittest.main()
