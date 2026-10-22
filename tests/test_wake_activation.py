import tempfile,threading,unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from audio_capture import CaptureResult
from memory import LocalState
from ui_controller import AssistantController
from wake_verifier import OfflineWakeVerifier,command_after_wake,verification_audio
from wake_service import WakeMonitor

class WakeActivationTests(unittest.TestCase):
    def test_verifier_removes_long_silent_context_without_clipping_speech(self):
        speech=np.full(8000,4000,dtype=np.int16)
        trimmed=verification_audio(np.concatenate([np.zeros(32000,dtype=np.int16),speech,np.zeros(8000,dtype=np.int16)]))
        self.assertEqual(np.count_nonzero(trimmed==4000),8000)
        self.assertEqual(len(trimmed),8000+5120)
        self.assertEqual(len(verification_audio(np.zeros(32000,dtype=np.int16))),32000)
    def test_full_phrase_is_required_not_hey_or_video_chatter(self):
        for text in ['Uh.','hey','Bilal','Hi Bilal','Hey Bill','Welcome to this video','They said hello.','hey bilalish open Chrome']:
            self.assertIsNone(command_after_wake(text),text)
        self.assertEqual(command_after_wake('Hey, Bilal! Open Chrome.'),'Open Chrome.')
        self.assertEqual(command_after_wake('background words. Hey Bilal, open Spotify.'),'open Spotify.')
    def test_verifier_checks_audio_with_fixed_keyword_context_and_no_history(self):
        model=Mock();model.transcribe.return_value=([Mock(text='Hey Bilal.',avg_logprob=-.3,no_speech_prob=.01)],Mock())
        verifier=OfflineWakeVerifier(model)
        self.assertTrue(verifier.check(np.ones(32000,dtype=np.int16))['accepted'])
        self.assertEqual(model.transcribe.call_args.kwargs['initial_prompt'],'Hey Bilal.')
        self.assertFalse(model.transcribe.call_args.kwargs['condition_on_previous_text'])
    def test_noise_or_weak_hallucination_is_rejected(self):
        model=Mock();verifier=OfflineWakeVerifier(model)
        for text,logprob,no_speech in [('Welcome back.',-.2,.01),('Hey Bilal.',-2,.01),('Hey Bilal.',-.61,.01),('Hey Bilal.',-.2,.9)]:
            model.transcribe.return_value=([Mock(text=text,avg_logprob=logprob,no_speech_prob=no_speech)],Mock())
            self.assertFalse(verifier.check(np.ones(32000,dtype=np.int16))['accepted'])
        model.transcribe.return_value=([Mock(text='Hey Bilal.',avg_logprob=-.56,no_speech_prob=.01)],Mock())
        self.assertTrue(verifier.check(np.ones(32000,dtype=np.int16))['accepted'])
    def test_busy_verifier_does_not_queue_repeated_video_candidates(self):
        verifier=OfflineWakeVerifier(Mock());verifier.active=Future()
        self.assertFalse(verifier.begin(np.ones(32000,dtype=np.int16)).result()['accepted'])
    def test_transcribed_video_without_trigger_never_reaches_agent(self):
        with tempfile.TemporaryDirectory() as folder:
            controller=AssistantController(enable_wake=False,state=LocalState(Path(folder)/'state.db'))
            controller.processor=Mock();events=[];controller.event.connect(lambda name,data:events.append(name))
            result=CaptureResult(np.ones(16000,dtype=np.int16),16000,'silence',True,.008)
            with patch('ui_controller.save_recording',return_value=Path(folder)/'command.wav'),patch('ui_controller.transcribe_recording',return_value='Uh.'):
                controller._captured(result,require_wake=True)
            controller.processor.handle.assert_not_called();self.assertIn('wake_rejected',events)
            self.assertNotIn('reply',events);self.assertNotIn('transcript',events);controller.close()
    def test_unverified_wake_event_cannot_open_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            controller=AssistantController(enable_wake=False,state=LocalState(Path(folder)/'state.db'));controller.wake_enabled=True
            with patch('ui_controller.capture_command') as capture:
                controller.wake_event('wake',{'stream':Mock()})
            capture.assert_not_called();self.assertEqual(controller.state,'idle');controller.close()
    def monitor_case(self,accepted=True,error=False,pause_at=None,score=.999,settings=None):
        monitor=WakeMonitor.__new__(WakeMonitor)
        monitor.enabled=threading.Event();monitor.enabled.set();monitor.stop=threading.Event();monitor.released=threading.Event()
        monitor.verifier=Mock();future=Future()
        if error:future.set_exception(RuntimeError('local failed'))
        else:future.set_result({'accepted':accepted})
        monitor.verifier.begin.return_value=future;monitor.rejected_candidates=0;monitor.examples=Mock();monitor.last_sample=None
        monitor.status='starting';events=[]
        def callback(name,data):
            events.append((name,data))
            if name in {'wake','wake_error'}:monitor.stop.set()
        monitor.callback=callback
        model=Mock();model.predict.return_value={'hey_bilal':score}
        class Stream:
            def __init__(self):self.reads=0
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,count):
                self.reads+=1
                if self.reads==pause_at:monitor.enabled.clear();monitor.stop.set()
                if self.reads>12:monitor.stop.set()
                return np.full(count,self.reads,dtype=np.int16).tobytes(),False
        with patch('wakeword.load_detector',return_value=model),patch('wakeword.load_settings',return_value=settings or {'threshold':.8,'consecutive_frames':2}),patch('sounddevice.RawInputStream',return_value=Stream()):
            monitor.run()
        return monitor,events
    def test_sensitive_candidate_gate_still_requires_full_phrase_verification(self):
        settings={'threshold':.8,'candidate_threshold':.3,'consecutive_frames':2}
        _,accepted=self.monitor_case(True,score=.35,settings=settings)
        _,rejected=self.monitor_case(False,score=.35,settings=settings)
        self.assertIn('wake',[name for name,data in accepted])
        self.assertNotIn('wake',[name for name,data in rejected])
    def test_high_model_score_without_spoken_phrase_stays_hidden(self):
        monitor,events=self.monitor_case(False)
        self.assertNotIn('wake',[name for name,data in events]);self.assertGreater(monitor.rejected_candidates,0)
        monitor.examples.record.assert_not_called()
    def test_verified_phrase_preserves_audio_and_only_then_activates(self):
        monitor,events=self.monitor_case(True)
        data=next(data for name,data in events if name=='wake')
        self.assertTrue(data['phrase_verified']);self.assertGreater(len(data['leading_audio']),1280*2)
        monitor.examples.record.assert_called_once()
    def test_verifier_failure_fails_closed(self):
        monitor,events=self.monitor_case(error=True)
        self.assertNotIn('wake',[name for name,data in events]);self.assertIn('wake_error',[name for name,data in events])

    def test_pause_during_verification_cannot_activate_late(self):
        monitor,events=self.monitor_case(True,pause_at=5)
        self.assertNotIn('wake',[name for name,data in events])
    def test_disabled_wake_ignores_even_a_verified_callback(self):
        with tempfile.TemporaryDirectory() as folder:
            controller=AssistantController(enable_wake=False,state=LocalState(Path(folder)/'state.db'))
            with patch('ui_controller.capture_command') as capture:
                controller.wake_event('wake',{'phrase_verified':True,'stream':Mock()})
            capture.assert_not_called();controller.close()
    def test_verified_transcript_passes_only_the_command_to_agent(self):
        with tempfile.TemporaryDirectory() as folder:
            controller=AssistantController(enable_wake=False,state=LocalState(Path(folder)/'state.db'))
            processor=Mock();processor.handle.return_value=Mock(reply='Ready.');processor.last_trace=[]
            controller.processor=processor
            result=CaptureResult(np.ones(16000,dtype=np.int16),16000,'silence',True,.008)
            with patch('ui_controller.save_recording',return_value=Path(folder)/'command.wav'),patch('ui_controller.transcribe_recording',return_value='Hey Bilal, open Chrome.'):
                controller._captured(result,require_wake=True)
            processor.handle.assert_called_once_with('open Chrome.',controller.cancel);controller.close()
