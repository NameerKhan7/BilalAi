"""Explicit, temporary grants to one existing Windows window.

No cookies or credentials are copied. A per-window property detects destruction
and HWND reuse; PID creation time detects process reuse. Grants are not durable.
"""
import os,secrets,time,threading
from dataclasses import dataclass,asdict


@dataclass(frozen=True)
class WindowIdentity:
    handle:int
    pid:int
    process_created:float
    process:str
    window_class:str
    property_name:str
    property_value:int
    title:str


class NativeWindows:
    def user32(self):
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.SetPropW.argtypes=[wintypes.HWND,wintypes.LPCWSTR,wintypes.HANDLE];user.SetPropW.restype=wintypes.BOOL
        for name in ('GetPropW','RemovePropW'):
            function=getattr(user,name);function.argtypes=[wintypes.HWND,wintypes.LPCWSTR];function.restype=wintypes.HANDLE
        return user
    def describe(self,handle):
        import win32gui,win32process,psutil
        from desktop_worker import BLOCKED_APPS
        if not win32gui.IsWindow(handle):raise ValueError('That window is no longer open.')
        handle=win32gui.GetAncestor(handle,2) or handle
        pid=win32process.GetWindowThreadProcessId(handle)[1]
        try:process=psutil.Process(pid);name=process.name().casefold();created=process.create_time()
        except psutil.Error:raise ValueError('That application closed or Windows refused access to it.') from None
        title=win32gui.GetWindowText(handle)
        if pid==os.getpid() or name in BLOCKED_APPS or title.casefold().startswith('bilal ai'):raise ValueError('Choose the app window, not Bilal, a terminal or a protected app.')
        if not win32gui.IsWindowVisible(handle) or win32gui.GetClassName(handle) in {'Progman','WorkerW','Shell_TrayWnd','ConsoleWindowClass'}:raise ValueError('Choose an application window, not the desktop or taskbar.')
        if any(word in title.casefold() for word in ('incognito','inprivate','private browsing','password manager','sign in','sign-in','log in','authentication')):raise ValueError('Open the intended signed-in app page first. Login and private windows are excluded.')
        return {'handle':handle,'pid':pid,'process_created':created,'process':name,'window_class':win32gui.GetClassName(handle),'title':title}
    def tag(self,handle,name,value):
        user=self.user32()
        if not user.SetPropW(handle,name,value) or user.GetPropW(handle,name)!=value:raise ValueError('Windows refused access to this window. Elevated windows are not supported.')
    def property(self,handle,name):
        return self.user32().GetPropW(handle,name)
    def untag(self,handle,name):
        import win32gui
        if win32gui.IsWindow(handle):self.user32().RemovePropW(handle,name)


def validate_identity(identity,native=None):
    native=native or NativeWindows();current=native.describe(identity['handle'])
    for field in ('handle','pid','process_created','process','window_class'):
        if current[field]!=identity[field]:raise ValueError('The selected window changed or was closed. Hand it to Bilal again.')
    if native.property(identity['handle'],identity['property_name'])!=identity['property_value']:raise ValueError('Window access expired or was revoked. Select it again.')
    return current


class WindowGrants:
    def __init__(self,native=None,clock=None):self.native=native or NativeWindows();self.clock=clock or time.monotonic;self.entries={};self.lock=threading.RLock()
    def issue(self,handle,seconds=900):
        info=self.native.describe(handle);token=secrets.token_hex(16);name='BilalAI.Handoff.'+token;value=secrets.randbelow(2**30)+1
        self.native.tag(info['handle'],name,value)
        identity=WindowIdentity(**info,property_name=name,property_value=value)
        with self.lock:self.entries[token]={'identity':asdict(identity),'expires':self.clock()+seconds,'owner':None}
        return token
    def bind(self,token,task_id):
        with self.lock:
            row=self.entries.get(token)
            if not row or row['expires']<=self.clock():raise ValueError('Window access expired. Select the window again.')
            if row['owner'] not in (None,task_id):raise ValueError('This window grant belongs to a different task.')
            if any(other is not row and other['expires']>self.clock() and other['owner'] not in (None,task_id) and other['identity']['handle']==row['identity']['handle'] for other in self.entries.values()):
                raise ValueError('Another task already controls this window. Stop that task before handing it over again.')
            validate_identity(row['identity'],self.native);row['owner']=task_id
            return dict(row['identity'])
    def revoke(self,token):
        with self.lock:row=self.entries.pop(token,None)
        if row:
            try:self.native.untag(row['identity']['handle'],row['identity']['property_name'])
            except Exception:pass
    def revoke_all(self):
        for token in list(self.entries):self.revoke(token)
