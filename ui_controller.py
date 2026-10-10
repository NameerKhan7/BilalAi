"""Background recording, transcription and agent tasks; UI receives signals only."""
from pathlib import Path
import threading, uuid
from PySide6.QtCore import QObject,Signal
from audio_capture import CaptureConfig,capture_command,save_recording
from stt_client import transcribe_recording,TranscriptionError
from agent_core import AgentBrain,AgentError
from request_router import RequestProcessor,RequestCancelled
from wake_service import WakeMonitor
ROOT=Path(__file__).resolve().parent

class AssistantController(QObject):
    event=Signal(str,object)
    def __init__(self,enable_wake=True):
        super().__init__();self.state='idle';self.closed=False
        self.cancel=threading.Event();self.stop_capture=threading.Event();self.brain=AgentBrain()
        self.processor=RequestProcessor(self.brain,on_progress=lambda text:self.emit('progress',text))
        self.wake_enabled=enable_wake
        self.monitor=WakeMonitor(self.emit) if enable_wake else None
        if self.monitor: self.monitor.resume()
    def emit(self,name,data=None):
        if not self.closed: self.event.emit(name,data)
    def set_wake(self,enabled):
        self.wake_enabled=enabled
        if enabled and self.monitor is None: self.monitor=WakeMonitor(self.emit)
        if self.monitor:
            if enabled and self.state=='idle': self.monitor.resume()
            else: self.monitor.pause()
    def record(self,from_wake=False):
        if self.state!='idle': return
        self.state='recording';self.cancel=threading.Event();self.stop_capture=threading.Event()
        self.emit('preparing',None)
        threading.Thread(target=self._record,args=(from_wake,),daemon=True).start()
    def _record(self,from_wake):
        try:
            if self.monitor: self.monitor.pause()
            config=CaptureConfig(calibration_seconds=0 if from_wake else .30)
            result=capture_command(config,stop_event=self.stop_capture,on_event=self.emit)
            if self.cancel.is_set(): raise RequestCancelled()
            if not result.speech_detected:
                self.emit('empty','I didn’t hear a command. Try again when you’re ready.');return
            path=save_recording(result,ROOT/'recordings'/f'command_{uuid.uuid4().hex[:8]}.wav')
            if result.reason=='max_length': self.emit('limit','Reached the 90-second recording limit.')
            self.state='transcribing';self.emit('transcribing',None)
            text=transcribe_recording(path)
            if self.cancel.is_set(): raise RequestCancelled()
            path.with_suffix('.txt').write_text(text+'\n',encoding='utf-8')
            self.emit('transcript',text);self._agent(text,path)
        except RequestCancelled: self.emit('cancelled',None)
        except (TranscriptionError,AgentError) as exc: self.emit('error',str(exc))
        except Exception: self.emit('error','The request could not finish. Your saved recording is kept locally.')
        finally: self.state='idle';self.emit('finished',None)
    def send(self,text):
        text=text.strip()
        if self.state!='idle' or not text: return
        self.state='thinking';self.cancel=threading.Event()
        self.emit('transcript',text)
        threading.Thread(target=self._typed,args=(text,),daemon=True).start()
    def _typed(self,text):
        try:
            if self.monitor: self.monitor.pause()
            self._agent(text)
        except RequestCancelled: self.emit('cancelled',None)
        except AgentError as exc: self.emit('error',str(exc))
        except Exception: self.emit('error','The agent could not complete this request. Please retry.')
        finally: self.state='idle';self.emit('finished',None)
    def _agent(self,text,path=None):
        self.state='thinking';self.emit('thinking',None)
        result=self.processor.handle(text,self.cancel)
        if self.cancel.is_set(): raise RequestCancelled()
        if path: path.with_suffix('.answer.txt').write_text(f'You: {text}\n\nBilalAI: {result.reply}\n',encoding='utf-8')
        trace=getattr(self.processor,'last_trace',[])
        verified=bool(trace) and all(step['result'].get('ok') is True for step in trace) and any(step['result'].get('verified') is True for step in trace)
        self.emit('reply',{'text':result.reply,'verified':verified})
    def finish_recording(self): self.stop_capture.set()
    def cancel_request(self): self.cancel.set();self.stop_capture.set()
    def resume_wake(self):
        if self.monitor and self.wake_enabled and self.state=='idle': self.monitor.resume()
    def close(self):
        self.closed=True;self.cancel_request()
        if self.monitor: self.monitor.close()
