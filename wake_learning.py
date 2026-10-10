"""Local wake examples. Detections are unlabelled until explicit user feedback."""
from collections import deque
from pathlib import Path
import hashlib,json,time,uuid,threading
from audio_capture import encode_wav
ROOT=Path(__file__).resolve().parent
class WakeExamples:
    def __init__(self,directory=None):
        self.directory=Path(directory or ROOT/'data/wake_examples');self.lock=threading.Lock()
    def record(self,audio,score,source='detected'):
        self.directory.mkdir(parents=True,exist_ok=True)
        sample_id=uuid.uuid4().hex;wave=self.directory/(sample_id+'.wav')
        raw=encode_wav(audio);wave.write_bytes(raw)
        metadata={'id':sample_id,'created':time.time(),'score':score,'source':source,'label':None,
                  'sha256':hashlib.sha256(raw).hexdigest(),'session':getattr(self,'session',None)}
        (self.directory/(sample_id+'.json')).write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        return sample_id
    def label(self,sample_id,label):
        if label not in {'positive','negative'}:raise ValueError('Use positive or negative.')
        if not sample_id or any(c not in '0123456789abcdef' for c in sample_id):raise ValueError('Unknown wake sample.')
        path=self.directory/(sample_id+'.json')
        with self.lock:
            row=json.loads(path.read_text(encoding='utf-8'))
            row['label']=label;row['label_source']='explicit_user_feedback'
            path.write_text(json.dumps(row,indent=2),encoding='utf-8')
        return row
    def examples(self):
        rows=[json.loads(p.read_text(encoding='utf-8')) for p in self.directory.glob('*.json')]
        return [row for row in rows if row.get('id')]
