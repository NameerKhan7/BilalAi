"""Fixed local Windows power actions, reachable only through human approval."""
import ctypes,os,subprocess,time
from contextlib import contextmanager
from pathlib import Path
ACTIONS={'sleep':'Sleep','shutdown':'Shut down','restart':'Restart'}
APPROVAL_SECONDS=120


@contextmanager
def shutdown_privilege():
    import win32api,win32con,win32security
    token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_ADJUST_PRIVILEGES|win32con.TOKEN_QUERY)
    previous=None
    try:
        luid=win32security.LookupPrivilegeValue(None,win32security.SE_SHUTDOWN_NAME)
        win32api.SetLastError(0)
        previous=win32security.AdjustTokenPrivileges(token,False,[(luid,win32con.SE_PRIVILEGE_ENABLED)])
        if win32api.GetLastError()==1300:raise RuntimeError('Windows has not granted this user the system power privilege.')
        yield
    finally:
        try:
            if previous is not None:win32security.AdjustTokenPrivileges(token,False,previous)
        finally:token.Close()


def system_directory():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    function=kernel.GetSystemDirectoryW;function.argtypes=[ctypes.c_wchar_p,ctypes.c_uint];function.restype=ctypes.c_uint
    buffer=ctypes.create_unicode_buffer(32768);size=function(buffer,len(buffer))
    if not size or size>=len(buffer):raise RuntimeError('Windows system directory could not be resolved.')
    return Path(buffer.value)


def suspend_windows():
    library=ctypes.WinDLL('powrprof',use_last_error=True)
    function=library.SetSuspendState;function.argtypes=[ctypes.c_ubyte]*3;function.restype=ctypes.c_ubyte
    with shutdown_privilege():
        if not function(False,False,False):raise RuntimeError('Windows rejected the sleep request (error '+str(ctypes.get_last_error())+').')


class WindowsPower:
    def execute(self,action):
        if action not in ACTIONS:raise ValueError('Unsupported power action.')
        if os.name!='nt':raise RuntimeError('Power control requires Windows.')
        if action=='sleep':
            suspend_windows()
            return {'ok':True,'verified':False,'reply':'The Windows sleep call completed. If the laptop slept, it is now awake again.'}
        command=[str(system_directory()/'shutdown.exe'),'/s' if action=='shutdown' else '/r','/t','0']
        # A positive shutdown timeout implicitly forces app closure; use zero and never /f.
        result=subprocess.run(command,shell=False,capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise RuntimeError('Windows rejected the '+action+' request (exit '+str(result.returncode)+').')
        return {'ok':True,'verified':False,'reply':'Windows accepted the '+action+' request. Open apps may ask you to save your work.'}


class PowerActions:
    def __init__(self,state,backend=None):self.state=state;self.backend=backend or WindowsPower()
    def request(self,action):
        if action not in ACTIONS:raise ValueError('Choose sleep, shutdown or restart.')
        row=self.state.propose('system_power',{'action':action})
        return {'ok':True,'verified':False,'approval_id':row['id'],'power_confirmation':True,
                'reply':ACTIONS[action]+' is ready for your confirmation. Save your work, then confirm in Bilal.'}
    def check_fresh(self,row):
        if row['payload'].get('action') not in ACTIONS:raise ValueError('Unsupported power action.')
        age=time.time()-row['created']
        if not 0<=age<=APPROVAL_SECONDS:raise ValueError('This power confirmation expired. Ask Bilal again when you are ready.')
    def execute_approved(self,row,cancel_event=None):
        self.check_fresh(row)
        if cancel_event is not None and cancel_event.is_set():raise RuntimeError('Cancelled before the power action.')
        return self.backend.execute(row['payload']['action'])
