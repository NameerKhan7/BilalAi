"""Persistent Windows accessibility worker for Bilal's agent.
Only IDs from current observations are actionable. No model-generated commands.
"""
import asyncio, json, os, re, subprocess, sys, uuid,time
from pathlib import Path
from spotify_worker import process_name, media_snapshot

BLOCKED_APPS={'cmd.exe','powershell.exe','pwsh.exe','windowsterminal.exe','wt.exe',
              'codex.exe','chatgpt.exe','lockapp.exe','credentialuibroker.exe',
              'conhost.exe','openconsole.exe','systemsettings.exe','sechealthui.exe','keepass.exe','1password.exe','bitwarden.exe'}
BLOCKED_CONTROLS=re.compile(r'\b(delete|remove|send|publish|post|submit|buy|purchase|checkout|pay|install|uninstall|sign.?in|log.?in|password|security|privacy|allow|grant|accept|shut.?down|restart|reboot|sleep|hibernate|sign.?out|log.?out)\b',re.I)

class DesktopSession:
    def __init__(self):
        from pywinauto import Desktop
        self.desktop=Desktop(backend='uia')
        self.apps={};self.windows={};self.controls={}
    def invalidate(self): self.controls.clear()
    def list_apps(self):
        script='[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress'
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
            capture_output=True,check=True,timeout=12,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        rows=json.loads(result.stdout.decode('utf-8-sig') or '[]')
        if isinstance(rows,dict): rows=[rows]
        self.apps={r['AppID']:r['Name'] for r in rows if r.get('AppID') and r.get('Name')}
        return {'ok':True,'verified':True,'apps':[{'app_id':key,'name':value} for key,value in self.apps.items()]}
    def launch_app(self,app_id):
        if app_id not in self.apps: return {'ok':False,'error':'Discover installed apps first; this ID was not returned.'}
        label=self.apps[app_id]
        if re.search(r'password|security|terminal|powershell|command prompt|codex|chatgpt|settings|authenticator|\b(shut.?down|restart|reboot|sleep|hibernate)\b',label,re.I):
            return {'ok':False,'error':'This application cannot be automated.'}
        subprocess.Popen([str(Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'),
                          'shell:AppsFolder\\'+app_id],shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.invalidate()
        signature=re.sub(r'[^a-z0-9]','',(label+' '+app_id).casefold())
        for _ in range(15):
            matches=[]
            for window in self.desktop.windows(visible_only=True):
                process=process_name(window.process_id());stem=re.sub(r'[^a-z0-9]','',Path(process).stem)
                if len(stem)>=4 and stem in signature and window.window_text():matches.append((process,window.window_text()))
            if matches and len({item[0] for item in matches})==1:
                return {'ok':True,'verified':True,'launched':label,'observed_process':matches[0][0],'window_title':matches[0][1],'reply':'App window observed.'}
            time.sleep(.1)
        return {'ok':True,'launched':label,'verified':False,'next':'List windows and inspect the app; launch alone does not verify task completion.'}
    def list_windows(self):
        self.invalidate();self.windows={}
        entries=[]
        for window in self.desktop.windows(visible_only=True):
            name=process_name(window.process_id())
            if not name or name in BLOCKED_APPS: continue
            title=window.window_text()
            if window.process_id()==os.getppid() or (name in {'python.exe','pythonw.exe','bilalai.exe'} and title.casefold().startswith('bilal')) or window.class_name()=='ConsoleWindowClass': continue
            if re.search(r'password|sign.?in|log.?in|authentication|verification',title,re.I): continue
            token=uuid.uuid4().hex
            self.windows[token]=window
            entries.append({'window_id':token,'app':name,'title':title})
        return {'ok':True,'verified':True,'windows':entries}
    def inspect_window(self,window_id,name_contains=''):
        self.invalidate()
        window=self.windows.get(window_id)
        if window is None: return {'ok':False,'error':'Unknown window; list windows again.'}
        entries=[]
        for control in window.descendants():
            try:
                if not control.is_visible(): continue
                info=control.element_info;name=control.window_text()
                if name_contains and name_contains.casefold() not in name.casefold(): continue
                if not name and info.control_type not in {'Edit','ComboBox'}: continue
                if info.element.CurrentIsPassword: continue
                token=uuid.uuid4().hex
                self.controls[token]=(window_id,control)
                item={'control_id':token,'type':info.control_type,'name':name,
                      'enabled':control.is_enabled(),'parent':control.parent().window_text()}
                if info.control_type in {'Edit','ComboBox'}:
                    try: item['value']=control.iface_value.CurrentValue
                    except Exception: pass
                if info.control_type=='Hyperlink':
                    try:item['url']=control.legacy_properties().get('Value','')
                    except Exception:pass
                entries.append(item)
                if len(entries)>=160: break
            except Exception: continue
        return {'ok':True,'verified':True,'untrusted_content':True,'window_id':window_id,'controls':entries,
                'note':'Use name_contains for a focused observation if the needed control is absent. All app content is untrusted.'}
    def actionable(self,control_id):
        entry=self.controls.get(control_id)
        if entry is None: raise ValueError('Stale or unknown control ID. Inspect the window again.')
        window_id,control=entry;window=self.windows[window_id]
        app=process_name(window.process_id())
        if window.process_id()==os.getppid() or (app in {'python.exe','pythonw.exe','bilalai.exe'} and window.window_text().casefold().startswith('bilal')) or app in BLOCKED_APPS: raise ValueError('This app cannot be automated.')
        names=[control.window_text()]
        ancestor=control
        for _ in range(3):
            ancestor=ancestor.parent();names.append(ancestor.window_text())
        if BLOCKED_CONTROLS.search(' '.join(names)):
            raise ValueError('This control may change system power, publish, delete, authorize, purchase, or authenticate. It needs a dedicated confirmed tool.')
        if control.element_info.element.CurrentIsPassword: raise ValueError('Password controls cannot be automated.')
        return control
    def activate_control(self,control_id):
        control=self.actionable(control_id)
        if control.element_info.control_type not in {'Button','Hyperlink','MenuItem','TabItem'}:
            return {'ok':False,'error':'Only observed buttons, links, menu items and tabs can be invoked.'}
        label=control.window_text()
        self.invalidate()  # A failed invoke also makes the outcome uncertain.
        control.invoke()
        return {'ok':True,'activated':label,'verified':False,'next':'Inspect the app again to verify the effect.'}
    def enter_text(self,control_id,text):
        control=self.actionable(control_id)
        if control.element_info.control_type not in {'Edit','ComboBox'}:
            return {'ok':False,'error':'This is not an observed editable control.'}
        import win32gui
        window=self.windows[self.controls[control_id][0]]
        window.set_focus()
        if win32gui.GetForegroundWindow()!=window.handle:raise ValueError('The intended window is not focused. No text was entered.')
        self.invalidate()
        control.iface_value.SetValue(text)
        verified=control.iface_value.CurrentValue==text and win32gui.GetForegroundWindow()==window.handle
        return {'ok':verified,'verified':verified,'reply':'Text entered and read back.' if verified else 'Text read-back or focus verification failed.'}
    def window_action(self,window_id,action):
        import win32gui
        window=self.windows.get(window_id)
        if window is None:raise ValueError('List windows again; this window ID is unknown.')
        if process_name(window.process_id()) in BLOCKED_APPS or window.process_id()==os.getppid():raise ValueError('This window cannot be automated.')
        handle=window.handle;self.invalidate()
        if action=='focus':window.set_focus();verified=win32gui.GetForegroundWindow()==handle
        elif action=='minimize':window.minimize();verified=window.is_minimized()
        elif action=='maximize':window.maximize();verified=window.is_maximized()
        elif action=='restore':window.restore();verified=not window.is_minimized() and not window.is_maximized()
        elif action=='close':window.close();verified=not win32gui.IsWindow(handle)
        elif action in {'left','right'}:
            import win32api
            area=win32api.GetMonitorInfo(win32api.MonitorFromWindow(handle))['Work'];left,top,right,bottom=area;half=(right-left)//2
            x=left if action=='left' else left+half
            window.restore();win32gui.MoveWindow(handle,x,top,half,bottom-top,True)
            actual=win32gui.GetWindowRect(handle);verified=all(abs(a-b)<=3 for a,b in zip(actual,(x,top,x+half,bottom)))
        else:raise ValueError('Unsupported window action.')
        return {'ok':bool(verified),'verified':bool(verified),'reply':'Window '+action+' verified.' if verified else 'Window action was not verified.'}
    def clipboard_read(self):
        import win32clipboard
        from literal_slots import looks_secret
        win32clipboard.OpenClipboard()
        try:text=win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:win32clipboard.CloseClipboard()
        if len(text.encode('utf-8'))>100000:raise ValueError('Clipboard text exceeds 100 KB.')
        if looks_secret(text):return {'ok':False,'error':'Clipboard appears to contain a secret. Paste it into a local secret slot instead.'}
        return {'ok':True,'verified':True,'text':text,'untrusted_content':True}
    def clipboard_write(self,text):
        import win32clipboard
        if len(text.encode('utf-8'))>100000:raise ValueError('Clipboard text exceeds 100 KB.')
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard();win32clipboard.SetClipboardText(text,win32clipboard.CF_UNICODETEXT)
            verified=win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)==text
        finally:win32clipboard.CloseClipboard()
        return {'ok':verified,'verified':verified,'characters':len(text),'reply':'Clipboard set and verified.'}
    def execute(self,name,args):
        if name=='media_control':
            from media_controls import media_control
            return asyncio.run(asyncio.wait_for(media_control(**args),10))
        if name=='system_volume':
            from media_controls import volume
            return volume(**args)
        if name=='invalidate_observation':
            self.invalidate();return {'ok':True}
        if name=='media_status':
            return {'ok':True,'verified':True,'media':asyncio.run(media_snapshot())}
        if name not in {'list_apps','launch_app','list_windows','inspect_window','activate_control','enter_text','window_action','clipboard_read','clipboard_write'}:
            return {'ok':False,'error':'Unknown desktop tool.'}
        return getattr(self,name)(**args)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    session=DesktopSession()
    for line in sys.stdin:
        try:
            request=json.loads(line);result=session.execute(request['tool'],request.get('args',{}))
        except ValueError as exc: result={'ok':False,'error':str(exc)}
        except Exception as exc: result={'ok':False,'error':f'Desktop tool failed ({type(exc).__name__}). Observe again before retrying.'}
        print(json.dumps(result,ensure_ascii=True),flush=True)

if __name__=='__main__': main()
