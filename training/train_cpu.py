"""CPU baseline: multi-speaker Piper audio -> openWakeWord embeddings -> MLP -> ONNX.
Train, validation and test voices are disjoint. No microphone audio is collected.
This is a synthetic baseline, not a production qualification.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import json, time, hashlib, warnings
import numpy as np
from scipy.signal import resample_poly, lfilter
from scipy.io import wavfile
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
from piper import PiperVoice, SynthesisConfig
from openwakeword.utils import AudioFeatures
import onnx
from onnx import helper, numpy_helper, TensorProto
import onnxruntime as ort

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
CACHE = ROOT / 'cache'
CACHE.mkdir(exist_ok=True)
MODELS = ROOT.parent / 'models'
MODELS.mkdir(exist_ok=True)
RNG = np.random.default_rng(42)
NEGATIVE_PHRASES = [
 'hey Bill', 'hey Bella', 'hey Billy', 'hey belay', 'hey below', 'hey be loud',
 'hey be well', 'hey Bil', 'hello Bilal', 'Bilal', 'hey', 'okay Google',
 'hey Siri', 'hey Jarvis', 'hey Alexa', 'tell me the time', 'open the browser',
 'what is the weather today', 'can you hear me', 'please open my files',
 'the bill is paid', 'he will call', 'it will all be okay', 'we are below the hill',
 'this is a normal conversation', 'bring me a glass of water', 'turn on the light',
 'I have a meeting tomorrow', 'play some music', 'good morning', 'thank you',
 'what do you think', 'call my friend', 'I am busy right now', 'have a nice day',
]
SPLITS = {'train': (0, 400), 'validation': (400, 480), 'test': (480, 560)}

def make_audio():
 voice = PiperVoice.load(ASSETS / 'voice.onnx')
 print('Generating synthetic wake-word clips', flush=True)
 start = time.time()
 for split, (lo, hi) in {**SPLITS, 'final_test': (560,600)}.items():
  folder = CACHE / split
  folder.mkdir(exist_ok=True)
  for sid in range(lo, hi):
   for label in (1, 0):
    path = folder / (f'1_{sid}_pk.wav' if label else f'0_{sid}.wav')
    if path.exists():
     continue
    text = ('hey [[b\u026al\u02c8\u0251\u02d0l]]' if sid % 2 else 'hey [[b\u026al\u02c8a\u02d0l]]') if label else NEGATIVE_PHRASES[(sid-lo) % len(NEGATIVE_PHRASES)]
    config = SynthesisConfig(speaker_id=sid, length_scale=float(RNG.uniform(.78,1.12)),
                            noise_scale=.667, noise_w_scale=.8)
    chunks = list(voice.synthesize(text, syn_config=config))
    audio = np.concatenate([c.audio_float_array for c in chunks])
    audio = resample_poly(audio, 320, 441)
    # Keep the complete utterance. The classifier uses 24 embedding frames (~2.6s context).
    wavfile.write(path, 16000, np.clip(audio*32767,-32768,32767).astype(np.int16))
   if (sid-lo+1) % 20 == 0:
    print(f'{split}: {sid-lo+1}/{hi-lo} voices, {time.time()-start:.0f}s', flush=True)
 print('Audio generation complete', flush=True)

FRAMES = 24
CLIP_SAMPLES = 64000

def prepare_audio(audio, augment=False):
 x = audio.astype(np.float32) / 32768
 if augment:
  x = x * RNG.uniform(.35,1.0)
  # Short decaying room response; noise stays below speech level.
  if RNG.random() < .6:
   taps = np.zeros(3201, dtype=np.float32)
   taps[0] = 1
   for delay in (400, 960, 1760, 3200):
    taps[delay] = float(RNG.uniform(.015,.10))
   x = np.convolve(x, taps)
  if RNG.random() < .5:
   x = lfilter([.6], [1,-.4], x)
  rms = max(float(np.sqrt(np.mean(x*x))), .001)
  x = x + RNG.normal(0, rms*10**(-RNG.uniform(15,35)/20), len(x))
 # Final window covers the phrase and 100-300 ms of trailing room context.
 tail = int(RNG.uniform(.10,.30)*16000) if augment else 2400
 if len(x) > CLIP_SAMPLES-tail:
  raise ValueError('Utterance too long; regenerate with a faster voice setting')
 out = np.zeros(CLIP_SAMPLES, np.float32)
 out[-tail-len(x):-tail] = x
 if augment:
  out += RNG.normal(0, .0003, len(out))
 return np.clip(out*32768,-32768,32767).astype(np.int16)

def extract():
 features = AudioFeatures(melspec_model_path=str(ASSETS/'melspectrogram.onnx'),
                          embedding_model_path=str(ASSETS/'embedding_model.onnx'),
                          inference_framework='onnx', ncpu=2)
 for split in SPLITS:
  output = CACHE / f'{split}_features_pk.npz'
  if output.exists():
   print('Cached features:', split, flush=True)
   continue
  waves, labels = [], []
  for path in sorted(p for p in (CACHE/split).glob('*.wav') if p.stem.startswith('0_') or p.stem.endswith('_pk')):
   _, audio = wavfile.read(path)
   for repeat in range(4 if split == 'train' else 1):
    waves.append(prepare_audio(audio, augment=split=='train'))
    labels.append(int(path.stem.split('_')[0]))
  batches=[]
  for offset in range(0,len(waves),24):
   embedding = features.embed_clips(np.stack(waves[offset:offset+24]), batch_size=64,ncpu=2)
   batches.append(embedding[:,-FRAMES:,:])
   print(f'{split} features: {min(offset+24,len(waves))}/{len(waves)}',flush=True)
  np.savez_compressed(output,x=np.concatenate(batches),y=np.array(labels))


def general_negatives():
 data = np.load(ASSETS/'negative_features.npy', mmap_mode='r')
 print('Background feature shape:', data.shape,flush=True)
 if data.ndim != 2 or data.shape[1] != 96:
  raise ValueError(f'Expected continuous (frames,96) background features, got {data.shape}')
 # Contiguous thirds ensure no shared/overlapping negative windows across splits.
 result={}
 boundaries=np.linspace(0,len(data),4,dtype=int)
 for i,split in enumerate(SPLITS):
  start,end=boundaries[i:i+2]
  indices=np.arange(start,end-FRAMES,FRAMES)
  limit=16000 if split=='train' else 10000
  if len(indices)>limit:
   indices=RNG.choice(indices,limit,replace=False)
  result[split]=np.stack([data[j:j+FRAMES].astype(np.float32) for j in indices])
 return result


def export(scaler, model):
 nodes=[helper.make_node('Flatten',['audio_features'],['flat'],axis=1),
        helper.make_node('Sub',['flat','mean'],['centered']),
        helper.make_node('Div',['centered','scale'],['scaled'])]
 tensors=[numpy_helper.from_array(scaler.mean_.astype(np.float32),'mean'),
          numpy_helper.from_array(scaler.scale_.astype(np.float32),'scale')]
 last='scaled'
 for i,(weight,bias) in enumerate(zip(model.coefs_,model.intercepts_)):
  tensors += [numpy_helper.from_array(weight.astype(np.float32),f'w{i}'),
              numpy_helper.from_array(bias.astype(np.float32),f'b{i}')]
  nodes.append(helper.make_node('Gemm',[last,f'w{i}',f'b{i}'],[f'z{i}']))
  last='hey_bilal' if i==len(model.coefs_)-1 else f'a{i}'
  nodes.append(helper.make_node('Sigmoid' if i==len(model.coefs_)-1 else 'Relu',[f'z{i}'],[last]))
 graph=helper.make_graph(nodes,'hey_bilal',
  [helper.make_tensor_value_info('audio_features',TensorProto.FLOAT,[None,FRAMES,96])],
  [helper.make_tensor_value_info('hey_bilal',TensorProto.FLOAT,[None,1])],tensors)
 exported=helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)],producer_name='BilalAI CPU baseline')
 exported.ir_version=8
 onnx.checker.check_model(exported)
 path=MODELS/'hey_bilal.onnx'
 onnx.save(exported,path)
 return path


def fit():
 negatives=general_negatives()
 sets={}
 for split in SPLITS:
  cached=np.load(CACHE/f'{split}_features_pk.npz')
  x=np.concatenate([cached['x'],negatives[split]])
  y=np.concatenate([cached['y'],np.zeros(len(negatives[split]),dtype=int)])
  sets[split]=(x,y)
 x,y=sets['train']
 # Background-only shifts expose every portion of hard negatives to the classifier,
 # instead of teaching it only the final aligned endpoint of each negative phrase.
 af=AudioFeatures(melspec_model_path=str(ASSETS/'melspectrogram.onnx'),
                  embedding_model_path=str(ASSETS/'embedding_model.onnx'),inference_framework='onnx',ncpu=2)
 silent_frame=af._get_embeddings(np.zeros(CLIP_SAMPLES,dtype=np.int16))[-1]
 source=np.load(CACHE/'train_features_pk.npz')
 hard_neg=source['x'][source['y']==0]
 variants=[]
 for shift in (-12,-6,6,12):
  shifted=np.tile(silent_frame,(len(hard_neg),FRAMES,1))
  if shift>0:
   shifted[:,shift:,:]=hard_neg[:,:-shift,:]
  else:
   shifted[:,:shift,:]=hard_neg[:,-shift:,:]
  variants.append(shifted)
 variants.append(np.tile(silent_frame,(128,FRAMES,1)))
 x=np.concatenate([x,*variants])
 y=np.concatenate([y,np.zeros(sum(len(v) for v in variants),dtype=int)])
 sets['train']=(x,y)
 print('Added shifted hard negatives and silence:',sum(len(v) for v in variants),flush=True)
 adversarial_path=CACHE/'hee_haa_v3'/'train_features.npz'
 if adversarial_path.exists():
  adversarial=np.load(adversarial_path)
  x=np.concatenate([x,adversarial['x']])
  y=np.concatenate([y,adversarial['y']])
  sets['train']=(x,y)
  print('Added explicit hee-haa hard-negative windows:',len(adversarial['x']),flush=True)
 scaler=StandardScaler().fit(x.reshape(len(x),-1))
 model=MLPClassifier(hidden_layer_sizes=(64,32),batch_size=128,max_iter=100,
                     random_state=42,early_stopping=False,alpha=.02,learning_rate_init=.0007,
                     verbose=True,n_iter_no_change=12)
 # Balance classes without making every negative dominate the loss.
 weights=np.where(y==1,len(y)/(2*sum(y)),len(y)/(2*sum(y==0)))
 model.fit(scaler.transform(x.reshape(len(x),-1)),y,sample_weight=weights)
 scores={split:model.predict_proba(scaler.transform(x.reshape(len(x),-1)))[:,1]
         for split,(x,y) in sets.items()}
 val_y=sets['validation'][1]
 candidates=[]
 for threshold in np.arange(.10,.96,.05):
  p=scores['validation']>=threshold
  recall=float(np.mean(p[val_y==1]))
  false_positive=float(np.mean(p[val_y==0]))
  candidates.append((float(threshold),recall,false_positive))
 valid=[c for c in candidates if c[2]<=.005]
 best=max(valid,key=lambda c:(c[1],-c[2],c[0])) if valid else min(candidates,key=lambda c:(c[2],-c[1]))
 threshold=best[0]
 path=export(scaler,model)
 session=ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
 test_x,test_y=sets['test']
 onnx_scores=session.run(None,{'audio_features':test_x[:64].astype(np.float32)})[0][:,0]
 np.testing.assert_allclose(onnx_scores,scores['test'][:64],atol=1e-5,rtol=1e-4)
 metrics={}
 for split,(_,labels) in sets.items():
  predicted=scores[split]>=threshold
  metrics[split]={
   'positive_examples':int(sum(labels)), 'negative_examples':int(sum(labels==0)),
   'positive_recall':float(np.mean(predicted[labels==1])),
   'negative_window_false_positive_rate':float(np.mean(predicted[labels==0])),
   'confusion_matrix_tn_fp_fn_tp':confusion_matrix(labels,predicted).ravel().tolist(),
  }
 report={'status':'synthetic_baseline_real_microphone_test_required','target_phrase':'hey Bilal',
         'seed':42,'embedding_frames':FRAMES,'threshold':threshold,'metrics':metrics,
         'split_speaker_ids':SPLITS,'training_iterations':model.n_iter_,
         'onnx_sklearn_max_error':float(np.max(np.abs(onnx_scores-scores['test'][:64]))),
         'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'limitations':['Synthetic English voices; Pakistani accent has not been tested.',
                        'Negative window rate is not a real-world false activations per hour measurement.',
                        'Small baseline dataset; tune against held-out microphone recordings before always-on use.'],
         'sources':{'voices':'https://huggingface.co/rhasspy/piper-voices',
                    'negative_features':'https://huggingface.co/datasets/davidscripka/openwakeword_features',
                    'feature_extractors':'https://github.com/dscripka/openWakeWord'}}
 (ROOT/'training_report.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
 print('Exported',path,flush=True)

if __name__=='__main__':
 make_audio()
 extract()
 fit()
