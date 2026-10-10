"""Train a personal candidate with recording-group holdouts; keep baseline untouched."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys,json,hashlib,time,warnings
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from openwakeword.utils import AudioFeatures
import onnxruntime as ort
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
SESSION=ROOT/'recordings/session_02a1911e'
OUTPUT=ROOT.parent/'models/personalized'
OUTPUT.mkdir(exist_ok=True)
RNG=np.random.default_rng(417)
FRAMES=24
PREFIX=48640


def crop_voice(audio):
 x=audio.astype(np.float32)/32768
 pad=np.pad(x,(0,(-len(x))%320))
 rms=np.sqrt(np.mean(pad.reshape(-1,320)**2,axis=1))
 threshold=max(.003,float(np.quantile(rms,.2))*3,float(rms.max())*.08)
 active=np.flatnonzero(rms>threshold)
 if len(active)==0: raise ValueError('No speech energy found in a recording.')
 start=max(0,int(active[0]*320)-2560)
 end=min(len(x),int((active[-1]+1)*320)+3840)
 return x[start:end],{'start_seconds':start/16000,'end_seconds':end/16000,'energy_threshold':threshold}


af=AudioFeatures(melspec_model_path=str(ROOT.parent/'models/melspectrogram.onnx'),
                 embedding_model_path=str(ROOT.parent/'models/embedding_model.onnx'),inference_framework='onnx',ncpu=1)
def streaming_features(audio):
 af.reset()
 padded=np.concatenate([np.zeros(PREFIX,dtype=np.int16),audio,np.zeros(16000,dtype=np.int16)])
 windows=[]
 times=[]
 for start in range(0,len(padded),1280):
  frame=padded[start:start+1280]
  if len(frame)<1280: frame=np.pad(frame,(0,1280-len(frame)))
  af(frame)
  if start>=PREFIX:
   windows.append(af.get_features(FRAMES)[0].copy())
   times.append((start+1280)/16000)
 return np.stack(windows),np.array(times)


items=json.loads((SESSION/'samples.json').read_text())['samples']
cache=SESSION/'personal_training_features.npz'
if cache.exists():
 stored=np.load(cache)
 personal_x,personal_y,groups=stored['x'],stored['y'],stored['groups']
 evaluation={}
 for item in items:
  evaluation[item['file']]=stored['eval_'+item['file']]
 print('Using cached personal streaming features',flush=True)
else:
 xs=[]; ys=[]; gs=[]; evaluation={}; crops=[]
 for item in items:
  sr,audio=wavfile.read(SESSION/item['file'])
  if sr!=16000 or audio.dtype!=np.int16 or audio.ndim!=1: raise ValueError('Expected mono 16kHz int16 recordings.')
  label=int(item['label']=='hey_bilal')
  evaluation[item['file']]=streaming_features(audio)[0]
  clipped,crop=crop_voice(audio)
  crops.append({'file':item['file'],**crop})
  for variant in range(12):
   x=clipped.copy()
   if variant:
    speed=float(RNG.uniform(.94,1.06))
    x=resample_poly(x,100,round(speed*100))
    x=x*RNG.uniform(.65,1.3)
    speech_rms=max(float(np.sqrt(np.mean(x*x))),.001)
    x=x+RNG.normal(0,speech_rms*RNG.uniform(.015,.06),len(x))
    if variant%3==0:
     echo=np.pad(x[:-800],(800,0)) if len(x)>800 else np.zeros_like(x)
     x=x+.05*echo
   sample=np.clip(x*32768,-32768,32767).astype(np.int16)
   windows,times=streaming_features(sample)
   if label:
    speech_end=PREFIX/16000+len(sample)/16000
    selected=(times>=speech_end-.20)&(times<=speech_end+.16)
   else:
    selected=np.arange(len(windows))%2==0
   if not np.any(selected): raise ValueError('No aligned training windows.')
   chosen=windows[selected]
   xs.append(chosen); ys.extend([label]*len(chosen)); gs.extend([item['number']]*len(chosen))
  print('Prepared recording:',item['file'],flush=True)
 personal_x=np.concatenate(xs); personal_y=np.array(ys); groups=np.array(gs)
 np.savez_compressed(cache,x=personal_x,y=personal_y,groups=groups,**{'eval_'+k:v for k,v in evaluation.items()})
 (SESSION/'personal_training_crops.json').write_text(json.dumps(crops,indent=2))

# Transfer the baseline feature scaling and trained weights; do not relearn generic rejection from scratch.
import onnx
from onnx import numpy_helper
baseline=onnx.load(ROOT.parent/'models/hey_bilal.onnx')
baseline_arrays={a.name:numpy_helper.to_array(a) for a in baseline.graph.initializer}
source=np.load(ROOT/'cache/train_features_pk.npz')
base_x=[]; base_y=[]
for label in (0,1):
 indices=np.flatnonzero(source['y']==label)
 indices=RNG.choice(indices,500,replace=False)
 base_x.append(source['x'][indices]); base_y.extend([label]*len(indices))
background=np.load(ROOT/'assets/negative_features.npy',mmap_mode='r')
indices=RNG.choice(np.arange(0,len(background)//3-FRAMES,FRAMES),2000,replace=False)
base_x.append(np.stack([background[j:j+FRAMES] for j in indices])); base_y.extend([0]*len(indices))
extra=np.load(ROOT/'cache/hee_haa_v3/train_features.npz')
indices=RNG.choice(len(extra['x']),500,replace=False)
base_x.append(extra['x'][indices]); base_y.extend([0]*len(indices))

stream_negative_cache=ROOT/'cache/personalized_stream_negatives.npz'
if stream_negative_cache.exists():
 stream_negatives=np.load(stream_negative_cache)['x']
else:
 clips=sorted((ROOT/'cache/train').glob('0_*.wav'))[:120]
 negatives=[]
 for index,path in enumerate(clips):
  _,audio=wavfile.read(path)
  windows,_=streaming_features(audio)
  negatives.append(windows[::2])
  if (index+1)%30==0: print('Prepared full-stream negative clips:',index+1,flush=True)
 stream_negatives=np.concatenate(negatives)
 np.savez_compressed(stream_negative_cache,x=stream_negatives)
base_x.append(stream_negatives); base_y.extend([0]*len(stream_negatives))

base_x=np.concatenate(base_x); base_y=np.array(base_y)


def fit_head(mask,seed):
 x=np.concatenate([base_x,personal_x[mask]])
 y=np.concatenate([base_y,personal_y[mask]])
 weights=np.where(y==1,len(y)/(2*np.sum(y==1)),len(y)/(2*np.sum(y==0)))
 weights[len(base_y):]*=4
 scaler=StandardScaler().fit(x.reshape(len(x),-1))
 scaler.mean_=baseline_arrays['mean'].astype(np.float64)
 scaler.scale_=baseline_arrays['scale'].astype(np.float64)
 scaler.var_=scaler.scale_**2
 head=MLPClassifier(hidden_layer_sizes=(64,32),batch_size=128,max_iter=100,
                    random_state=seed,alpha=.12,learning_rate_init=.0001,warm_start=True,
                    tol=.0005,n_iter_no_change=10,verbose=False)
 with threadpool_limits(limits=1):
  data=scaler.transform(x.reshape(len(x),-1))
  head.max_iter=1
  with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   head.fit(data,y,sample_weight=weights)
  for index in range(len(head.coefs_)):
   head.coefs_[index][:]=baseline_arrays[f'w{index}']
   head.intercepts_[index][:]=baseline_arrays[f'b{index}']
  head.max_iter=100
  head.n_iter_=0
  head.best_loss_=float('inf')
  head.loss_curve_=[]
  head._no_improvement_count=0
  head.fit(data,y,sample_weight=weights)
 return scaler,head


def stable_score(scaler,head,windows):
 probabilities=head.predict_proba(scaler.transform(windows.reshape(len(windows),-1)))[:,1]
 return float(np.max(np.minimum(probabilities[:-1],probabilities[1:])))


folds=[]
for number in sorted(set(groups.tolist())):
 scaler,head=fit_head(groups!=number,40+number)
 rows=[]
 for item in items:
  if item['number']==number:
   score=stable_score(scaler,head,evaluation[item['file']])
   row={**item,'confirmed_score':score}
   rows.append(row); folds.append(row)
 print('Held-out recording pair',number,json.dumps(rows),flush=True)

positive=[r['confirmed_score'] for r in folds if r['label']=='hey_bilal']
negative=[r['confirmed_score'] for r in folds if r['label']=='hee_haa']
threshold=.8
if min(positive)<threshold or max(negative)>=threshold:
 gap=min(positive)-max(negative)
 if gap>.1:
  threshold=round(float(np.clip((min(positive)+max(negative))/2,.3,.95)),2)
report={'status':'candidate_requires_fresh_microphone_validation','source_session':str(SESSION.relative_to(ROOT.parent)),
        'threshold':threshold,'consecutive_frames':2,'cooldown_seconds':.6,
        'cross_validation':'leave one original positive/negative recording pair out; augmentations excluded with their original',
        'initialization':'baseline weights and scaling; full-stream negative examples retained',
        'baseline_sha256':hashlib.sha256((ROOT.parent/'models/hey_bilal.onnx').read_bytes()).hexdigest(),
        'recording_group_count':len(set(groups.tolist())), 'personal_training_windows':len(personal_x),
        'folds':folds,'held_out_positive_hits':sum(s>=threshold for s in positive),'held_out_positive_count':len(positive),
        'held_out_negative_hits':sum(s>=threshold for s in negative),'held_out_negative_count':len(negative),
        'limitations':['Only five original recordings per class; cross-validation is diagnostic.',
                       'Fresh positive and negative microphone recordings are required before replacing the baseline.',
                       'General background reliability is not established by this personal calibration.']}
scaler,head=fit_head(np.ones(len(groups),dtype=bool),417)
import train_cpu
train_cpu.MODELS=OUTPUT
path=train_cpu.export(scaler,head)
session=ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
x=personal_x[:32].astype(np.float32)
expected=head.predict_proba(scaler.transform(x.reshape(len(x),-1)))[:,1]
actual=session.run(None,{'audio_features':x})[0][:,0]
np.testing.assert_allclose(actual,expected,atol=1e-5,rtol=1e-4)
report['onnx_sklearn_max_error']=float(np.max(np.abs(actual-expected)))
report['model_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
report['training_iterations']=head.n_iter_
(OUTPUT/'calibration.json').write_text(json.dumps(report,indent=2))
(ROOT/'personalized_training_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['threshold','held_out_positive_hits','held_out_positive_count','held_out_negative_hits','held_out_negative_count','status']},indent=2),flush=True)
print('Candidate exported:',path,flush=True)
