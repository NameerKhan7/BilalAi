"""Opt-in native checks. No email, account writes, power or microphone access."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from task_store import TaskStore


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--browser',action='store_true');parser.add_argument('--clipboard',action='store_true');args=parser.parse_args()
    report={'checked_at':time.time(),'scope':'Native component checks, not microphone, semantic benchmark or release acceptance.'}
    from hold_to_talk import KeyboardHook
    hook=KeyboardHook((162,160,32),lambda down:None);hook.start();hook.stop();report['keyboard_hook']={'registered':not hook.error,'released':not hook.thread.is_alive(),'physical_trials':'pending'}
    if args.clipboard:
        import win32clipboard
        from desktop_worker import DesktopSession
        win32clipboard.OpenClipboard()
        try:
            # Preserve Unicode text; abort rather than destroy a non-text clipboard.
            if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):raise ValueError('Clipboard does not contain Unicode text; native check skipped to preserve it.')
            original=win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:win32clipboard.CloseClipboard()
        session=DesktopSession.__new__(DesktopSession)
        try:
            payload='Aa0+/= \t\n'*12500
            payload=payload[:100000]
            written=session.clipboard_write(payload);read=session.clipboard_read()
            report['clipboard']={'bytes':len(payload.encode()),'verified':written['verified'] and read.get('text')==payload}
        finally:session.clipboard_write(original)
    if args.browser:
        from dom_bridge import DOMBridge
        store=TaskStore();before=store.setting('allowed_domains',[]);domains=['example.com','www.python.org','docs.python.org','en.wikipedia.org','www.wikipedia.org']
        store.set_setting('allowed_domains',sorted(set(before+domains)));bridge=DOMBridge();results=[]
        try:
            for domain in domains:
                opened=bridge.call('browser_open',{'url':'https://'+domain+'/'})
                read=bridge.call('browser_read',{'tab_id':opened['tab_id']}) if opened.get('tab_id') else {}
                results.append({'domain':domain,'opened':opened.get('verified',False),'read':read.get('verified',False),'characters':len(read.get('text','')),'error':opened.get('error') or read.get('error')})
        finally:bridge.close();store.set_setting('allowed_domains',before)
        report['browser']=results
    output=Path(__file__).resolve().parents[1]/'logs/capability_runtime.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
