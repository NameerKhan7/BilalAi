"""Background recording, transcription and agent tasks; UI receives signals only."""
from pathlib import Path
import threading, uuid,subprocess
from runtime_paths import worker_python
from PySide6.QtCore import QObject,Signal
from audio_capture import CaptureConfig,capture_command,save_recording
from stt_client import transcribe_recording,TranscriptionError
from agent_core import AgentBrain,AgentError
from request_router import RequestProcessor,RequestCancelled
from wake_service import WakeMonitor
from voice_cancel import CancelListener,is_cancel_request,strip_wake_prefix
from wake_verifier import command_after_wake
from memory import LocalState
from business_tools import BusinessWorkflows
from conversation import FOLLOWUP_WAIT_SECONDS,is_conversation_end
ROOT=Path(__file__).resolve().parent

class AssistantController(QObject):
    event=Signal(str,object)
    def __init__(self,enable_wake=True,enable_cancel=None,state=None,enable_tasks=False,transcriber=None):
        if enable_tasks:
            from wake_acceptance import accepted
            enable_wake=enable_wake and accepted()
        super().__init__();self.state='idle';self.closed=False
        self.cancel=threading.Event();self.stop_capture=threading.Event();self.state_store=state or LocalState(recover_inflight=enable_wake)
        self.brain=AgentBrain(state=self.state_store);self.business=BusinessWorkflows(self.state_store)
        from provider_interfaces import GroqTranscriber
        self.transcriber=transcriber or GroqTranscriber()
        self.runtime=None
        if enable_tasks:
            from task_runtime import TaskRuntime
            self.runtime=TaskRuntime(self.state_store,self.emit)
            self.brain.persistent=self.runtime.store
            self.brain.history=self.runtime.store.history()
        self.reviewed_action=None;self.learning_process=None;self.pending_input=None
        self.conversation_active=False;self.hold_event=threading.Event();self.capture_mode='manual'
        self.cancel_listener=CancelListener(self.cancel_request) if (enable_wake if enable_cancel is None else enable_cancel) else None
        self.processor=RequestProcessor(self.brain,on_progress=lambda text:self.emit('progress',text))
        self.wake_enabled=enable_wake
        self.monitor=WakeMonitor(self.wake_event) if enable_wake else None
        if self.monitor: self.monitor.resume()
    def wake_event(self,name,data):
        if name!='wake':self.emit(name,data);return
        if self.closed or not self.wake_enabled or self.state!='idle' or self.input_blocks_wake() or self.conversation_active:return
        if not isinstance(data,dict) or data.get('phrase_verified') is not True:return
        self.state='recording';self.cancel=threading.Event();self.stop_capture=threading.Event()
        self.emit('wake_activated',{'sample_id':data.get('sample_id')})
        try:
            self.capture_mode='clarification' if self.pending_input else 'wake'
            result=capture_command(CaptureConfig(calibration_seconds=0),stop_event=self.stop_capture,
                on_event=self.emit,stream=data['stream'],leading_audio=data.get('leading_audio'),hold_event=self.hold_event)
            threading.Thread(target=self._captured,args=(result,True),daemon=True).start()
        except Exception:
            self.state='idle';self.emit('error','Wake capture failed. Try starting from the tray.');self.emit('finished',None)
    def _captured(self,result,require_wake=False):
        try:
            if self.monitor:self.monitor.pause()
            self._process_capture(result,require_wake=require_wake,mode=self.capture_mode)
        except RequestCancelled:self.emit('cancelled',None)
        except (TranscriptionError,AgentError) as exc:self.emit('cancelled' if self.cancel.is_set() else 'error',None if self.cancel.is_set() else str(exc))
        except Exception:self.emit('error','The voice request could not finish.')
        finally:
            if self.cancel_listener:self.cancel_listener.stop()
            self.state='idle';self.emit('finished',None)
    def emit(self,name,data=None):
        if not self.closed: self.event.emit(name,data)
    def set_wake(self,enabled):
        if enabled and self.runtime:
            from wake_acceptance import accepted
            if not accepted():
                self.emit('wake_error','Wake activation needs a fresh 50-trial and one-hour negative acceptance test. Use hold-to-talk meanwhile.');return
        self.wake_enabled=enabled
        if enabled and self.monitor is None: self.monitor=WakeMonitor(self.wake_event)
        if self.monitor:
            if enabled and self.state=='idle' and not self.input_blocks_wake() and not self.conversation_active: self.monitor.resume()
            else: self.monitor.pause()
    def record(self,from_wake=False,mode='manual'):
        if self.state!='idle':return
        if self.pending_input:
            if self.pending_input.get('field')=='email':return
            mode='clarification'
        self.state='recording';self.cancel=threading.Event();self.stop_capture=threading.Event()
        self.capture_mode=mode
        self.emit('preparing',None)
        threading.Thread(target=self._record,args=(from_wake,mode),daemon=True).start()
    def _record(self,from_wake,mode='manual'):
        try:
            if self.monitor: self.monitor.pause()
            config=CaptureConfig(calibration_seconds=0 if from_wake or mode in {'hold','followup','clarification'} else .30,
                initial_wait_seconds=FOLLOWUP_WAIT_SECONDS if mode=='followup' else 10.,max_seconds=600. if mode in {'hold','followup','clarification'} else 90.)
            result=capture_command(config,stop_event=self.stop_capture,on_event=self.emit,hold_event=self.hold_event)
            self._process_capture(result,require_wake=from_wake,mode=mode)
        except RequestCancelled: self.emit('cancelled',None)
        except (TranscriptionError,AgentError) as exc:self.emit('cancelled' if self.cancel.is_set() else 'error',None if self.cancel.is_set() else str(exc))
        except Exception: self.emit('error','The request could not finish. Your saved recording is kept locally.')
        finally:
            if self.cancel_listener:self.cancel_listener.stop()
            self.state='idle';self.emit('finished',None)
    def _process_capture(self,result,require_wake=False,mode='manual'):
        if self.cancel.is_set(): raise RequestCancelled()
        if not result.speech_detected:
            if mode=='followup' and result.reason=='no_speech':self.emit('conversation_timeout',None);return
            if mode in {'hold','followup','clarification'}:self.emit('conversation_wait',None);return
            self.emit('empty','I didn’t hear a command. Try again when you’re ready.');return
        path=save_recording(result,ROOT/'recordings'/f'command_{uuid.uuid4().hex[:8]}.wav')
        if result.reason=='max_length': self.emit('limit','Reached the recording limit. Processing this part now.')
        self.state='transcribing';self.emit('transcribing',None)
        if self.cancel_listener:self.cancel_listener.start()
        text=self.transcriber.transcribe(path) if self.runtime else transcribe_recording(path)
        if self.cancel.is_set(): raise RequestCancelled()
        path.with_suffix('.txt').write_text(text+'\n',encoding='utf-8')
        if require_wake:
            command=command_after_wake(text)
            if command is None:
                self.emit('wake_rejected',None);return
            text=command
        self.emit('transcript',text)
        if mode=='clarification' and self.pending_input:
            if is_cancel_request(strip_wake_prefix(text)) or is_conversation_end(strip_wake_prefix(text)):
                self.cancel_request();self.emit('cancelled',None);return
            text=self.clarification_request(text)
        self._agent(text,path)
    def send(self,text):
        text=text.strip()
        if self.state!='idle' or self.pending_input or not text: return
        self.state='thinking';self.cancel=threading.Event()
        self.emit('transcript',text)
        threading.Thread(target=self._typed,args=(text,),daemon=True).start()
    def _typed(self,text):
        try:
            if self.monitor: self.monitor.pause()
            self._agent(text)
        except RequestCancelled: self.emit('cancelled',None)
        except AgentError as exc:self.emit('cancelled' if self.cancel.is_set() else 'error',None if self.cancel.is_set() else str(exc))
        except Exception: self.emit('error','The agent could not complete this request. Please retry.')
        finally:
            if self.cancel_listener:self.cancel_listener.stop()
            self.state='idle';self.emit('finished',None)
    def _agent(self,text,path=None):
        text=strip_wake_prefix(text)
        if not text:
            self.emit('reply',{'text':"I'm here. What are we working on?",'verified':False});return
        if is_conversation_end(text):
            self.emit('conversation_ended',None)
            self.emit('reply',{'text':"All right. I'll be here when you need me.",'verified':False});return
        if is_cancel_request(text):
            if self.runtime:
                try:self.runtime.engine.cancel('last')
                except ValueError:pass
            self.cancel_request();self.emit('cancelled',None);return
        if self.runtime:
            result=self.runtime.submit(text,getattr(self,'literal_vault',None))
            self.emit('reply',{'text':result['reply'],'verified':True,'queued':bool(result.get('task_id'))})
            return
        if self.cancel_listener:self.cancel_listener.start()
        self.state='thinking';self.emit('thinking',None)
        result=self.processor.handle(text,self.cancel)
        if self.cancel.is_set(): raise RequestCancelled()
        if path: path.with_suffix('.answer.txt').write_text(f'You: {text}\n\nBilalAI: {result.reply}\n',encoding='utf-8')
        trace=getattr(self.processor,'last_trace',[])
        detail=next((step['result'].get('input_request') for step in trace if step['result'].get('input_request')),None)
        if detail:
            self.pending_input=dict(detail)
            self.emit('reply',{'text':detail['question'],'verified':False})
            self.emit('input_needed',self.pending_input);return
        verified=bool(trace) and all(step['result'].get('ok') is True for step in trace) and any(step['result'].get('verified') is True for step in trace)
        self.emit('reply',{'text':result.reply,'verified':verified})
        for step in trace:
            action_id=step['result'].get('approval_id')
            if action_id:
                pending=self.state_store.get(action_id)
                if pending['status']=='pending':self.emit('approval',pending);break
    def submit_input(self,value):
        if self.closed or self.state!='idle' or not self.pending_input:return False
        self.send(self.clarification_request(value))
        return True
    def clarification_request(self,value):
        from contextual_input import validate_detail
        value=validate_detail(self.pending_input['field'],value)
        detail=dict(self.pending_input);question=detail['question'];self.pending_input=None
        if self.runtime:
            from literal_slots import LiteralVault
            self.literal_vault=LiteralVault();value=self.literal_vault.add(value,'Answer to '+question)
            if detail.get('task_id'):
                self.runtime.store.set_state(detail['task_id'],'cancelled',error='Continued as a new clarification task.')
        return 'Original goal: '+detail.get('original_goal','See recent conversation.')+'\nAnswer to your clarification '+repr(question)+': '+value+'\nDo not repeat completed writes. This answer is not sending approval.'
    def collect_wake_examples(self):
        if self.state!='idle' or self.pending_input:return
        self.state='learning';self.cancel=threading.Event()
        self.emit('thinking',None)
        def work():
            try:
                if self.monitor:self.monitor.pause()
                if self.cancel.is_set():return
                self.learning_process=subprocess.Popen([worker_python(),str(ROOT/'collect_wake_examples.py'),'--label','both','--count','10'],cwd=ROOT,
                    creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
                if self.cancel.is_set():self.learning_process.kill()
                self.learning_process.wait()
                if self.cancel.is_set():self.emit('cancelled',None);return
                self.emit('reply',{'text':'Wake collection finished. Reviewed examples remain local; the model has not been changed.','verified':False})
            finally:self.learning_process=None;self.state='idle';self.emit('finished',None)
        threading.Thread(target=work,daemon=True).start()
    def finish_recording(self): self.stop_capture.set()
    def cancel_request(self,reject_approval=True):
        self.cancel.set();self.stop_capture.set();self.emit('cancelling',None)
        if self.pending_input:
            self.pending_input=None;self.emit('input_cancelled',None)
            self.brain.remember('Cancel the pending task.','Cancelled; do not continue it.')
        if self.learning_process is not None and self.learning_process.poll() is None:self.learning_process.kill()
        if reject_approval and self.reviewed_action:
            try:self.business.resolve(*self.reviewed_action,approve=False)
            except ValueError:pass
            self.reviewed_action=None;self.emit('approval_cancelled',None)
    def resolve_approval(self,action_id,fingerprint,approve):
        if self.state!='idle':return
        self.state='approval';self.cancel=threading.Event();self.reviewed_action=None;self.emit('thinking',None)
        def work():
            try:
                if self.monitor:self.monitor.pause()
                if self.cancel_listener:self.cancel_listener.start()
                if self.runtime:self.runtime.policy.trusted_business_decision(self.state_store.get(action_id),approve)
                result=self.business.resolve(action_id,fingerprint,approve,self.cancel)
                if self.runtime:
                    self.runtime.store.audit('business.result',{'approval_id':action_id,'result':result})
                    for task in self.runtime.store.tasks(['waiting_approval']):
                        if (task.get('result') or {}).get('approval_id')==action_id:
                            if result.get('approval_id'):
                                self.runtime.store.set_state(task['id'],'waiting_approval',result=result)
                            else:self.runtime.store.set_state(task['id'],'done' if result.get('verified') else 'cancelled' if not approve else 'failed',result=result)
                self.emit('reply',{'text':result.get('reply','Action processed.'),'verified':result.get('verified',False)})
                if result.get('approval_id'):self.emit('approval',self.state_store.get(result['approval_id']))
            except Exception as exc:self.emit('error',str(exc))
            finally:
                if self.cancel_listener:self.cancel_listener.stop()
                self.state='idle';self.emit('finished',None)
        threading.Thread(target=work,daemon=True).start()
    def resume_wake(self):
        if not self.closed and self.monitor and self.wake_enabled and self.state=='idle' and not self.input_blocks_wake() and not self.conversation_active: self.monitor.resume()
    def input_blocks_wake(self):return bool(self.pending_input and self.pending_input.get('field')=='email')
    def close(self):
        self.closed=True;self.cancel_request(reject_approval=False)
        if self.runtime:self.runtime.close()
        if self.cancel_listener:self.cancel_listener.stop()
        if self.monitor: self.monitor.close()
