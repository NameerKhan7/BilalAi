import threading,unittest
from unittest.mock import Mock,patch
import numpy as np
from runtime_paths import worker_python
from wake_service import WakeMonitor

class BackgroundStartupTests(unittest.TestCase):
    def test_pythonw_uses_console_python_for_json_workers(self):
        with patch('runtime_paths.sys.executable','C:/project/venv/Scripts/pythonw.exe'),patch('runtime_paths.Path.is_file',return_value=True):
            self.assertTrue(worker_python().endswith('python.exe'))
            self.assertNotIn('pythonw.exe',worker_python())
    def test_microphone_startup_failure_recovers(self):
        monitor=WakeMonitor.__new__(WakeMonitor)
        monitor.enabled=threading.Event();monitor.enabled.set()
        monitor.stop=threading.Event();monitor.released=threading.Event();monitor.released.set()
        monitor.verifier=Mock();monitor.rejected_candidates=0
        monitor.status='starting';events=[];monitor.callback=lambda name,data:events.append(name)
        model=Mock();model.predict.return_value={'hey_bilal':0}
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,count):
                monitor.stop.set()
                return np.zeros(count,dtype=np.int16).tobytes(),False
        with patch('wakeword.load_detector',return_value=model),patch('wakeword.load_settings',return_value={'threshold':.8}), \
             patch('sounddevice.RawInputStream',side_effect=[RuntimeError('not ready'),Stream()]) as microphone, \
             patch.object(monitor.stop,'wait',return_value=False):
            monitor.run()
        self.assertEqual(microphone.call_count,2)
        self.assertIn('wake_retry',events);self.assertIn('wake_ready',events)
        self.assertNotIn('wake_error',events)
        self.assertTrue(monitor.released.is_set())
        self.assertEqual(monitor.status,'stopped')

if __name__=='__main__':unittest.main()
