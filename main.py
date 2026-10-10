"""BilalAI voice-to-text test: local recording and explicit cloud transcription."""
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
ROOT=Path(__file__).resolve().parent

class RecorderApp:
    def __init__(self, root):
        self.root=root
        self.events=queue.Queue()
        self.state='idle'
        self.stop_event=threading.Event()
        self.last_path=None
        self.closing=False
        self.space_down=False
        root.title('BilalAI - Voice to Text')
        root.geometry('650x640')
        root.minsize(620,620)
        root.configure(bg='#111827')
        root.protocol('WM_DELETE_WINDOW',self.close)
        panel=tk.Frame(root,bg='#111827',padx=28,pady=24)
        panel.pack(fill='both',expand=True)
        tk.Label(panel,text='BILALAI',font=('Segoe UI',11,'bold'),fg='#72e4bf',bg='#111827').pack(anchor='w')
        tk.Label(panel,text='Voice to text',font=('Segoe UI',23,'bold'),fg='#f9fafb',bg='#111827').pack(anchor='w',pady=(4,10))
        tk.Label(panel,text='Press Space or click Record. Wait for Speak now.\nRecording stops after one second of silence.',
                 font=('Segoe UI',11),justify='left',fg='#cbd5e1',bg='#111827').pack(anchor='w')
        self.status=tk.StringVar(value='Ready to record')
        tk.Label(panel,textvariable=self.status,font=('Segoe UI',13,'bold'),fg='#f9fafb',bg='#111827',wraplength=510,justify='left').pack(anchor='w',pady=(22,12))
        self.level=ttk.Progressbar(panel,maximum=100,mode='determinate')
        self.level.pack(fill='x',pady=(0,18))
        row=tk.Frame(panel,bg='#111827')
        row.pack(fill='x')
        self.record_button=tk.Button(row,text='Record command',command=self.toggle_record,font=('Segoe UI',12,'bold'),
                                     bg='#72e4bf',fg='#111827',activebackground='#a7f3d0',relief='flat',padx=18,pady=12,takefocus=False)
        self.record_button.pack(side='left')
        self.play_button=tk.Button(row,text='Play recording',command=self.play,font=('Segoe UI',12),
                                   bg='#334155',fg='white',activebackground='#475569',activeforeground='white',
                                   relief='flat',padx=18,pady=12,state='disabled',takefocus=False)
        self.play_button.pack(side='left',padx=(12,0))
        self.transcribe_button=tk.Button(row,text='Transcribe',command=self.transcribe,font=('Segoe UI',12,'bold'),
                                         bg='#3b82f6',fg='white',activebackground='#60a5fa',activeforeground='white',
                                         relief='flat',padx=18,pady=12,state='disabled',takefocus=False)
        self.transcribe_button.pack(side='left',padx=(12,0))
        self.detail=tk.StringVar(value='Say: Open YouTube and search for Pakistani food.')
        tk.Label(panel,textvariable=self.detail,font=('Segoe UI',10),fg='#cbd5e1',bg='#111827',justify='left',wraplength=510).pack(anchor='w',pady=(18,0))
        tk.Label(panel,text='Transcript',font=('Segoe UI',12,'bold'),fg='#f9fafb',bg='#111827').pack(anchor='w',pady=(18,6))
        self.transcript_box=tk.Text(panel,height=5,width=1,font=('Segoe UI',11),wrap='word',bg='#1f2937',fg='#f9fafb',
                                    insertbackground='white',relief='flat',padx=10,pady=10,state='disabled')
        self.transcript_box.pack(fill='both',expand=True)
        tk.Label(panel,text='Recording and playback stay local. Transcribe sends the selected clip to Groq.\nEscape stops recording or playback.',
                 font=('Segoe UI',9),fg='#94a3b8',bg='#111827',wraplength=510,justify='left').pack(anchor='w',pady=(14,0))
        for widget in (root,self.record_button,self.play_button,self.transcribe_button,self.transcript_box):
            widget.bind('<KeyPress-space>',self.press_space)
            widget.bind('<KeyRelease-space>',self.release_space)
            widget.bind('<Escape>',self.escape)
        root.after(50,self.poll_events)

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
            self.toggle_record()
        elif self.state=='playing':
            winsound.PlaySound(None,0)
        return 'break'

    def toggle_record(self):
        if self.state in ('preparing','listening'):
            self.stop_event.set()
            self.state='stopping'
            self.status.set('Finishing recording...')
            self.record_button.config(state='disabled')
            return
        if self.state!='idle': return
        self.state='preparing'
        self.last_path=None
        self.stop_event=threading.Event()
        self.status.set('Checking microphone - please wait...')
        self.record_button.config(text='Stop recording')
        self.play_button.config(state='disabled')
        self.transcribe_button.config(state='disabled')
        self.set_transcript('')
        self.level['value']=0
        threading.Thread(target=self.record_worker,daemon=True).start()

    def record_worker(self):
        try:
            result=capture_command(stop_event=self.stop_event,on_event=lambda name,data:self.events.put((name,data)))
            path=None
            if result.speech_detected and not self.closing:
                path=save_recording(result,ROOT/'recordings'/f'command_{uuid.uuid4().hex[:8]}.wav')
            self.events.put(('finished',(result,path)))
        except Exception as exc:
            self.events.put(('error',str(exc)))

    def play(self):
        if self.state!='idle' or self.last_path is None: return
        self.state='playing'
        self.status.set('Playing your recording...')
        self.record_button.config(state='disabled')
        self.play_button.config(state='disabled')
        self.transcribe_button.config(state='disabled')
        threading.Thread(target=self.play_worker,daemon=True).start()

    def play_worker(self):
        try:
            winsound.PlaySound(str(self.last_path),winsound.SND_FILENAME)
            self.events.put(('play_finished',None))
        except Exception as exc:
            self.events.put(('error','Playback failed: '+str(exc)))

    def set_transcript(self,text):
        self.transcript_box.config(state='normal')
        self.transcript_box.delete('1.0','end')
        self.transcript_box.insert('1.0',text)
        self.transcript_box.config(state='disabled')

    def transcribe(self):
        if self.state!='idle' or self.last_path is None: return
        self.state='transcribing'
        self.status.set('Transcribing with Groq...')
        self.detail.set('Sending this recording to Groq for speech-to-text.')
        self.record_button.config(state='disabled')
        self.play_button.config(state='disabled')
        self.transcribe_button.config(state='disabled')
        self.level.config(mode='indeterminate')
        self.level.start(50)
        threading.Thread(target=self.transcribe_worker,args=(self.last_path,),daemon=True).start()

    def transcribe_worker(self,path):
        start=time.perf_counter()
        try:
            text=transcribe_recording(path)
            transcript_path=path.with_suffix('.txt')
            if not self.closing:
                transcript_path.write_text(text+'\n',encoding='utf-8')
                self.events.put(('transcribed',(text,time.perf_counter()-start,transcript_path.name)))
        except TranscriptionError as exc:
            self.events.put(('transcription_error',str(exc)))
        except Exception:
            self.events.put(('transcription_error','Could not complete transcription. Please try again.'))

    def set_idle(self):
        self.state='idle'
        self.record_button.config(text='Record command',state='normal')
        self.play_button.config(state='normal' if self.last_path else 'disabled')
        self.transcribe_button.config(state='normal' if self.last_path else 'disabled')
        self.level.stop()
        self.level.config(mode='determinate')
        self.level['value']=0

    def poll_events(self):
        if self.closing: return
        try:
            while True:
                name,data=self.events.get_nowait()
                if name=='ready' and not self.stop_event.is_set():
                    self.state='listening'
                    self.status.set('Speak now')
                elif name=='level':
                    self.level['value']=min(100,data['rms']*700)
                    if self.state=='listening' and data['speech_detected']:
                        self.status.set('Listening - finish your command')
                elif name=='finished':
                    result,path=data
                    self.set_idle()
                    if path:
                        self.last_path=path
                        self.play_button.config(state='normal')
                        self.transcribe_button.config(state='normal')
                        label='Saved - play back or transcribe' if result.reason!='max_length' else 'Reached 15 seconds - play it back'
                        self.status.set(label)
                        self.detail.set(f'{result.duration_seconds:.1f} seconds saved in recordings/{path.name}')
                    else:
                        self.status.set('No command heard - try again' if result.reason=='no_speech' else 'Recording cancelled')
                elif name=='play_finished':
                    self.set_idle()
                    self.status.set('Ready to record again')
                elif name=='transcribed':
                    text,duration,filename=data
                    self.set_idle()
                    self.set_transcript(text)
                    self.status.set('Transcript ready')
                    self.detail.set(f'Transcribed in {duration:.1f}s. Text saved in recordings/{filename}')
                elif name=='transcription_error':
                    self.set_idle()
                    self.status.set('Transcription failed - retry available')
                    self.detail.set(data)
                elif name=='error':
                    self.set_idle()
                    self.status.set('Could not complete the test')
                    self.detail.set(data+'\nCheck microphone access in Windows Settings.')
        except queue.Empty:
            pass
        self.root.after(50,self.poll_events)

    def close(self):
        self.closing=True
        self.stop_event.set()
        winsound.PlaySound(None,0)
        self.root.destroy()


def main():
    root=tk.Tk()
    RecorderApp(root)
    root.mainloop()

if __name__=='__main__':
    main()
