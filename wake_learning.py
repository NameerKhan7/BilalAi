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
        rows=[]
        for path in self.directory.glob('*.json'):
            try:row=json.loads(path.read_text(encoding='utf-8'))
            except (ValueError,OSError):continue
            if isinstance(row,dict) and row.get('id'):rows.append(row)
        return rows

    def reviewed(self):
        valid=[];invalid=[]
        for row in self.examples():
            if row.get('label_source')!='explicit_user_feedback':continue
            sample_id=row.get('id','')
            if not isinstance(sample_id,str) or len(sample_id)!=32 or any(c not in '0123456789abcdef' for c in sample_id):
                invalid.append('invalid_sample_id');continue
            wave=self.directory/(sample_id+'.wav')
            try:
                if row.get('label') not in {'positive','negative'} or not wave.is_file() or wave.stat().st_size>20_000_000:
                    raise ValueError('Invalid clip')
                if hashlib.sha256(wave.read_bytes()).hexdigest()!=row.get('sha256'):raise ValueError('Changed clip')
            except (ValueError,OSError):invalid.append(sample_id);continue
            valid.append(row)
        return valid,invalid
