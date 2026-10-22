"""Conversation sessions and hold-to-talk without live microphone/provider effects."""
import os,tempfile,threading,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,Signal
from PySide6.QtTextToSpeech import QTextToSpeech
from audio_capture import CaptureConfig,CaptureResult,CommandEndpoint
from conversation import is_conversation_end,FOLLOWUP_WAIT_SECONDS
from hold_to_talk import HoldToTalk
from main import AssistantWindow
from memory import LocalState
from ui_controller import AssistantController


class SpeechFixture(QObject):
    stateChanged=Signal(object)
    def __init__(self):super().__init__();self.current=QTextToSpeech.State.Ready
    def state(self):return self.current
    def say(self,text):self.current=QTextToSpeech.State.Speaking;self.stateChanged.emit(self.current)
    def stop(self):self.current=QTextToSpeech.State.Ready;self.stateChanged.emit(self.current)


class ConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.controller=AssistantController(enable_wake=False,state=LocalState(Path(self.temp.name)/'state.db'))
        self.controller.monitor=Mock();self.controller.wake_enabled=True
        self.window=AssistantWindow(preview=True,conversation_enabled=True);self.window.controller=self.controller
        self.controller.event.connect(self.window.handle_event)
        self.controller.record=Mock()
    def tearDown(self):
        self.window.turn_timer.stop();self.window.character.timer.stop();self.window.shutting_down=True
        self.controller.close();self.window.hide();self.window.deleteLater();self.app.processEvents();self.temp.cleanup()
    def test_global_chord_checks_only_left_keys_and_fires_on_edges(self):
        keys=set();hotkey=HoldToTalk(key_down=lambda key:key in keys);edges=[];hotkey.changed.connect(edges.append)
        for state in [{0xA3,0xA1},{0xA2},{0xA2,0xA0},{0xA2,0xA0},{0xA0},set()]:
            keys.clear();keys.update(state);hotkey.poll()
        self.assertEqual(edges,[True,False]);hotkey.stop()
    def test_hold_shows_companion_and_release_finishes_capture(self):
        self.window.hold_changed(True)
        self.assertTrue(self.window.isVisible());self.assertTrue(self.controller.hold_event.is_set())
        self.controller.record.assert_called_once_with(mode='hold')
        self.controller.state='recording';self.window.hold_changed(False)
        self.assertTrue(self.controller.stop_capture.is_set());self.assertTrue(self.window.conversation.active)
    def test_holding_never_dismisses_even_after_conversation_end(self):
        self.window.hold_changed(True);self.window.end_conversation();self.window.hide_if_idle()
        self.assertTrue(self.window.isVisible())
        self.window.hold_changed(False);self.window.hide_if_idle();self.assertFalse(self.window.isVisible())
    def test_reply_completion_continues_without_another_wake_phrase(self):
        self.window.begin_conversation();self.window.show()
        self.window.handle_event('reply',{'text':'What is the assignment about?','verified':False})
        self.window.handle_event('finished',None);self.window.turn_timer.stop();self.window.continue_conversation()
        self.controller.record.assert_called_once_with(mode='followup')
        self.assertTrue(self.window.isVisible());self.assertTrue(self.controller.conversation_active)
        self.controller.monitor.resume.assert_not_called()
    def test_followup_timeout_ends_session_and_restores_wake(self):
        self.window.begin_conversation();self.window.show()
        self.window.handle_event('conversation_timeout',None);self.window.continue_conversation()
        self.assertFalse(self.window.isVisible());self.assertFalse(self.window.conversation.active)
        self.controller.monitor.resume.assert_called_once();self.controller.record.assert_not_called()
    def test_followup_microphone_waits_for_spoken_reply_to_finish(self):
        speech=SpeechFixture();self.window.speech=speech;self.window.voice.setChecked(True)
        speech.stateChanged.connect(self.window.speech_state);self.window.begin_conversation()
        self.window.handle_event('reply',{'text':'What is the assignment about?','verified':False})
        self.window.handle_event('finished',None);self.window.continue_conversation()
        self.controller.record.assert_not_called()
        speech.stop();self.window.turn_timer.stop();self.window.continue_conversation()
        self.controller.record.assert_called_once_with(mode='followup')
    def test_pending_input_blocks_hotkey_and_followup_capture(self):
        self.controller.pending_input={'field':'email','question':'Address?'}
        self.window.hold_changed(True);self.window.continue_conversation()
        self.controller.record.assert_not_called();self.assertFalse(self.controller.hold_event.is_set())
    def test_pending_approval_cannot_be_confirmed_or_recorded_by_hotkey(self):
        self.window.pending_dialog=Mock();self.window.begin_conversation()
        self.window.hold_changed(True);self.window.continue_conversation()
        self.controller.record.assert_not_called();self.window.pending_dialog.accept.assert_not_called()
        self.window.pending_dialog=None
    def test_waiting_silence_does_not_upload_or_generate_empty_replies(self):
        result=CaptureResult(np.empty(0,dtype=np.int16),16000,'no_speech',False,.008)
        events=[];self.controller.event.connect(lambda name,data:events.append(name))
        with patch('ui_controller.capture_command',return_value=result) as capture,patch('ui_controller.transcribe_recording') as transcribe:
            self.controller._record(False,'followup')
        self.assertEqual(capture.call_args.args[0].initial_wait_seconds,FOLLOWUP_WAIT_SECONDS)
        transcribe.assert_not_called();self.assertIn('conversation_timeout',events);self.assertNotIn('empty',events)
    def test_explicit_done_is_local_and_never_dispatches_tools(self):
        self.controller.processor=Mock();self.window.begin_conversation()
        self.controller._agent("We're done.")
        self.controller.processor.handle.assert_not_called();self.assertFalse(self.window.conversation.active)
        self.assertIn("I'll be here",self.window.reply.toPlainText())
        self.assertFalse(is_conversation_end("We are done writing; now open Chrome."))
        self.assertFalse(is_conversation_end('Explain what done means.'))
        self.assertTrue(is_conversation_end("Okay, we're done."))
        self.assertTrue(is_conversation_end("I'm done."))
    def test_bare_wake_greets_instead_of_needing_a_second_wake(self):
        self.controller.processor=Mock();self.controller._agent('Hey Bilal')
        self.assertEqual(self.window.reply.toPlainText(),"I'm here. What are we working on?")
        self.controller.processor.handle.assert_not_called()
    def test_active_conversation_prevents_wake_stream_reopening(self):
        self.controller.conversation_active=True;self.controller.resume_wake();self.controller.set_wake(True)
        self.controller.monitor.resume.assert_not_called()


class HeldAudioTests(unittest.TestCase):
    def test_hold_ignores_both_initial_wait_and_thinking_pause(self):
        config=CaptureConfig(initial_wait_seconds=1,silence_seconds=.5,max_seconds=12)
        endpoint=CommandEndpoint(config);block=config.block_samples
        for value,count in [(0,100),(6000,20),(0,150),(7000,20)]:
            for _ in range(count):self.assertIsNone(endpoint.feed(np.full(block,value,dtype=np.int16),held=True))
        result=endpoint.finish('manual')
        self.assertTrue(result.speech_detected);self.assertIn(7000,result.audio)
    def test_buffer_remains_bounded_if_keys_are_stuck(self):
        config=CaptureConfig(initial_wait_seconds=1,max_seconds=2)
        endpoint=CommandEndpoint(config)
        for _ in range(100):endpoint.feed(np.zeros(config.block_samples,dtype=np.int16),held=True)
        self.assertEqual(endpoint.reason,'max_length')
