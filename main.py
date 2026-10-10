"""BilalAI: local recording, Groq transcription and explicit Gemini answers."""
from pathlib import Path
import queue
import threading
import uuid
import time
import tkinter as tk
from tkinter import ttk
import winsound
from audio_capture import capture_command,save_recording
from stt_client import transcribe_recording,TranscriptionError
from agent_core import AgentBrain,AgentError
from request_router import RequestProcessor,RequestCancelled
from app_tools import AppLaunchError
from browser_tools import BrowserActionError
ROOT=Path(__file__).resolve().parent

class RecorderApp:
    def __init__(self,root):
        self.root=root
        self.events=queue.Queue()
        self.brain=AgentBrain()
        self.processor=RequestProcessor(self.brain,on_progress=lambda text:self.events.put(('agent_progress',text)))
        self.request_cancel=threading.Event()
        self.state='idle'
        self.stop_event=threading.Event()
        self.last_path=None
        self.closing=False
        self.space_down=False
        root.title('BilalAI - Voice Assistant')
        root.geometry('780x650')
        root.minsize(720,620)
        root.configure(bg='#111827')
        root.protocol('WM_DELETE_WINDOW',self.close)
        panel=tk.Frame(root,bg='#111827',padx=28,pady=24)
        panel.pack(fill='both',expand=True)
        tk.Label(panel,text='BILALAI',font=('Segoe UI',11,'bold'),fg='#72e4bf',bg='#111827').pack(anchor='w')
        tk.Label(panel,text='Talk to Bilal',font=('Segoe UI',23,'bold'),fg='#f9fafb',bg='#111827').pack(anchor='w',pady=(4,10))
        tk.Label(panel,text='Press Record and speak. Bilal handles the rest.\nQuestions get answers. App commands open the installed app.',
                 font=('Segoe UI',11),justify='left',fg='#cbd5e1',bg='#111827').pack(anchor='w')
        self.status=tk.StringVar(value='Ready to record or type a question')
        tk.Label(panel,textvariable=self.status,font=('Segoe UI',13,'bold'),fg='#f9fafb',bg='#111827',wraplength=700,justify='left').pack(anchor='w',pady=(18,10))
        self.level=ttk.Progressbar(panel,maximum=100,mode='determinate')
        self.level.pack(fill='x',pady=(0,16))
        row=tk.Frame(panel,bg='#111827')
        row.pack(fill='x')
        def button(label,callback,bg,bold=False):
            widget=tk.Button(row,text=label,command=callback,font=('Segoe UI',11,'bold' if bold else 'normal'),
                             bg=bg,fg='#111827' if bg=='#72e4bf' else 'white',activebackground=bg,
                             relief='flat',padx=16,pady=12,takefocus=False)
            widget.pack(side='left',padx=(0,10))
            return widget
        self.record_button=button('Record command',self.toggle_record,'#72e4bf',True)
        self.play_button=button('Play recording',self.play,'#334155')
        self.transcribe_button=button('Transcribe',self.transcribe,'#3b82f6',True)
        self.play_button.pack_forget()
        self.transcribe_button.pack_forget()
        self.ask_button=button('Send typed text',self.ask,'#8b5cf6',True)
        self.detail=tk.StringVar(value='Try: What is the difference between a website and a web app?')
        tk.Label(panel,textvariable=self.detail,font=('Segoe UI',10),fg='#cbd5e1',bg='#111827',justify='left',wraplength=700).pack(anchor='w',pady=(14,0))
        panes=tk.Frame(panel,bg='#111827')
        panes.pack(fill='both',expand=True,pady=(16,0))
        panes.columnconfigure(0,weight=1)
        panes.columnconfigure(1,weight=1)
        panes.rowconfigure(0,weight=1)
        def text_pane(column,label,editable):
            frame=tk.Frame(panes,bg='#111827')
            frame.grid(row=0,column=column,sticky='nsew',padx=(0,12) if column==0 else (0,0))
            tk.Label(frame,text=label,font=('Segoe UI',11,'bold'),fg='#f9fafb',bg='#111827').pack(anchor='w',pady=(0,6))
            widget=tk.Text(frame,height=7,width=1,font=('Segoe UI',11),wrap='word',bg='#1f2937',fg='#f9fafb',
                           insertbackground='white',relief='flat',padx=10,pady=10,state='normal' if editable else 'disabled')
            widget.pack(fill='both',expand=True)
            return widget
        self.transcript_box=text_pane(0,'Transcript - editable',True)
        self.answer_box=text_pane(1,'BilalAI reply',False)
        bottom=tk.Frame(panel,bg='#111827')
        bottom.pack(fill='x',pady=(12,0))
        self.clear_button=tk.Button(bottom,text='Clear chat',command=self.clear_chat,font=('Segoe UI',10),
                                    bg='#334155',fg='white',relief='flat',padx=12,pady=6,takefocus=False)
        self.clear_button.pack(side='right')
        tk.Label(bottom,text='Speech goes to Groq. Gemini reasons over your request and relevant app controls.\nActions run locally. Private task logs stay on this PC. Escape stops pending steps.',
                 font=('Segoe UI',9),fg='#94a3b8',bg='#111827',wraplength=560,justify='left').pack(side='left',anchor='w')
        for widget in (root,self.record_button,self.play_button,self.transcribe_button,self.ask_button,self.clear_button,self.answer_box):
            widget.bind('<KeyPress-space>',self.press_space)
            widget.bind('<KeyRelease-space>',self.release_space)
            widget.bind('<Escape>',self.escape)
        self.transcript_box.bind('<KeyPress-space>',self.edit_space)
        self.transcript_box.bind('<<Modified>>',self.text_changed)
        self.transcript_box.bind('<Escape>',self.escape)
        self.refresh_controls()
        root.after(50,self.poll_events)

    def query_text(self):
        return self.transcript_box.get('1.0','end-1c').strip()

    def text_changed(self,event=None):
        if self.transcript_box.edit_modified():
            self.transcript_box.edit_modified(False)
            self.ask_button.config(state='normal' if self.state=='idle' and self.query_text() else 'disabled')

    def edit_space(self,event=None):
        if self.state=='idle':
            try: self.transcript_box.delete('sel.first','sel.last')
            except tk.TclError: pass
            self.transcript_box.insert('insert',' ')
        return 'break'

    def press_space(self,event=None):
        if not self.space_down:
            self.space_down=True
            self.toggle_record()
        return 'break'

    def release_space(self,event=None):
        self.space_down=False
        return 'break'

    def escape(self,event=None):
        if self.state in ('preparing','listening'):
            self.request_cancel.set();self.toggle_record()
        elif self.state in ('transcribing','thinking'):
            self.request_cancel.set();self.status.set('Cancelling request...')
        elif self.state=='playing': winsound.PlaySound(None,0)
        return 'break'

    def refresh_controls(self):
        idle=self.state=='idle'
        self.record_button.config(text='Stop recording' if self.state in ('preparing','listening') else 'Record command',
                                  state='normal' if idle or self.state in ('preparing','listening') else 'disabled')
        self.play_button.config(state='normal' if idle and self.last_path else 'disabled')
        self.transcribe_button.config(state='normal' if idle and self.last_path else 'disabled')
        self.ask_button.config(state='normal' if idle and self.query_text() else 'disabled')
        self.clear_button.config(state='normal' if idle and self.brain.history else 'disabled')
        self.transcript_box.config(state='normal' if idle else 'disabled')
        if self.state in ('transcribing','thinking'):
            self.level.config(mode='indeterminate');self.level.start(50)
        else:
            self.level.stop();self.level.config(mode='determinate')
            if idle: self.level['value']=0

    def set_text(self,widget,text,editable=False):
        widget.config(state='normal')
        widget.delete('1.0','end');widget.insert('1.0',text)
        if widget is self.transcript_box: widget.edit_modified(False)
        widget.config(state='normal' if editable and self.state=='idle' else 'disabled')

    def set_idle(self):
        self.state='idle'
        self.refresh_controls()

    def toggle_record(self):
        if self.state in ('preparing','listening'):
            self.stop_event.set();self.state='stopping'
            self.status.set('Finishing recording...');self.refresh_controls()
            return
        if self.state!='idle': return
        self.state='preparing';self.last_path=None
        self.request_cancel=threading.Event()
        self.stop_event=threading.Event()
        self.set_text(self.transcript_box,'');self.set_text(self.answer_box,'')
        self.status.set('Checking microphone - please wait...')
        self.level['value']=0;self.refresh_controls()
        threading.Thread(target=self.record_worker,daemon=True).start()

    def record_worker(self):
        try:
            result=capture_command(stop_event=self.stop_event,on_event=lambda name,data:self.events.put((name,data)))
            path=save_recording(result,ROOT/'recordings'/f'command_{uuid.uuid4().hex[:8]}.wav') if result.speech_detected and not self.closing else None
            self.events.put(('finished',(result,path)))
        except Exception as exc: self.events.put(('error',str(exc)))

    def play(self):
        if self.state!='idle' or self.last_path is None: return
        self.state='playing';self.status.set('Playing your recording...');self.refresh_controls()
        threading.Thread(target=self.play_worker,daemon=True).start()

    def play_worker(self):
        try:
            winsound.PlaySound(str(self.last_path),winsound.SND_FILENAME)
            self.events.put(('play_finished',None))
        except Exception as exc: self.events.put(('error','Playback failed: '+str(exc)))

    def transcribe(self):
        if self.state!='idle' or self.last_path is None: return
        self.state='transcribing';self.status.set('Transcribing with Groq...')
        self.detail.set('Sending the selected audio clip to Groq.')
        self.set_text(self.answer_box,'');self.refresh_controls()
        threading.Thread(target=self.transcribe_worker,args=(self.last_path,),daemon=True).start()

    def transcribe_worker(self,path):
        start=time.perf_counter()
        try:
            text=transcribe_recording(path)
            if self.request_cancel.is_set():
                self.events.put(('cancelled',None));return
            if not self.closing:
                output=path.with_suffix('.txt');output.write_text(text+'\n',encoding='utf-8')
                self.events.put(('transcribed',(text,time.perf_counter()-start,output.name)))
        except TranscriptionError as exc: self.events.put(('transcription_error',str(exc)))
        except Exception: self.events.put(('transcription_error','Could not complete transcription. Please retry.'))

    def ask(self,auto=False):
        if self.state!='idle' or not self.query_text(): return
        query=self.query_text()
        if not auto: self.request_cancel=threading.Event()
        if self.request_cancel.is_set(): return
        self.state='thinking';self.status.set('Handling your request...')
        self.detail.set('Bilal is choosing tools, observing the app and checking the result.')
        self.set_text(self.answer_box,'');self.refresh_controls()
        threading.Thread(target=self.ask_worker,args=(query,self.last_path),daemon=True).start()

    def ask_worker(self,query,path):
        start=time.perf_counter()
        try:
            result=self.processor.handle(query,self.request_cancel)
            reply=result.reply
            saved_name=None
            if path and not self.closing:
                try:
                    output=path.with_suffix('.answer.txt')
                    output.write_text(f'You: {query}\n\nBilalAI: {reply}\n',encoding='utf-8');saved_name=output.name
                except OSError: pass
            self.events.put(('answered',(reply,time.perf_counter()-start,saved_name,result.kind)))
        except RequestCancelled: self.events.put(('cancelled',None))
        except (AgentError,AppLaunchError,BrowserActionError) as exc: self.events.put(('answer_error',str(exc)))
        except Exception: self.events.put(('answer_error','Could not complete the answer. Please retry.'))

    def clear_chat(self):
        if self.state!='idle': return
        self.brain.clear();self.set_text(self.answer_box,'')
        self.status.set('Conversation cleared');self.detail.set('The next question starts a fresh conversation.')
        self.refresh_controls()

    def poll_events(self):
        if self.closing: return
        try:
            while True:
                name,data=self.events.get_nowait()
                if name=='agent_progress':
                    self.detail.set(data)
                elif name=='ready' and not self.stop_event.is_set():
                    self.state='listening';self.status.set('Speak now');self.refresh_controls()
                elif name=='level':
                    self.level['value']=min(100,data['rms']*700)
                    if self.state=='listening' and data['speech_detected']: self.status.set('Listening - finish your command')
                elif name=='finished':
                    result,path=data
                    self.last_path=path;self.set_idle()
                    if path:
                        self.status.set('Saved - play back or transcribe' if result.reason!='max_length' else 'Reached 15 seconds - play it back')
                        self.detail.set(f'{result.duration_seconds:.1f}s saved in recordings/{path.name}')
                        if self.request_cancel.is_set(): self.status.set('Request cancelled')
                        else: self.transcribe()
                    else: self.status.set('No command heard - try again' if result.reason=='no_speech' else 'Recording cancelled')
                elif name=='play_finished':
                    self.set_idle();self.status.set('Ready to record or ask again')
                elif name=='transcribed':
                    text,duration,filename=data
                    self.state='idle';self.set_text(self.transcript_box,text,True);self.refresh_controls()
                    self.detail.set(f'Transcribed in {duration:.1f}s. Saved in recordings/{filename}')
                    if self.request_cancel.is_set(): self.status.set('Request cancelled')
                    else: self.ask(auto=True)
                elif name=='answered':
                    reply,duration,filename,kind=data
                    self.set_idle();self.set_text(self.answer_box,reply)
                    self.status.set('App command completed' if kind=='app' else 'Browser command completed' if kind=='browser' else 'Command not supported yet' if kind=='unsupported' else 'Bilal replied')
                    self.detail.set(f'Handled in {duration:.1f}s.'+(f' Saved in recordings/{filename}' if filename else ''))
                elif name=='cancelled':
                    self.set_idle();self.status.set('Request cancelled')
                elif name in ('transcription_error','answer_error','error'):
                    self.set_idle()
                    self.status.set('Transcription failed' if name=='transcription_error' else 'Answer failed' if name=='answer_error' else 'Could not complete recording or playback')
                    self.detail.set(data)
        except queue.Empty: pass
        self.root.after(50,self.poll_events)

    def close(self):
        self.closing=True;self.stop_event.set();self.request_cancel.set()
        winsound.PlaySound(None,0);self.root.destroy()


def main():
    root=tk.Tk();RecorderApp(root);root.mainloop()

if __name__=='__main__': main()
