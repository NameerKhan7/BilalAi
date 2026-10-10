import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from wake_learning import WakeExamples
from train_reviewed_wake import prepare
from evaluate_wake_learning import evaluate

class WakeAcceptanceTests(unittest.TestCase):
    def test_changed_or_missing_reviewed_audio_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            store=WakeExamples(directory);store.session='session-one'
            sample=store.record(np.ones(16000,dtype=np.int16),None);store.label(sample,'positive')
            wave=Path(directory)/(sample+'.wav');wave.write_bytes(b'changed')
            valid,invalid=store.reviewed();self.assertEqual(valid,[]);self.assertEqual(invalid,[sample])
            self.assertFalse(prepare(directory)['ready'])
            self.assertEqual(evaluate(directory)['invalid_reviewed_count'],1)
    def test_evaluation_does_not_accept_separate_single_class_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            store=WakeExamples(directory)
            for label in ['positive','negative']:
                store.session=label
                for _ in range(10):store.label(store.record(np.ones(320,dtype=np.int16),None),label)
            with patch('wakeword.load_detector'),patch('wakeword.score_wav',return_value=.7),patch('wakeword.load_settings',return_value={'threshold':.65,'consecutive_frames':3}):
                result=evaluate(directory)
            self.assertEqual(result['status'],'needs_more_independent_examples')
            self.assertEqual(result['balanced_sessions'],0);self.assertEqual(result['positive_hits'],10)
            self.assertEqual(result['negative_hits'],10);self.assertFalse(result['settings_changed'])
            self.assertFalse(prepare(directory)['ready'])
    def test_balanced_preparation_keeps_session_groups_and_candidate_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=WakeExamples(root/'samples')
            for session in ['first','second']:
                store.session=session
                for label in ['positive','negative']:
                    for _ in range(5):store.label(store.record(np.ones(320,dtype=np.int16),None),label)
            with patch('train_reviewed_wake.ROOT',root):result=prepare(store.directory)
            self.assertTrue(result['ready']);self.assertIn('candidates',result['output'])
            items=json.loads((Path(result['session'])/'samples.json').read_text())['samples']
            self.assertEqual({r['session'] for r in items},{'first','second'})
            self.assertFalse((root/'models/hey_bilal.onnx').exists())
    def test_malformed_sidecar_does_not_break_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'broken.json').write_text('{')
            self.assertEqual(WakeExamples(directory).examples(),[])
