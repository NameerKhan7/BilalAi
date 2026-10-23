"""Panel, queued notifications and activation gates without microphones or APIs."""
import json,os,tempfile,unittest,time
from pathlib import Path
from unittest.mock import Mock,patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from main import AssistantWindow
from quick_input import QuickInput
from ui_controller import AssistantController
from memory import LocalState
from task_store import TaskStore
from hold_to_talk import HoldToTalk,parse_chord
from wake_acceptance import accepted


class CapabilityUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.controller=AssistantController(enable_wake=False,state=LocalState(self.root/'s.db'));self.controller.runtime=Mock();self.controller.runtime.store=TaskStore(self.root/'s.db')
        self.window=AssistantWindow(preview=True);self.window.controller=self.controller;self.panel=None
    def tearDown(self):
        if self.panel:self.panel.close()
        self.controller.close();self.window.notice_timer.stop();self.window.turn_timer.stop();self.window.click_timer.stop();self.window.character.timer.stop();self.window.close();self.window.deleteLater();self.app.processEvents();self.temp.cleanup()
    def test_QIN_uncommitted_paste_available_to_voice_as_local_slot(self):
        self.panel=QuickInput(self.controller);exact='Some.Name+builder@example.com';self.panel.payload.setPlainText(exact)
        vault=self.controller.literal_vault;descriptors=vault.descriptors();self.assertEqual(len(descriptors),1);self.assertEqual(vault.resolve(descriptors[0]['slot']),exact);self.assertNotIn(exact,json.dumps(descriptors))
    def test_QIN_typed_secret_not_in_prompt_or_snippet_history(self):
        self.panel=QuickInput(self.controller);secret='gsk_'+'x'*30;self.panel.payload.setPlainText(secret);self.panel.add();self.panel.instruction.setPlainText('Write the pasted value to an approved env file.')
        self.controller.send=Mock();self.panel.send();query=self.controller.send.call_args.args[0]
        self.assertNotIn(secret,query);self.assertIn('LIT_',query)
        with self.controller.runtime.store.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM snippets').fetchone()[0],0)
    def test_TSK_completion_waits_until_user_releases_chord(self):
        self.window.conversation.held=True;self.window.handle_event('task_finished',{'reply':'Done.','state':'done'})
        self.window.speak_message=Mock();self.window.deliver_task_notice();self.window.speak_message.assert_not_called()
        self.window.conversation.held=False;self.window.deliver_task_notice();self.window.speak_message.assert_called_once_with('Done.')
    def test_HOT_toggle_and_hold_edges(self):
        keys=set();hotkey=HoldToTalk(key_down=lambda k:k in keys,keys=parse_chord('Ctrl+Shift+Space'),toggle=True);edges=[];hotkey.changed.connect(edges.append)
        for value in [{162,160,32},{162,160,32},set(),{162,160,32},set()]:keys.clear();keys.update(value);hotkey.poll()
        self.assertEqual(edges,[True,False]);hotkey.stop()
        self.assertEqual(parse_chord('Ctrl+Shift'),[162,160])
        with self.assertRaises(ValueError):parse_chord('Ctrl+Ctrl')
    def test_VOI_wake_requires_fresh_independent_measured_evidence(self):
        path=self.root/'wake.json';self.assertFalse(accepted(path));report={'independent':True,'tested_at':time.time(),'positive_trials':50,'true_activations':45,'negative_seconds':3600,'false_activations':0};path.write_text(json.dumps(report));self.assertTrue(accepted(path))
        report['false_activations']=1;path.write_text(json.dumps(report));self.assertFalse(accepted(path))
        report['false_activations']=0;report['tested_at']-=31*86400;path.write_text(json.dumps(report));self.assertFalse(accepted(path))
    def test_VOI_background_queue_does_not_make_controller_busy(self):
        self.controller.runtime.submit.return_value={'reply':'Queued.','task_id':'abc'}
        self.controller._typed('Analyze this project');self.assertEqual(self.controller.state,'idle');self.controller.runtime.submit.assert_called_once()


if __name__=='__main__':unittest.main()
