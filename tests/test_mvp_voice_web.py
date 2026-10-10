import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from voice_cancel import is_cancel_request
from wake_learning import WakeExamples
from train_reviewed_wake import prepare
from web_reader import read_webpage,validate_url
from audio_capture import CaptureConfig,capture_command
from ui_controller import AssistantController

class VoiceWebTests(unittest.TestCase):
    def test_never_mind_skips_agent_execution(self):
        controller=AssistantController(enable_wake=False)
        controller.processor=Mock()
        controller._typed('Hey Bilal, actually never mind.')
        controller.processor.handle.assert_not_called();controller.close()
    def test_cancel_words_inside_questions_are_not_control_commands(self):
        self.assertFalse(is_cancel_request('What does never mind mean?'))
        self.assertFalse(is_cancel_request('Write an email saying never mind'))
        self.assertTrue(is_cancel_request('Cancel that.'))
    def test_detections_stay_unlabelled_until_user_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            samples=WakeExamples(directory)
            sample=samples.record(np.zeros(16000,dtype=np.int16),.9)
            self.assertIsNone(samples.examples()[0]['label'])
            samples.label(sample,'negative')
            self.assertEqual(samples.examples()[0]['label_source'],'explicit_user_feedback')
            self.assertFalse(prepare(directory)['ready'])
    def test_shared_stream_retains_leading_words_without_reopening_microphone(self):
        config=CaptureConfig(calibration_seconds=0,silence_seconds=.1,max_seconds=2,initial_wait_seconds=1)
        class Stream:
            latency=.08
            def read(self,count):return np.zeros(count,dtype=np.int16).tobytes(),False
        prefix=np.full(3200,6000,dtype=np.int16)
        with patch('sounddevice.RawInputStream') as opened:
            result=capture_command(config,stream=Stream(),leading_audio=prefix)
        opened.assert_not_called()
        self.assertEqual(np.count_nonzero(result.audio==6000),3200)
    def test_public_web_reader_extracts_text_and_marks_it_untrusted(self):
        response=Mock();response.status_code=200;response.headers={'Content-Type':'text/html'}
        response.iter_content.return_value=[b'<title>Example</title><script>unsafe()</script><main>Useful facts <b>here</b>.</main>']
        session=Mock();session.get.return_value=response
        with patch('web_reader.socket.getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]):
            result=read_webpage('https://example.org',session)
        self.assertIn('Useful facts',result['text']);self.assertNotIn('unsafe()',result['text'])
        self.assertTrue(result['untrusted_content']);self.assertEqual(result['url'],'https://example.org')
    def test_local_targets_and_redirects_are_blocked(self):
        with patch('web_reader.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):validate_url('https://localhost')
        response=Mock();response.status_code=302;response.headers={'Location':'http://127.0.0.1'}
        session=Mock();session.get.return_value=response
        def lookup(host,*args,**kwargs):
            return [(2,1,6,'',('127.0.0.1' if host=='127.0.0.1' else '93.184.216.34',443))]
        with patch('web_reader.socket.getaddrinfo',side_effect=lookup):
            with self.assertRaises(ValueError):read_webpage('https://example.org',session)
    def test_missing_gmail_connection_does_not_fake_a_draft(self):
        from business_tools import GmailClient,ConnectionRequired
        with patch('business_tools.load_secret',return_value=None):
            with self.assertRaises(ConnectionRequired):GmailClient().create('test@example.org','Test','Body')
    def test_agent_cannot_activate_its_approval_window(self):
        from desktop_worker import DesktopSession
        session=DesktopSession.__new__(DesktopSession);window=Mock();window.window_text.return_value='Bilal AI Approval'
        import os
        window.process_id.return_value=os.getppid()
        session.windows={'win':window};session.controls={'button':('win',Mock())}
        with patch('desktop_worker.process_name',return_value='pythonw.exe'):
            with self.assertRaises(ValueError):session.activate_control('button')

if __name__=='__main__':unittest.main()
