import unittest
from unittest.mock import Mock,patch
import numpy as np
from ui_controller import AssistantController
from audio_capture import CaptureResult

class VoiceControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller=AssistantController(enable_wake=False)
        self.events=[]
        self.controller.event.connect(lambda name,data:self.events.append((name,data)))
    def tearDown(self): self.controller.close()
    def test_typed_request_keeps_the_agent_and_verified_result(self):
        processor=Mock();processor.handle.return_value=Mock(reply='Playing the song.')
        processor.last_trace=[{'result':{'ok':True,'verified':True}}]
        self.controller.processor=processor
        self.controller._typed('Play blind Lights by The Weeknd.')
        processor.handle.assert_called_once_with('Play blind Lights by The Weeknd.',self.controller.cancel)
        reply=next(data for name,data in self.events if name=='reply')
        self.assertTrue(reply['verified']);self.assertEqual(self.controller.state,'idle')
    def test_failed_tool_does_not_show_verified_success(self):
        processor=Mock();processor.handle.return_value=Mock(reply='Could not finish.')
        processor.last_trace=[{'result':{'ok':True,'verified':True}},{'result':{'ok':False}}]
        self.controller.processor=processor;self.controller._typed('Do a task')
        reply=next(data for name,data in self.events if name=='reply')
        self.assertFalse(reply['verified'])
    def test_wake_capture_skips_calibration_to_reduce_lost_words(self):
        empty=CaptureResult(np.empty(0,dtype=np.int16),16000,'no_speech',False,.008)
        with patch('ui_controller.capture_command',return_value=empty) as capture:
            self.controller._record(True)
        config=capture.call_args.args[0]
        self.assertEqual(config.calibration_seconds,0)
        self.assertEqual(config.silence_seconds,4)
        self.assertEqual(config.max_seconds,90)
        self.assertIn('empty',[name for name,data in self.events])
    def test_cancel_before_transcription_discards_pending_processing(self):
        empty=CaptureResult(np.empty(0,dtype=np.int16),16000,'cancelled',False,.008)
        self.controller.cancel.set()
        with patch('ui_controller.capture_command',return_value=empty),patch('ui_controller.transcribe_recording') as transcribe:
            self.controller._record(False)
        transcribe.assert_not_called()
        self.assertIn('cancelled',[name for name,data in self.events])

if __name__=='__main__':unittest.main()
