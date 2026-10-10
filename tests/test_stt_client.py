import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import httpx
import numpy as np
from groq import AuthenticationError,APITimeoutError
from audio_capture import encode_wav
from stt_client import transcribe_recording,TranscriptionError,DEFAULT_MODEL
ROOT=Path(__file__).resolve().parents[1]

class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'recordings'
        folder.mkdir(exist_ok=True)
        self.path=folder/('stt_test_'+uuid.uuid4().hex+'.wav')
        if not self.path.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError('Test file escaped project folder.')
        self.path.write_bytes(encode_wav(np.ones(1600,dtype=np.int16)))

    def tearDown(self):
        if self.path.exists(): self.path.unlink()

    def test_sends_only_selected_wave_and_returns_clean_text(self):
        with patch('stt_client.Groq') as factory:
            client=factory.return_value.__enter__.return_value
            client.audio.transcriptions.create.return_value=SimpleNamespace(text='  Open YouTube.  ')
            self.assertEqual(transcribe_recording(self.path,api_key='test-key'),'Open YouTube.')
            options=client.audio.transcriptions.create.call_args.kwargs
            self.assertEqual(options['file'],(self.path.name,self.path.read_bytes()))
            self.assertEqual(options['model'],DEFAULT_MODEL)
            self.assertNotIn('language',options)
            factory.assert_called_once_with(api_key='test-key',timeout=20.0,max_retries=1)

    def test_empty_wave_is_not_uploaded(self):
        import wave
        with wave.open(str(self.path),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000)
        with patch('stt_client.Groq') as factory:
            with self.assertRaisesRegex(TranscriptionError,'empty'):
                transcribe_recording(self.path,api_key='test-key')
            factory.assert_not_called()

    def test_missing_api_key_is_not_a_network_request(self):
        with patch.dict(os.environ,{},clear=True),patch('stt_client.dotenv_values',return_value={}),patch('stt_client.Groq') as factory:
            with self.assertRaisesRegex(TranscriptionError,'GROQ_API_KEY'):
                transcribe_recording(self.path)
            factory.assert_not_called()

    def test_blank_transcript_is_not_reported_as_success(self):
        with patch('stt_client.Groq') as factory:
            factory.return_value.__enter__.return_value.audio.transcriptions.create.return_value=SimpleNamespace(text='  ')
            with self.assertRaisesRegex(TranscriptionError,'No speech'):
                transcribe_recording(self.path,api_key='test-key')

    def test_auth_failure_does_not_expose_provider_details(self):
        request=httpx.Request('POST','https://api.groq.com/openai/v1/audio/transcriptions')
        response=httpx.Response(401,request=request)
        with patch('stt_client.Groq') as factory:
            factory.return_value.__enter__.return_value.audio.transcriptions.create.side_effect=AuthenticationError('private-provider-detail',response=response,body={})
            with self.assertRaises(TranscriptionError) as error:
                transcribe_recording(self.path,api_key='test-key')
            self.assertIn('rejected',str(error.exception))
            self.assertNotIn('private-provider-detail',str(error.exception))

    def test_timeout_is_retryable_error(self):
        request=httpx.Request('POST','https://api.groq.com/openai/v1/audio/transcriptions')
        with patch('stt_client.Groq') as factory:
            factory.return_value.__enter__.return_value.audio.transcriptions.create.side_effect=APITimeoutError(request=request)
            with self.assertRaisesRegex(TranscriptionError,'timed out'):
                transcribe_recording(self.path,api_key='test-key')

if __name__=='__main__': unittest.main()
