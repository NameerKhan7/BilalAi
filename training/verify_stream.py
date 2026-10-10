"""Calibrate on validation voice clips using the actual streaming detector; evaluate test clips."""
from pathlib import Path
import json, sys, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from wakeword import load_detector, score_wav
import onnxruntime as ort

report=json.loads((ROOT/'training_report.json').read_text())
model=load_detector()
model_hash=hashlib.sha256((ROOT.parent/'models'/'hey_bilal.onnx').read_bytes()).hexdigest()[:12]
scores={}
for split in ('validation','final_test'):
 cache=ROOT/'cache'/f'{split}_{model_hash}_g2_streaming_scores.json'
 if cache.exists():
  scores[split]=json.loads(cache.read_text())
  continue
 rows=[]
 paths=sorted(p for p in (ROOT/'cache'/split).glob('*.wav') if p.stem.startswith('0_') or p.stem.endswith('_pk'))
 for i,path in enumerate(paths):
  rows.append({'clip':path.name,'label':int(path.stem.split('_')[0]),'peak':score_wav(model,path)})
  if (i+1)%20==0:
   print(f'Streaming {split}: {i+1}/{len(paths)}',flush=True)
 cache.write_text(json.dumps(rows,indent=2))
 scores[split]=rows

# Validate against the disjoint middle third of real background embeddings as well.
data=np.load(ROOT/'assets'/'negative_features.npy',mmap_mode='r')
frames=report['embedding_frames']
start=len(data)//3
end=2*len(data)//3
background=np.stack([data[j:j+frames] for j in range(start,end-frames,frames)])
session=ort.InferenceSession(str(ROOT.parent/'models'/'hey_bilal.onnx'),providers=['CPUExecutionProvider'])
bg_scores=session.run(None,{'audio_features':background.astype(np.float32)})[0][:,0]
val_positive=np.array([r['peak'] for r in scores['validation'] if r['label']==1])
val_negative=np.array([r['peak'] for r in scores['validation'] if r['label']==0])
candidates=[]
for t in np.arange(.80,.991,.01):
 candidates.append((float(t),float(np.mean(val_positive>=t)),float(np.mean(val_negative>=t)),float(np.mean(bg_scores>=t))))
valid=[r for r in candidates if r[2]<=.05 and r[3]<=.005]
best=max(valid,key=lambda r:(r[1],-r[2],-r[3],r[0])) if valid else min(candidates,key=lambda r:(r[2]+r[3],-r[1]))
threshold=round(best[0],2)
metrics={}
for split,rows in scores.items():
 positive=[r['peak']>=threshold for r in rows if r['label']==1]
 negative=[r['peak']>=threshold for r in rows if r['label']==0]
 metrics[split]={'positive_clips':len(positive),'detected_positive_clips':sum(positive),
                 'positive_clip_recall':float(np.mean(positive)),
                 'negative_clips':len(negative),'false_trigger_negative_clips':sum(negative),
                 'negative_clip_false_trigger_rate':float(np.mean(negative))}
report.setdefault('endpoint_threshold',report['threshold'])
if 'metrics' in report:
 report['endpoint_metrics']=report.pop('metrics')
report['threshold']=threshold
report['streaming_metrics']=metrics
report['streaming_metrics_threshold']=threshold
report['streaming_metrics_consecutive_frames']=2
report['final_test_speaker_ids']=[560,600]
report.setdefault('revision','v2_shifted_hard_negatives_and_silence')
report['validation_background_window_false_positive_rate']=float(np.mean(bg_scores>=threshold))
report['streaming_threshold_selected_on']='validation voices and validation background only'
test_background=np.stack([data[j:j+frames] for j in range(end,len(data)-frames,frames)])
test_bg_scores=session.run(None,{'audio_features':test_background.astype(np.float32)})[0][:,0]
report['test_background_windows']={'count':len(test_bg_scores),'false_positive_windows':int(np.sum(test_bg_scores>=threshold)),
                                 'false_positive_window_rate':float(np.mean(test_bg_scores>=threshold))}
(ROOT/'training_report.json').write_text(json.dumps(report,indent=2))
config={'wakeword':{'phrase':'hey Bilal','model_path':'models/hey_bilal.onnx',
                   'threshold':threshold,'sample_rate':16000,'chunk_samples':1280,
                   'cooldown_seconds':.6,'consecutive_frames':2,'status':'synthetic_baseline'}}
(ROOT.parent/'config'/'config.yaml').write_text(json.dumps(config,indent=2))
print(json.dumps({'threshold':threshold,'streaming_metrics':metrics},indent=2),flush=True)
