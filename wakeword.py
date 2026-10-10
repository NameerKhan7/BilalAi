"""Test the trained hey Bilal detector on a microphone or a WAV file."""
from pathlib import Path
import argparse, json, time, math
import numpy as np
from openwakeword.model import Model
from wakeword_gate import DetectionGate
ROOT = Path(__file__).resolve().parent


def load_settings(profile='baseline'):
 if profile=='personalized':
  return json.loads((ROOT/'models/personalized/calibration.json').read_text(encoding='utf-8'))
 path=ROOT/'config/config.yaml'
 return json.loads(path.read_text(encoding='utf-8'))['wakeword']

def load_detector(model_path=None):
 assets=ROOT/'models'
 model_path=Path(model_path) if model_path is not None else ROOT/'models'/'hey_bilal.onnx'
 if not model_path.exists():
  raise FileNotFoundError(f'Wake-word model is missing: {model_path}')
 detector=Model(wakeword_models=[str(model_path)],inference_framework='onnx',
              melspec_model_path=str(assets/'melspectrogram.onnx'),
              embedding_model_path=str(assets/'embedding_model.onnx'),ncpu=1)
 # Pre-fill the audio context before the user starts speaking.
 for _ in range(38):
  detector.predict(np.zeros(1280,dtype=np.int16))
 return detector

def score_wav(model,path,consecutive_frames=2):
 from scipy.io import wavfile
 from scipy.signal import resample_poly
 sr,audio=wavfile.read(path)
 if audio.dtype.kind=='f':
  audio=np.clip(audio*32768,-32768,32767).astype(np.int16)
 elif audio.dtype!=np.int16:
  raise ValueError('Use 16-bit PCM or floating-point WAV audio.')
 if audio.ndim==2:
  audio=audio.astype(np.float32).mean(axis=1).astype(np.int16)
 if sr!=16000:
  divisor=math.gcd(sr,16000)
  audio=resample_poly(audio.astype(np.float32),16000//divisor,sr//divisor).astype(np.int16)
 audio=np.concatenate([np.zeros(48640,dtype=np.int16),audio,np.zeros(16000,dtype=np.int16)])
 model.reset()
 scores=[]
 gate=DetectionGate(.5,consecutive_frames)
 for offset in range(0,len(audio),1280):
  frame=audio[offset:offset+1280]
  if len(frame)<1280:
   frame=np.pad(frame,(0,1280-len(frame)))
  raw_score=float(model.predict(frame)['hey_bilal'])
  if offset<48640:
   continue
  _,stable_score=gate.update(raw_score,offset/16000)
  scores.append(stable_score)
 return max(scores)

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--wav',type=Path)
 parser.add_argument('--model',choices=['baseline','personalized'],default='baseline')
 parser.add_argument('--device',type=int)
 parser.add_argument('--list-devices',action='store_true')
 parser.add_argument('--threshold',type=float)
 parser.add_argument('--seconds',type=float,default=60)
 parser.add_argument('--consecutive-frames',type=int,default=2)
 parser.add_argument('--cooldown',type=float,default=.6)
 args=parser.parse_args()
 import sounddevice as sd
 if args.list_devices:
  print(sd.query_devices())
  return
 report=load_settings(args.model)
 threshold=args.threshold if args.threshold is not None else report['threshold']
 if not 0<threshold<1:
  parser.error('Threshold must be between 0 and 1.')
 if args.cooldown<0:
  parser.error('cooldown cannot be negative.')
 if args.consecutive_frames<1:
  parser.error('consecutive-frames must be positive.')
 model_path=ROOT/'models/personalized/hey_bilal.onnx' if args.model=='personalized' else None
 model=load_detector(model_path)
 if args.wav:
  score=score_wav(model,args.wav,args.consecutive_frames)
  print(json.dumps({'file':str(args.wav),'confirmed_score':score,'threshold':threshold,'consecutive_frames':args.consecutive_frames,'detected':score>=threshold}))
  return
 print(f'Model: {args.model}.',flush=True)
 print(f'Confirmation: {args.consecutive_frames} consecutive 80ms frames.',flush=True)
 print('Audio is processed locally; it is not recorded or uploaded.',flush=True)
 gate=DetectionGate(threshold,args.consecutive_frames,args.cooldown)
 peak=0
 confirmed_peak=0
 processing_ms=[]
 try:
  with sd.RawInputStream(samplerate=16000,blocksize=1280,dtype='int16',channels=1,device=args.device,latency='low') as stream:
   start=time.monotonic()
   print(f'Listening for hey Bilal for {args.seconds:g}s. Threshold {threshold:.2f}. Ctrl+C to stop.',flush=True)
   print(f'Microphone latency: {stream.latency*1000:.0f}ms. Repeat cooldown: {args.cooldown:g}s.',flush=True)
   while time.monotonic()-start<args.seconds:
    raw,overflow=stream.read(1280)
    if overflow:
     gate.reset()
     print('Audio overflow; some samples were lost.',flush=True)
    processing_start=time.perf_counter()
    score=float(model.predict(np.frombuffer(raw,dtype=np.int16))['hey_bilal'])
    processing_ms.append((time.perf_counter()-processing_start)*1000)
    peak=max(peak,score)
    detected,stable_score=gate.update(score,time.monotonic())
    confirmed_peak=max(confirmed_peak,stable_score)
    if detected:
     print(f'HEY BILAL detected: {stable_score:.3f}',flush=True)

 except KeyboardInterrupt:
  pass
 print(f'Finished. Highest raw score: {peak:.3f}; confirmed score: {confirmed_peak:.3f}',flush=True)
 if processing_ms:
  print(f'Processing per 80ms block: median {np.median(processing_ms):.1f}ms; p95 {np.percentile(processing_ms,95):.1f}ms.',flush=True)

if __name__=='__main__':
 main()
