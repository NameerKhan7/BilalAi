"""Serial access to one owned browser; no worker uses the user's Chrome profile."""
import threading


class DOMBridge:
    def __init__(self):
        from agent_tools import DesktopBridge
        self.worker=DesktopBridge('dom_worker.py');self.lock=threading.Lock()
    def call(self,name,args,cancel_event=None):
        from request_router import RequestCancelled
        while not self.lock.acquire(timeout=.1):
            if cancel_event and cancel_event.is_set():raise RequestCancelled('Browser task cancelled.')
        try:return self.worker.call(name,args,cancel_event)
        finally:self.lock.release()
    def close(self):self.worker.close()
