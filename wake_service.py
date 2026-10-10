"""Local wake-word monitor. It releases the microphone before command capture."""
import threading, time
import numpy as np

class WakeMonitor:
    def __init__(self,callback):
        self.callback=callback;self.enabled=threading.Event();self.stop=threading.Event()
        self.released=threading.Event();self.released.set()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def resume(self): self.enabled.set()
    def pause(self):
        self.enabled.clear()
        self.released.wait(timeout=.5)
    def close(self): self.enabled.clear();self.stop.set()
    def run(self):
        try:
            import sounddevice as sd
            from wakeword import load_detector,load_settings
            from wakeword_gate import DetectionGate
            model=load_detector();settings=load_settings()
            gate=DetectionGate(settings['threshold'],2,1.5)
            self.callback('wake_ready',None)
            while not self.stop.is_set():
                if not self.enabled.wait(.2): continue
                triggered=False;self.released.clear()
                try:
                    with sd.RawInputStream(samplerate=16000,blocksize=1280,dtype='int16',channels=1,latency='low') as stream:
                        while self.enabled.is_set() and not self.stop.is_set():
                            raw,overflow=stream.read(1280)
                            if overflow: gate.reset();continue
                            score=float(model.predict(np.frombuffer(raw,dtype=np.int16))['hey_bilal'])
                            detected,_=gate.update(score,time.monotonic())
                            if detected:
                                self.enabled.clear();triggered=True;break
                finally: self.released.set()
                model.reset();gate.reset()
                if triggered and not self.stop.is_set(): self.callback('wake',None)
        except Exception:
            self.released.set();self.callback('wake_error','Wake-word listening could not start. You can still use the microphone button.')
