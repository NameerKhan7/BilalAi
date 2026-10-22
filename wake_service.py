"""Wake monitoring: acoustic candidate, offline phrase verification, then capture."""
import threading,time,uuid
from collections import deque
from wake_learning import WakeExamples
from wake_verifier import OfflineWakeVerifier
import numpy as np

class WakeMonitor:
    def __init__(self,callback):
        self.callback=callback;self.enabled=threading.Event();self.stop=threading.Event()
        self.released=threading.Event();self.released.set();self.status='starting'
        self.examples=WakeExamples();self.examples.session=uuid.uuid4().hex;self.last_sample=None
        self.verifier=OfflineWakeVerifier();self.rejected_candidates=0
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def resume(self):self.enabled.set()
    def pause(self):
        self.enabled.clear();self.released.wait(timeout=.5)
    def close(self):
        self.enabled.clear();self.stop.set();self.verifier.close()
    def run(self):
        try:
            import sounddevice as sd
            from wakeword import load_detector,load_settings
            from wakeword_gate import DetectionGate
            model=load_detector();settings=load_settings()
            # This gate only schedules offline verification; it never authorizes activation.
            gate=DetectionGate(settings.get('candidate_threshold',settings['threshold']),settings.get('consecutive_frames',2),settings.get('cooldown_seconds',.6))
            self.verifier.start()
        except Exception:
            self.status='model_error';self.released.set()
            self.callback('wake_error','Offline Hey Bilal verification could not load. Run setup_wake_verifier.py, then restart Bilal. You can still start from the tray.');return
        retry_delay=1.
        while not self.stop.is_set():
            if not self.enabled.wait(.2):continue
            for _ in range(38):model.predict(np.zeros(1280,dtype=np.int16))
            if not self.enabled.is_set() or self.stop.is_set():continue
            self.released.clear()
            try:
                with sd.RawInputStream(samplerate=16000,blocksize=1280,dtype='int16',channels=1,latency='low') as stream:
                    self.status='listening';retry_delay=1.;frames=deque(maxlen=32);candidate=None;next_candidate=0.
                    self.callback('wake_ready',None)
                    while self.enabled.is_set() and not self.stop.is_set():
                        raw,overflow=stream.read(1280)
                        if not self.enabled.is_set() or self.stop.is_set():break
                        if overflow:
                            gate.reset();frames.clear();candidate=None;continue
                        audio=np.frombuffer(raw,dtype=np.int16);frames.append(audio.copy())
                        score=float(model.predict(audio)['hey_bilal']);now=time.monotonic()
                        if candidate is not None:
                            candidate['audio'].append(audio.copy())
                            if len(candidate['audio'])*1280>16000*6:
                                candidate=None;gate.reset();next_candidate=now+1.5
                                self.rejected_candidates+=1;continue
                            if candidate['future'] is None:
                                candidate['lookahead']-=1
                                if candidate['lookahead']<=0:
                                    candidate['wake_audio']=np.concatenate(candidate['audio'])
                                    candidate['future']=self.verifier.begin(candidate['wake_audio'])
                            future=candidate['future']
                            if future is None or not future.done():continue
                            try:accepted=future.result().get('accepted') is True
                            except Exception:
                                self.enabled.clear();self.status='verification_error'
                                self.callback('wake_error','Offline trigger verification failed. Wake activation is paused; restart Bilal or use the tray.');break
                            if not accepted:
                                candidate=None;gate.reset();next_candidate=now+1.5
                                self.rejected_candidates+=1;continue
                            self.enabled.clear()
                            try:self.last_sample=self.examples.record(candidate['wake_audio'],candidate['score'])
                            except OSError:self.last_sample=None
                            self.callback('wake',{'phrase_verified':True,'sample_id':self.last_sample,'stream':stream,'leading_audio':np.concatenate(candidate['audio'])})
                            break
                        detected,confirmed=gate.update(score,now)
                        if detected and now>=next_candidate:
                            candidate={'audio':list(frames),'score':confirmed,'lookahead':3,'future':None}
                if self.status!='verification_error':self.status='paused'
            except Exception:
                self.status='waiting_microphone'
                self.callback('wake_retry','Waiting for the microphone; wake listening will retry automatically.')
            finally:self.released.set()
            model.reset();gate.reset()
            if self.status=='waiting_microphone':
                self.stop.wait(retry_delay);retry_delay=min(10.,retry_delay*2)
        self.verifier.close();self.status='stopped';self.released.set()
