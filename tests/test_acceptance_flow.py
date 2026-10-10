"""Integrated GUI/controller checks with simulated audio, speech and account effects."""
import os,tempfile,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtCore import QObject,Signal
from PySide6.QtTextToSpeech import QTextToSpeech
from main import AssistantWindow
from ui_controller import AssistantController
from memory import LocalState
from audio_capture import CaptureResult
from business_tools import BusinessWorkflows

class SimulatedSpeech(QObject):
    stateChanged=Signal(object)
    def __init__(self):super().__init__();self.current=QTextToSpeech.State.Ready;self.spoken=[]
    def state(self):return self.current
    def say(self,text):self.spoken.append(text);self.current=QTextToSpeech.State.Speaking;self.stateChanged.emit(self.current)
    def stop(self):self.current=QTextToSpeech.State.Ready;self.stateChanged.emit(self.current)

class AcceptanceFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=LocalState(Path(self.temp.name)/'state.db')
        self.window=AssistantWindow(preview=True)
        self.controller=AssistantController(enable_wake=False,state=self.store)
        self.controller.monitor=Mock();self.controller.wake_enabled=True
        self.window.controller=self.controller;self.controller.event.connect(self.window.handle_event)
        self.speech=SimulatedSpeech();self.window.speech=self.speech;self.window.voice.setChecked(True)
        self.speech.stateChanged.connect(self.window.speech_state)
        self.events=[];self.controller.event.connect(lambda name,data:self.events.append(name))
    def pump(self,condition,timeout=3):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            self.app.processEvents()
            if condition():return
            time.sleep(.01)
        self.fail('GUI acceptance condition did not complete')
    def tearDown(self):
        self.window.shutting_down=True;self.controller.close();self.window.character.timer.stop()
        for dialog in [self.window.input_dialog,self.window.pending_dialog]:
            if dialog:dialog.close()
        self.window.hide();self.window.deleteLater();self.app.processEvents();self.temp.cleanup()
    def test_record_transcribe_reply_speech_then_hide(self):
        processor=Mock();processor.handle.return_value=Mock(reply='The result is ready.');processor.last_trace=[]
        self.controller.processor=processor
        result=CaptureResult(np.ones(16000,dtype=np.int16),16000,'silence',True,.008)
        def capture(config,**kwargs):kwargs['on_event']('ready');return result
        with patch('ui_controller.capture_command',side_effect=capture),patch('ui_controller.save_recording',return_value=Path(self.temp.name)/'command.wav'),patch('ui_controller.transcribe_recording',return_value='Explain websites.'):
            self.controller._record(False)
        self.assertIn('ready',self.events);self.assertIn('transcribing',self.events);self.assertIn('reply',self.events)
        self.assertTrue(self.window.isVisible());self.assertTrue(self.window.speech_pending)
        self.window.hide_if_idle();self.assertTrue(self.window.isVisible())
        self.assertEqual(self.speech.spoken,['The result is ready.'])
        self.speech.stop();self.pump(lambda:not self.window.isVisible())
    def test_wake_shares_audio_then_shows_companion_until_reply_finishes(self):
        processor=Mock();processor.handle.return_value=Mock(reply='Ready.');processor.last_trace=[]
        self.controller.processor=processor
        result=CaptureResult(np.ones(16000,dtype=np.int16),16000,'silence',True,.008)
        stream=Mock();prefix=np.ones(12800,dtype=np.int16)
        def capture(config,**kwargs):kwargs['on_event']('ready');return result
        with patch('ui_controller.capture_command',side_effect=capture) as captured,patch('ui_controller.save_recording',return_value=Path(self.temp.name)/'command.wav'),patch('ui_controller.transcribe_recording',return_value='Hey Bilal, explain websites.'):
            self.controller.wake_event('wake',{'stream':stream,'leading_audio':prefix,'sample_id':'fixture'})
            self.pump(lambda:'finished' in self.events and self.speech.spoken==['Ready.'])
        self.assertIs(captured.call_args.kwargs['stream'],stream)
        self.assertIs(captured.call_args.kwargs['leading_audio'],prefix)
        self.assertEqual(self.window.last_wake_sample,'fixture');self.assertTrue(self.window.isVisible())
        self.speech.stop();self.pump(lambda:not self.window.isVisible())
    def test_failure_is_spoken_and_clears_previous_success(self):
        self.window.verified=True
        self.window.handle_event('error','Could not finish; please retry.')
        self.assertFalse(self.window.verified)
        self.assertEqual(self.speech.spoken,['Could not finish; please retry.'])
        self.window.hide_if_idle();self.assertTrue(self.window.isVisible())
        self.speech.stop();self.pump(lambda:not self.window.isVisible())
    def test_missing_address_to_review_then_approved_fixture_send(self):
        question={'question':'Tell me the email address.','field':'email'}
        processor=Mock()
        def handle(query,cancel):
            if 'recipient@example.org' not in query:
                processor.last_trace=[{'result':{'ok':True,'input_request':question}}]
                return Mock(reply=question['question'])
            result=self.controller.business.draft('recipient@example.org','Meeting','Meet tomorrow at 3 PM.')
            processor.last_trace=[{'result':result}];return Mock(reply=result['reply'])
        processor.handle.side_effect=handle;self.controller.processor=processor
        message={'to':'recipient@example.org','cc':'','bcc':'','from':'sender@example.org','subject':'Meeting','body':'Meet tomorrow at 3 PM.'}
        gmail=Mock();gmail.create.return_value={'draft_id':'fixture-draft','message':message};gmail.get.return_value=message
        gmail.send.return_value={'verified':True,'reply':'Fixture sent and verified.'}
        self.controller.business=BusinessWorkflows(self.store,gmail=gmail)
        self.controller._typed('Draft an email saying meet tomorrow at 3 PM.')
        self.assertTrue(self.window.input_dialog.isVisible());gmail.create.assert_not_called()
        self.speech.stop();self.window.hide_if_idle();self.assertTrue(self.window.isVisible())
        self.window.input_dialog.entry.setText('recipient@example.org');self.window.input_dialog.send_detail()
        self.pump(lambda:self.window.pending_dialog is not None and self.controller.state=='idle')
        self.assertIsNone(self.window.input_dialog);gmail.send.assert_not_called()
        self.assertIn('Meet tomorrow at 3 PM.',self.window.pending_dialog.findChild(__import__('PySide6.QtWidgets',fromlist=['QTextBrowser']).QTextBrowser).toPlainText())
        button=next(b for b in self.window.pending_dialog.findChildren(QPushButton) if b.text()=='Approve sending')
        button.click();self.pump(lambda:gmail.send.called and self.controller.state=='idle')
        self.app.processEvents();self.assertTrue(self.window.verified)
        self.speech.stop();self.pump(lambda:not self.window.isVisible())
    def test_escape_input_cancels_without_running_another_task(self):
        processor=Mock();processor.handle.return_value=Mock(reply='Address?')
        processor.last_trace=[{'result':{'ok':True,'input_request':{'question':'Address?','field':'email'}}}]
        self.controller.processor=processor;self.controller._typed('Draft an email.')
        self.window.input_dialog.reject();self.app.processEvents()
        self.assertIsNone(self.controller.pending_input);self.assertIsNone(self.window.input_dialog)
        self.assertEqual(processor.handle.call_count,1)
    def test_transcription_failure_never_becomes_verified_success(self):
        from stt_client import TranscriptionError
        result=CaptureResult(np.ones(16000,dtype=np.int16),16000,'silence',True,.008)
        with patch('ui_controller.capture_command',return_value=result),patch('ui_controller.save_recording',return_value=Path(self.temp.name)/'command.wav'),patch('ui_controller.transcribe_recording',side_effect=TranscriptionError('Transcription failed.')):
            self.controller._record(False)
        self.assertIn('error',self.events);self.assertNotIn('reply',self.events);self.assertFalse(self.window.verified)
