import io
import threading
import unittest
from unittest.mock import patch
import wave
import numpy as np
from audio_capture import CaptureConfig,CommandEndpoint,capture_command,encode_wav

class CommandCaptureTests(unittest.TestCase):
    def setUp(self):
        self.config=CaptureConfig()

    def frame(self,value):
        return np.full(self.config.block_samples,value,dtype=np.int16)

    def feed_many(self,endpoint,value,count):
        for _ in range(count):
            if endpoint.feed(self.frame(value)) is not None: break

    def test_preserves_soft_first_sound_and_stops_after_silence(self):
        endpoint=CommandEndpoint(self.config)
        self.feed_many(endpoint,0,20)
        self.feed_many(endpoint,100,4)  # A soft beginning before louder speech.
        self.feed_many(endpoint,6000,30)
        self.feed_many(endpoint,0,60)
        result=endpoint.finish()
        self.assertEqual(result.reason,'silence')
        self.assertTrue(result.speech_detected)
        self.assertEqual(np.count_nonzero(result.audio==100),4*self.config.block_samples)
        self.assertEqual(np.count_nonzero(result.audio==6000),30*self.config.block_samples)
        self.assertLess(result.duration_seconds,1.3)

    def test_keeps_a_pause_inside_a_sentence(self):
        endpoint=CommandEndpoint(self.config)
        self.feed_many(endpoint,0,15)
        self.feed_many(endpoint,5000,20)
        self.feed_many(endpoint,0,20)
        self.assertIsNone(endpoint.reason)
        self.feed_many(endpoint,7000,20)
        self.feed_many(endpoint,0,60)
        result=endpoint.finish()
        self.assertEqual(result.reason,'silence')
        self.assertEqual(np.count_nonzero(result.audio==5000),20*self.config.block_samples)
        self.assertEqual(np.count_nonzero(result.audio==7000),20*self.config.block_samples)

    def test_silence_does_not_create_a_command(self):
        endpoint=CommandEndpoint(self.config)
        self.feed_many(endpoint,0,320)
        result=endpoint.finish()
        self.assertEqual(result.reason,'no_speech')
        self.assertFalse(result.speech_detected)
        self.assertEqual(len(result.audio),0)

    def test_single_click_does_not_count_as_speech(self):
        endpoint=CommandEndpoint(self.config)
        endpoint.feed(self.frame(20000))
        self.feed_many(endpoint,0,320)
        self.assertFalse(endpoint.finish().speech_detected)

    def test_manual_stop_retains_captured_speech(self):
        endpoint=CommandEndpoint(self.config)
        self.feed_many(endpoint,6000,20)
        result=endpoint.finish('manual')
        self.assertEqual(result.reason,'manual')
        self.assertEqual(len(result.audio),20*self.config.block_samples)

    def test_long_command_has_a_duration_limit(self):
        config=CaptureConfig(initial_wait_seconds=1,max_seconds=2)
        endpoint=CommandEndpoint(config)
        self.feed_many(endpoint,6000,150)
        result=endpoint.finish()
        self.assertEqual(result.reason,'max_length')
        self.assertEqual(result.duration_seconds,2)

    def test_pcm_wave_can_be_read_without_sample_loss(self):
        samples=np.array([-32768,-1234,0,1234,32767],dtype=np.int16)
        with wave.open(io.BytesIO(encode_wav(samples)),'rb') as wav:
            self.assertEqual((wav.getnchannels(),wav.getsampwidth(),wav.getframerate()),(1,2,16000))
            self.assertEqual(wav.getnframes(),len(samples))
            decoded=np.frombuffer(wav.readframes(len(samples)),dtype='<i2')
        np.testing.assert_array_equal(decoded,samples)

    def test_microphone_path_calibrates_then_records_until_silence(self):
        frames=iter([self.frame(0)]*15+[self.frame(6000)]*30+[self.frame(0)]*60)
        class FakeStream:
            latency=.02
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return next(frames).tobytes(),False
        events=[]
        with patch('sounddevice.RawInputStream',return_value=FakeStream()):
            result=capture_command(self.config,on_event=lambda name,data:events.append(name))
        self.assertEqual(result.reason,'silence')
        self.assertIn('ready',events)
        self.assertEqual(np.count_nonzero(result.audio==6000),30*self.config.block_samples)

    def test_overflow_is_reported_instead_of_saving_a_cut_command(self):
        class BadStream:
            latency=.02
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return self_outer.frame(0).tobytes(),True
        self_outer=self
        with patch('sounddevice.RawInputStream',return_value=BadStream()):
            with self.assertRaisesRegex(RuntimeError,'overflow'):
                capture_command(self.config)

if __name__=='__main__':
    unittest.main()
