"""Offline full-phrase verification before wake activation; no cloud requests."""
import re,threading
from concurrent.futures import Future
from pathlib import Path
import numpy as np
MODEL_DIRECTORY=Path(__file__).resolve().parent/'models/wake_asr'
MIN_KEYWORD_LOGPROB=-.60
WAKE_CONTEXT='Hey Bilal.'
WAKE_PHRASE=re.compile(r'\bhey[\s,]+bilal\b[\s,.!?;:]*',re.I)


def verification_audio(audio):
    """Keep short speech context instead of letting long silent pre-roll bias decoding."""
    audio=np.asarray(audio,dtype=np.int16).reshape(-1)
    block=320
    voiced=[offset for offset in range(0,len(audio),block)
        if np.sqrt(np.mean((audio[offset:offset+block].astype(np.float32)/32768.)**2))>=.008]
    if not voiced:return audio
    return audio[max(0,voiced[0]-2560):min(len(audio),voiced[-1]+block+2560)]


def command_after_wake(text):
    # Allow captured pre-roll before the trigger, but require both complete words.
    match=WAKE_PHRASE.search(text[:200])
    return text[match.end():].strip() if match else None


class OfflineWakeVerifier:
    def __init__(self,model=None):self.model=model;self.lock=threading.Lock();self.closed=threading.Event();self.task_lock=threading.Lock();self.active=None
    def start(self):
        if self.closed.is_set():raise RuntimeError('Wake verifier is closed.')
        if self.model is not None:return
        if not all((MODEL_DIRECTORY/name).is_file() for name in ['model.bin','config.json','tokenizer.json','vocabulary.txt']):raise RuntimeError('Install the offline wake verifier with setup_wake_verifier.py.')
        from faster_whisper import WhisperModel
        self.model=WhisperModel(str(MODEL_DIRECTORY),device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,local_files_only=True)
    def check(self,audio):
        with self.lock:
            self.start()
            audio=np.asarray(audio,dtype=np.int16).reshape(-1)
            if not 1600<=len(audio)<=16000*6:return {'accepted':False}
            audio=verification_audio(audio)
            segments,_=self.model.transcribe(audio.astype(np.float32)/32768.,language='en',beam_size=1,best_of=1,
                temperature=0,condition_on_previous_text=False,vad_filter=False,initial_prompt=WAKE_CONTEXT,max_new_tokens=32)
            rows=list(segments)
            accepted=any(command_after_wake(row.text) is not None and row.avg_logprob>=MIN_KEYWORD_LOGPROB and row.no_speech_prob<.6 for row in rows)
            return {'accepted':bool(accepted) and not self.closed.is_set()}
    def begin(self,audio):
        with self.task_lock:
            future=Future()
            if self.active is not None and not self.active.done():
                future.set_result({'accepted':False});return future
            self.active=future
        def work():
            try:future.set_result(self.check(audio))
            except Exception as exc:future.set_exception(exc)
        threading.Thread(target=work,daemon=True).start();return future
    def close(self):self.closed.set()
