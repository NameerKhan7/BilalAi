"""Global left Ctrl + left Shift state only; no typing interception or key log."""
import ctypes,os,threading
from PySide6.QtCore import QObject,QTimer,Signal

KEY_NAMES={'Ctrl':0xA2,'Shift':0xA0,'Alt':0xA4,'Space':0x20,'Escape':0x1B,'Backspace':0x08}

def parse_chord(text):
    names=[x.strip() for x in text.split('+')]
    lookup={key.casefold():value for key,value in KEY_NAMES.items()}
    keys=[lookup.get(name.casefold(),ord(name.upper()) if len(name)==1 and name.isascii() and name.isalnum() else -1) for name in names]
    if len(keys)<2 or len(keys)>5 or -1 in keys or len(set(keys))!=len(keys) or not any(k in (0xA2,0xA0,0xA4) for k in keys):raise ValueError('Use distinct keys with Ctrl, Shift or Alt, for example Ctrl+Shift+Space.')
    if set(keys) in ({0xA2,0xA0,0x1B},{0xA4,0x73}):raise ValueError('This chord conflicts with a Windows shortcut.')
    return keys


class HoldToTalk(QObject):
    changed=Signal(bool)
    def __init__(self,parent=None,key_down=None,keys=None,toggle=False):
        super().__init__(parent);self.held=False;self.available=False
        self.keys=tuple(keys or (0xA2,0xA0));self.toggle=toggle;self.chord_down=False;self.injected=key_down is not None;self.hook=None
        if not self.keys or len(set(self.keys))!=len(self.keys):raise ValueError('Choose a chord with distinct keys.')
        self.key_down=key_down
        if self.key_down is None and os.name=='nt':
            try:
                function=ctypes.WinDLL('user32',use_last_error=True).GetAsyncKeyState
                function.argtypes=[ctypes.c_int];function.restype=ctypes.c_short
                self.key_down=lambda key:bool(function(key)&0x8000)
            except (OSError,AttributeError):self.key_down=None
        self.available=self.key_down is not None
        self.timer=QTimer(self);self.timer.setInterval(25);self.timer.timeout.connect(self.poll)
    def start(self):
        if not self.available:return
        if self.injected:self.timer.start()
        else:
            self.hook=KeyboardHook(self.keys,self.edge);self.hook.start()
    def edge(self,down):
        if down==self.chord_down:return
        self.chord_down=down
        if self.toggle:
            if not down:return
            self.held=not self.held
        else:self.held=down
        self.changed.emit(self.held)
    def poll(self):
        down=bool(all(self.key_down(key) for key in self.keys)) if self.key_down else False
        self.edge(down)
    def stop(self):
        self.timer.stop();self.held=False
        if self.hook:self.hook.stop()


class KeyboardHook:
    """WH_KEYBOARD_LL tracks configured keys only. It never records typed text.

    Callback forwards every key immediately. Work runs outside the hook thread;
    injected keys cannot activate the assistant or approve an action.
    """
    def __init__(self,keys,edge):self.keys=set(keys);self.edge=edge;self.down=set();self.thread_id=None;self.ready=threading.Event();self.error=None
    def start(self):
        self.thread=threading.Thread(target=self.run,daemon=True,name='bilal-hotkey');self.thread.start()
        if not self.ready.wait(2) or self.error:raise RuntimeError('The global shortcut could not be registered.')
    def run(self):
        from ctypes import wintypes
        user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        class Key(ctypes.Structure):_fields_=[('vk',wintypes.DWORD),('scan',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        user.SetWindowsHookExW.argtypes=[ctypes.c_int,callback_type,wintypes.HINSTANCE,wintypes.DWORD];user.SetWindowsHookExW.restype=wintypes.HHOOK
        user.CallNextHookEx.argtypes=[wintypes.HHOOK,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];user.CallNextHookEx.restype=ctypes.c_ssize_t
        user.UnhookWindowsHookEx.argtypes=[wintypes.HHOOK];user.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE
        self.thread_id=kernel.GetCurrentThreadId()
        def callback(code,message,data):
            try:
                if code>=0:
                    key=ctypes.cast(data,ctypes.POINTER(Key)).contents
                    if not key.flags&0x10:
                        vk=key.vk
                        if vk==0x11:vk=0xA3 if key.flags&1 else 0xA2
                        if vk==0x10:vk=0xA1 if key.scan==0x36 else 0xA0
                        if vk==0x12:vk=0xA5 if key.flags&1 else 0xA4
                        if vk in self.keys:
                            if message in (0x100,0x104):self.down.add(vk)
                            elif message in (0x101,0x105):self.down.discard(vk)
                            self.edge(self.keys<=self.down)
            finally:return user.CallNextHookEx(None,code,message,data)
        self.callback=callback_type(callback)
        hook=user.SetWindowsHookExW(13,self.callback,kernel.GetModuleHandleW(None),0)
        if not hook:self.error=ctypes.get_last_error();self.ready.set();return
        self.ready.set();message=wintypes.MSG()
        try:
            while user.GetMessageW(ctypes.byref(message),None,0,0)>0:
                user.TranslateMessage(ctypes.byref(message));user.DispatchMessageW(ctypes.byref(message))
        finally:user.UnhookWindowsHookEx(hook);self.down.clear()
    def stop(self):
        if self.thread_id:
            from ctypes import wintypes
            user=ctypes.WinDLL('user32');user.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            user.PostThreadMessageW(self.thread_id,0x12,0,0)
            if threading.current_thread()!=getattr(self,'thread',None):self.thread.join(timeout=2)
