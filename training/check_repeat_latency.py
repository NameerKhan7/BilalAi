"""Replay five wake phrases to check repeat cooldown and CPU processing time."""
from pathlib import Path
import sys,time,json
import numpy as np
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from wakeword import load_detector
from wakeword_gate import DetectionGate
_,speech=wavfile.read(ROOT/'cache/final_test/1_560_pk.wav')
audio=np.concatenate([np.zeros(32000,dtype=np.int16),
 *[np.concatenate([speech,np.zeros(8000,dtype=np.int16)]) for _ in range(5)],
 np.zeros(16000,dtype=np.int16)])
model=load_detector()
gates={'previous_2_seconds':DetectionGate(.8,2,2),'current_0_6_seconds':DetectionGate(.8,2,.6)}
hits={key:[] for key in gates}
timings=[]
for offset in range(0,len(audio),1280):
 frame=audio[offset:offset+1280]
 if len(frame)<1280: frame=np.pad(frame,(0,1280-len(frame)))
 start=time.perf_counter()
 score=float(model.predict(frame)['hey_bilal'])
 timings.append((time.perf_counter()-start)*1000)
 for key,gate in gates.items():
  if gate.update(score,offset/16000)[0]: hits[key].append(round((offset+1280)/16000,3))
assert len(hits['current_0_6_seconds'])==5,hits
result={'spoken_repetitions':5,'hits':hits,'median_processing_ms':float(np.median(timings)),
        'p95_processing_ms':float(np.percentile(timings,95)),'audio_block_budget_ms':80,
        'scope':'saved synthetic phrase replay; microphone retest still required'}
(ROOT/'repeat_latency_report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
