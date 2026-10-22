"""Local command recording with pre-roll and silence-based stopping."""
from dataclasses import dataclass
import io
import threading
import wave
from pathlib import Path
import numpy as np

@dataclass(frozen=True)
class CaptureConfig:
    sample_rate: int = 16000
    block_ms: int = 20
    calibration_seconds: float = .30
    pre_roll_seconds: float = .25
    tail_seconds: float = .25
    silence_seconds: float = 4.0
    initial_wait_seconds: float = 10.0
    max_seconds: float = 90.0
    min_speech_rms: float = .008
    noise_multiplier: float = 3.0
    onset_frames: int = 3

    def __post_init__(self):
        if self.sample_rate <= 0 or self.block_ms <= 0 or self.onset_frames < 1:
            raise ValueError('Invalid audio format or onset settings.')
        if not 0 < self.initial_wait_seconds <= self.max_seconds:
            raise ValueError('Initial wait must be positive and within maximum duration.')
        if self.silence_seconds <= 0 or self.min_speech_rms <= 0:
            raise ValueError('Silence interval and speech level must be positive.')
        if min(self.calibration_seconds, self.pre_roll_seconds, self.tail_seconds) < 0:
            raise ValueError('Audio context intervals cannot be negative.')

    @property
    def block_samples(self):
        return max(1, round(self.sample_rate*self.block_ms/1000))

@dataclass
class CaptureResult:
    audio: np.ndarray
    sample_rate: int
    reason: str
    speech_detected: bool
    threshold: float

    @property
    def duration_seconds(self):
        return len(self.audio)/self.sample_rate

class CommandEndpoint:
    """The same endpoint detector can consume microphone audio or saved test frames."""
    def __init__(self, config=CaptureConfig(), noise_rms=0.0):
        self.config=config
        self.threshold=max(config.min_speech_rms, noise_rms*config.noise_multiplier)
        self.chunks=[]
        self.total_samples=0
        self.start_index=None
        self.last_speech_end=0
        self.onset_count=0
        self.reason=None
        self.rms=0.0

    def feed(self, frame, held=False):
        if self.reason is not None:
            raise RuntimeError('Capture already ended.')
        frame=np.asarray(frame,dtype=np.int16).reshape(-1).copy()
        remaining=round(self.config.max_seconds*self.config.sample_rate)-self.total_samples
        frame=frame[:remaining]
        self.chunks.append(frame)
        self.total_samples+=len(frame)
        self.rms=float(np.sqrt(np.mean((frame.astype(np.float32)/32768)**2))) if len(frame) else 0
        if self.start_index is None:
            self.onset_count=self.onset_count+1 if self.rms>=self.threshold else 0
            if self.onset_count>=self.config.onset_frames:
                onset_start=self.total_samples-self.onset_count*self.config.block_samples
                self.start_index=max(0,onset_start-round(self.config.pre_roll_seconds*self.config.sample_rate))
                self.last_speech_end=self.total_samples
        elif self.rms>=self.threshold*.60:
            self.last_speech_end=self.total_samples
        if not held and self.start_index is not None and self.total_samples-self.last_speech_end>=round(self.config.silence_seconds*self.config.sample_rate):
            self.reason='silence'
        elif not held and self.start_index is None and self.total_samples>=round(self.config.initial_wait_seconds*self.config.sample_rate):
            self.reason='no_speech'
        elif self.total_samples>=round(self.config.max_seconds*self.config.sample_rate):
            self.reason='max_length'
        return self.reason

    def finish(self, reason=None):
        reason=reason or self.reason or 'manual'
        if self.start_index is None:
            return CaptureResult(np.empty(0,dtype=np.int16),self.config.sample_rate,
                                 'cancelled' if reason=='manual' else reason,False,self.threshold)
        audio=np.concatenate(self.chunks)
        end=min(len(audio),self.last_speech_end+round(self.config.tail_seconds*self.config.sample_rate))
        return CaptureResult(audio[self.start_index:end].copy(),self.config.sample_rate,reason,True,self.threshold)


def capture_command(config=CaptureConfig(),device=None,stop_event=None,on_event=None,stream=None,leading_audio=None,hold_event=None):
    """Capture manually or reuse the already-open wake stream without a microphone gap."""
    stop_event=stop_event or threading.Event()
    on_event=on_event or (lambda name,data:None)
    on_event('preparing',None)
    if stream is not None:
        return _capture_stream(stream,config,stop_event,on_event,leading_audio,hold_event)
    import sounddevice as sd
    with sd.RawInputStream(samplerate=config.sample_rate,blocksize=config.block_samples,
                          dtype='int16',channels=1,device=device,latency='low') as opened:
        return _capture_stream(opened,config,stop_event,on_event,leading_audio,hold_event)

def _capture_stream(stream,config,stop_event,on_event,leading_audio=None,hold_event=None):
    noise=[]
    blocks=round(config.calibration_seconds*config.sample_rate/config.block_samples)
    for _ in range(blocks):
        if stop_event.is_set():
            return CommandEndpoint(config).finish('manual')
        raw,overflow=stream.read(config.block_samples)
        if overflow: raise RuntimeError('Microphone overflow. Close other audio apps and retry.')
        x=np.frombuffer(raw,dtype=np.int16).astype(np.float32)/32768
        noise.append(float(np.sqrt(np.mean(x*x))))
    endpoint=CommandEndpoint(config,float(np.median(noise)) if noise else 0)
    if leading_audio is not None:
        samples=np.asarray(leading_audio,dtype=np.int16)
        for offset in range(0,len(samples),config.block_samples):
            if endpoint.feed(samples[offset:offset+config.block_samples],held=bool(hold_event and hold_event.is_set())) is not None:break
    if stop_event.is_set(): return endpoint.finish('manual')
    if endpoint.reason is not None:return endpoint.finish()
    on_event('ready',{'latency_ms':stream.latency*1000,'threshold':endpoint.threshold})
    frame_count=0
    while not stop_event.is_set():
        raw,overflow=stream.read(config.block_samples)
        if overflow: raise RuntimeError('Microphone overflow. Close other audio apps and retry.')
        reason=endpoint.feed(np.frombuffer(raw,dtype=np.int16),held=bool(hold_event and hold_event.is_set()))
        frame_count+=1
        if frame_count%5==0:
            on_event('level',{'rms':endpoint.rms,'speech_detected':endpoint.start_index is not None,'silence_seconds':max(0,(endpoint.total_samples-endpoint.last_speech_end)/config.sample_rate) if endpoint.start_index is not None else 0})
        if reason is not None: return endpoint.finish()
    return endpoint.finish('manual')


def encode_wav(audio, sample_rate=16000):
    audio=np.asarray(audio,dtype=np.int16).reshape(-1)
    if len(audio)==0: raise ValueError('Cannot save an empty recording.')
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(audio.astype('<i2',copy=False).tobytes())
    return buffer.getvalue()


def save_recording(result, path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(encode_wav(result.audio,result.sample_rate))
    return path
