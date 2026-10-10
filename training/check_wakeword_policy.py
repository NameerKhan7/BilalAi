"""Regression checks for the stricter, two-frame wake-word policy."""
from pathlib import Path
import sys,json,hashlib,time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from wakeword import load_detector,score_wav
from wakeword_gate import DetectionGate

# Exact user-reported false-trigger levels must fail the new threshold.
gate=DetectionGate(.8,2)
assert not any(gate.update(score,i*.08)[0] for i,score in enumerate([.562,.662,.711]))
# One high frame is insufficient; two sustained frames detect once, not repeatedly.
gate=DetectionGate(.8,2)
sequence=[.1,.95,.1,.85,.96,.97,.98]
hits=[gate.update(score,i*.08)[0] for i,score in enumerate(sequence)]
assert hits==[False,False,False,False,True,False,False],hits
# A low score rearms, while cooldown blocks an immediate repeat.
gate=DetectionGate(.8,2,cooldown_seconds=2)
assert not gate.update(.9,0)[0]
assert gate.update(.9,.08)[0]
assert not gate.update(.1,.16)[0]
assert not gate.update(.9,.24)[0]
assert not gate.update(.9,.32)[0]
assert gate.update(.9,2.2)[0]
print('Temporal gate regression checks passed',flush=True)

model=load_detector()
cases=[]
for path in sorted((ROOT/'cache'/'final_test').glob('1_*_pk.wav'))[:10]:
 cases.append(('existing_wake_phrase',1,path))
for path in sorted((ROOT/'cache'/'hee_haa_v3'/'test').glob('1_*.wav'))[:10]:
 cases.append(('fresh_wake_phrase',1,path))
for path in sorted((ROOT/'cache'/'hee_haa_v3'/'test').glob('0_*.wav'))[:20]:
 cases.append(('hee_haa',0,path))
for path in sorted((ROOT/'cache'/'final_test').glob('0_*.wav'))[:10]:
 cases.append(('other_similar_phrase',0,path))
rows=[]
for i,(category,label,path) in enumerate(cases):
 score=score_wav(model,path,2)
 rows.append({'category':category,'label':label,'clip':path.name,'confirmed_score':score,'detected':score>=.8})
 if (i+1)%10==0:
  print(f'Policy regression: {i+1}/{len(cases)}',flush=True)
summary={}
for category in sorted({r['category'] for r in rows}):
 subset=[r for r in rows if r['category']==category]
 summary[category]={'count':len(subset),'detections':sum(r['detected'] for r in subset)}
result={'threshold':.8,'consecutive_frames':2,
        'model_sha256':hashlib.sha256((ROOT.parent/'models'/'hey_bilal.onnx').read_bytes()).hexdigest(),
        'summary':summary,'clips':rows,'real_user_hee_haa_retest':'pending'}
(ROOT/'wakeword_policy_report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(summary,indent=2),flush=True)
