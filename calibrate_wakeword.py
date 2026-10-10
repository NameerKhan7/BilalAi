"""Collect labeled local voice samples; diagnose threshold/confirmation misses.
Nothing is uploaded and no live detector settings are changed.
"""
from pathlib import Path
import argparse,json,uuid,math,hashlib
import numpy as np
from scipy.io import wavfile
from wakeword import load_detector,load_settings
ROOT=Path(__file__).resolve().parent

def analyze_clips(session, model, settings=None, profile=None):
 metadata=json.loads((session/'samples.json').read_text(encoding='utf-8'))
 rows=[]
 for item in metadata['samples']:
  sr,audio=wavfile.read(session/item['file'])
  if sr!=16000 or audio.dtype!=np.int16 or audio.ndim!=1:
   raise ValueError('Calibration clips must be mono 16kHz, 16-bit PCM.')
  model.reset()
  padded=np.concatenate([np.zeros(48640,dtype=np.int16),audio,np.zeros(16000,dtype=np.int16)])
  trace=[]
  for start in range(0,len(padded),1280):
   frame=padded[start:start+1280]
   if len(frame)<1280: frame=np.pad(frame,(0,1280-len(frame)))
   score=float(model.predict(frame)['hey_bilal'])
   if start>=48640:
    trace.append(score)
  scores={str(n):max(min(trace[i:i+n]) for i in range(len(trace)-n+1)) for n in (1,2,3)}
  normalized=audio.astype(np.float32)/32768
  row={**item,'scores_by_consecutive_frames':scores,
       'audio_rms':float(np.sqrt(np.mean(normalized*normalized))),
       'audio_peak':float(np.max(np.abs(normalized))),
       'clipping_fraction':float(np.mean(np.abs(audio.astype(np.int32))>=32760))}
  rows.append(row)
  print(f"{item['label']} #{item['number']}: raw {scores['1']:.3f}, confirmed {scores['2']:.3f}",flush=True)
 threshold=settings['threshold'] if settings is not None else metadata.get('policy',{}).get('threshold',load_settings('baseline')['threshold'])
 positive=[r for r in rows if r['label']=='hey_bilal']
 negative=[r for r in rows if r['label']!='hey_bilal']
 if not positive or not negative:
  raise ValueError('Both positive and negative recordings are required.')
 candidates=[]
 for frames in (1,2,3):
  for t in np.arange(.10,.991,.01):
   hits=int(sum(r['scores_by_consecutive_frames'][str(frames)]>=t for r in positive))
   false_hits=int(sum(r['scores_by_consecutive_frames'][str(frames)]>=t for r in negative))
   if false_hits==0:
    candidates.append({'threshold':round(float(t),2),'consecutive_frames':frames,
                       'positive_hits':hits,'negative_hits':false_hits})
 best=max(candidates,key=lambda c:(c['positive_hits'],c['consecutive_frames']==2,c['consecutive_frames']==3,c['threshold'])) if candidates else None
 if best is not None and best['positive_hits']<math.ceil(.8*len(positive)):
  best=None
 current={'threshold':threshold,'consecutive_frames':2,
          'positive_hits':sum(r['scores_by_consecutive_frames']['2']>=threshold for r in positive),
          'positive_count':len(positive),
          'negative_hits':sum(r['scores_by_consecutive_frames']['2']>=threshold for r in negative),
          'negative_count':len(negative),
          'negative_hits_by_label':{label:sum(r['scores_by_consecutive_frames']['2']>=threshold for r in negative if r['label']==label) for label in sorted({r['label'] for r in negative})}}
 # This is a diagnostic candidate, not independent validation or a production guarantee.
 result={'model_profile':profile or metadata.get('model_profile','baseline'),
         'model_sha256':settings.get('model_sha256',settings.get('sha256')) if settings is not None else metadata.get('model_sha256'),
         'current_policy':current,'diagnostic_candidate':best,'clips':rows,
         'limitation':'Small calibration set; validate any proposed change using a separate fresh recording session.',
         'settings_changed':False}
 output_path=session/(f'analysis_{profile}.json' if profile is not None and profile!=metadata.get('model_profile','baseline') else 'analysis.json')
 output_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
 print('\nCURRENT POLICY:',json.dumps(current),flush=True)
 print('DIAGNOSTIC CANDIDATE:',json.dumps(best),flush=True)
 print('Saved local report:',output_path,flush=True)
 return result

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--samples',type=int,default=5)
 parser.add_argument('--other-samples',type=int,default=0)
 parser.add_argument('--model',choices=['baseline','personalized'])
 parser.add_argument('--seconds',type=float,default=3)
 parser.add_argument('--device',type=int)
 parser.add_argument('--analyze-only',type=Path)
 args=parser.parse_args()
 if args.other_samples<0 or args.other_samples>3:
  parser.error('other-samples must be between 0 and 3.')
 if args.samples<3 or not 2<=args.seconds<=10:
  parser.error('Use at least 3 samples and 2-10 seconds per recording.')
 profile=args.model
 if profile is None and args.analyze_only:
  profile=json.loads((args.analyze_only/'samples.json').read_text()).get('model_profile','baseline')
 profile=profile or 'baseline'
 model_path=ROOT/'models/personalized/hey_bilal.onnx' if profile=='personalized' else ROOT/'models/hey_bilal.onnx'
 settings=load_settings(profile)
 model=load_detector(model_path)
 print(f'Model: {profile}.',flush=True)
 if args.analyze_only:
  analyze_clips(args.analyze_only,model,settings,profile)
  return
 import sounddevice as sd
 session=ROOT/'training/recordings'/('session_'+uuid.uuid4().hex[:8])
 session.mkdir(parents=True)
 print('This saves short microphone recordings locally for calibration. Nothing is uploaded.',flush=True)
 print('Use your normal voice and usual microphone distance. Say each phrase only once.',flush=True)
 samples=[]
 manifest={'sample_rate':16000,'samples':samples,'model_profile':profile,
           'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
           'policy':{'threshold':settings['threshold'],'consecutive_frames':2}}
 try:
  plan=[('hey_bilal','hey Bilal',args.samples),('hee_haa','hee haa',args.samples)]
  for number,phrase in enumerate(['hey Bill','hey Bella','hello Bilal'][:args.other_samples],1):
   plan.append((f'other_{number}',phrase,1))
  for label,phrase,count in plan:
   print(f'\nNext: {count} recordings of {phrase}.',flush=True)
   for number in range(1,count+1):
    input(f'[{number}/{count}] Press Enter when ready to say "{phrase}"...')
    chunks=[]
    overflowed=False
    count=math.ceil(args.seconds*16000/1280)
    with sd.RawInputStream(samplerate=16000,blocksize=1280,dtype='int16',channels=1,
                           device=args.device,latency='low') as stream:
     print(f'SPEAK NOW: {phrase}',flush=True)
     for _ in range(count):
      raw,overflow=stream.read(1280)
      overflowed=overflowed or overflow
      chunks.append(np.frombuffer(raw,dtype=np.int16).copy())
    if overflowed:
     raise RuntimeError('Microphone overflow; repeat calibration after closing other audio apps.')
    audio=np.concatenate(chunks)[:int(args.seconds*16000)]
    filename=f'{label}_{number:02d}.wav'
    wavfile.write(session/filename,16000,audio)
    samples.append({'file':filename,'label':label,'number':number,'prompt':phrase})
    (session/'samples.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Saved.',flush=True)
 except (KeyboardInterrupt,EOFError):
  print('\nStopped. Partial recordings remain local at',session,flush=True)
  return
 analyze_clips(session,model,settings,profile)

if __name__=='__main__':
 main()
