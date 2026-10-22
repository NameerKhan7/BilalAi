"""Global left Ctrl + left Shift state only; no typing interception or key log."""
import ctypes,os
from PySide6.QtCore import QObject,QTimer,Signal


class HoldToTalk(QObject):
    changed=Signal(bool)
    def __init__(self,parent=None,key_down=None):
        super().__init__(parent);self.held=False;self.available=False
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
        if self.available:self.timer.start()
    def poll(self):
        down=bool(self.key_down(0xA2) and self.key_down(0xA0)) if self.key_down else False
        if down!=self.held:
            self.held=down;self.changed.emit(down)
    def stop(self):
        self.timer.stop();self.held=False
