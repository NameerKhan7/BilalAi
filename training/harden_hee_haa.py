"""Generate confusable hee-haa sounds and add full-window hard negatives."""
from pathlib import Path
import sys, json, time
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from piper import PiperVoice, SynthesisConfig
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from wakeword import load_detector, score_wav
from train_cpu import prepare_audio, AudioFeatures, FRAMES, ASSETS

RNG=np.random.default_rng(2026)
TEXTS=['[[h\u02c8i\u02d0 h\u02c8\u0251\u02d0]]',
       '[[h\u02c8i\u02d0 h\u02c8a\u02d0]]',
       '[[h\u02c8i\u02d0 h\u02c8\u0254\u02d0]]',
       'hey [[h\u02c8\u0251\u02d0]]']
SPLITS={'train':range(40),'validation':range(620,640),'test':range(660,680)}
CACHE=ROOT/'cache'/'hee_haa_v3'
CACHE.mkdir(exist_ok=True)
voice=PiperVoice.load(ASSETS/'voice.onnx')
for split,speakers in SPLITS.items():
 folder=CACHE/split
 folder.mkdir(exist_ok=True)
 for sid in speakers:
  cases=[(0,j,text) for j,text in enumerate(TEXTS)]
  if split!='train':
   cases.append((1,0,'hey [[b\u026al\u02c8\u0251\u02d0l]]'))
  for label,variant,text in cases:
   path=folder/f'{label}_{sid}_{variant}.wav'
   if path.exists():
    continue
   settings=SynthesisConfig(speaker_id=sid,length_scale=float(RNG.uniform(.8,1.15)))
   chunks=list(voice.synthesize(text,syn_config=settings))
   audio=resample_poly(np.concatenate([c.audio_float_array for c in chunks]),320,441)
   wavfile.write(path,16000,np.clip(audio*32767,-32768,32767).astype(np.int16))
 print(f'Generated {split}: {len(list(folder.glob("*.wav")))} clips',flush=True)

# Measure this adversarial corpus against the previous model before changing weights.
before=CACHE/'before.json'
if not before.exists():
 model=load_detector()
 rows=[]
 for path in sorted((CACHE/'validation').glob('*.wav')):
  if len(rows)>=25:
   break
  rows.append({'clip':path.name,'label':int(path.stem[0]),
               'single_frame_score':score_wav(model,path,1),
               'three_frame_score':score_wav(model,path,3)})
 before.write_text(json.dumps(rows,indent=2))
 print('Before-model regression samples saved',flush=True)

output=CACHE/'train_features.npz'
if not output.exists():
 af=AudioFeatures(melspec_model_path=str(ASSETS/'melspectrogram.onnx'),
                  embedding_model_path=str(ASSETS/'embedding_model.onnx'),inference_framework='onnx',ncpu=2)
 waves=[]
 for path in sorted((CACHE/'train').glob('*.wav')):
  _,audio=wavfile.read(path)
  for repeat in range(2):
   waves.append(prepare_audio(audio,augment=True))
 batches=[]
 for start in range(0,len(waves),24):
  embedded=af.embed_clips(np.stack(waves[start:start+24]),batch_size=64,ncpu=2)
  # Include each position at which a negative sound could be encountered.
  for offset in range(0,embedded.shape[1]-FRAMES+1,3):
   batches.append(embedded[:,offset:offset+FRAMES,:])
  print(f'Hee-haa features: {min(start+24,len(waves))}/{len(waves)}',flush=True)
 x=np.concatenate(batches)
 np.savez_compressed(output,x=x,y=np.zeros(len(x),dtype=int))
 print(f'Saved {len(x)} adversarial negative windows',flush=True)
