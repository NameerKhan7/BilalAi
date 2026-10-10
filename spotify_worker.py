"""Spotify search, observed result invocation, and Windows playback verification.
Run: python spotify_worker.py --query "jazz"
No coordinate clicks, global media keys, generated commands or login automation.
"""
import argparse, asyncio, ctypes, json, os, re, sys, time
from urllib.parse import quote
from pathlib import Path

STAGE="starting"
REPORT=Path(__file__).resolve().parent/"logs"/"spotify_latest.json"

class PlaybackFailure(RuntimeError): pass

def words(text): return set(re.findall(r'\w+',text.casefold()))

def matches_title(expected,actual):
    return bool(words(expected)) and words(expected).issubset(words(actual))

def process_name(pid):
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle: return ''
    try:
        size=ctypes.c_ulong(32768);buffer=ctypes.create_unicode_buffer(size.value)
        if kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)):
            return os.path.basename(buffer.value).casefold()
        return ''
    finally: kernel.CloseHandle(handle)

def spotify_window(desktop):
    candidates=[w for w in desktop.windows(visible_only=True) if process_name(w.process_id())=='spotify.exe']
    candidates=[w for w in candidates if w.rectangle().width()>400 and w.rectangle().height()>250]
    return candidates[0] if len(candidates)==1 else None

async def media_snapshot():
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
    manager=await Manager.request_async()
    sessions=[s for s in manager.get_sessions() if 'spotify' in s.source_app_user_model_id.casefold()]
    if len(sessions)!=1: return None
    session=sessions[0];props=await session.try_get_media_properties_async()
    return {'title':props.title,'artist':props.artist,
            'playing':session.get_playback_info().playback_status==Status.PLAYING}

def result_buttons(window):
    candidates=[]
    for button in window.descendants(control_type='Button'):
        match=re.fullmatch(r'Play\s+(.+)',button.window_text().strip(),re.I)
        if not match or not button.is_visible() or not button.is_enabled(): continue
        title=match.group(1).strip(' "')
        if title.casefold() in {'pause','next','previous','shuffle','back','queue'}: continue
        candidates.append((button,title))
    return candidates

def execute(query):
    global STAGE
    from pywinauto import Desktop
    STAGE='checking playback support'
    asyncio.run(media_snapshot())  # Check status API before changing playback.
    STAGE='opening Spotify search'
    desktop=Desktop(backend='uia')
    os.startfile('spotify:search:'+quote(query,safe=''))
    deadline=time.monotonic()+12;window=None
    while time.monotonic()<deadline:
        window=spotify_window(desktop)
        if window: break
        time.sleep(.3)
    if window is None:
        raise PlaybackFailure('Spotify did not expose one usable window. Open Spotify, sign in yourself if needed, and retry.')
    STAGE='verifying search field'
    search_verified=False
    while time.monotonic()<deadline:
        for edit in window.descendants(control_type='Edit'):
            try: value=edit.get_value()
            except Exception: continue
            if value.strip().casefold()==query.casefold(): search_verified=True;break
        if search_verified: break
        time.sleep(.3)
    if not search_verified:
        raise PlaybackFailure('Opened Spotify search, but could not verify the search field. Playback was not attempted. Keep Spotify visible and retry.')
    STAGE='finding a playable result'
    time.sleep(1)
    deadline=time.monotonic()+6;candidates=[]
    while time.monotonic()<deadline:
        candidates=result_buttons(window)
        if candidates: break
        time.sleep(.3)
    if not candidates:
        raise PlaybackFailure('Spotify searched, but no named playable result was exposed. Try a specific song and artist. No Play control was pressed.')
    candidates.sort(key=lambda item:(not matches_title(query,item[1]),item[0].rectangle().top,item[0].rectangle().left))
    target,selected_title=candidates[0]
    STAGE='pressing result Play'
    target.invoke()
    STAGE='verifying playback'
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        state=asyncio.run(media_snapshot())
        if state and state['playing'] and matches_title(selected_title,state['title']):
            artist=' by '+state['artist'] if state['artist'] else ''
            return {'ok':True,'reply':f"Playing {state['title']}{artist} on Spotify.",
                    'selected_result':selected_title,'media':state}
        time.sleep(.4)
    raise PlaybackFailure(f'Pressed Play for {selected_title}, but could not verify that result playing. Spotify may require interaction or may be playing an advertisement.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--query');args=parser.parse_args()
    try:
        query=args.query if args.query is not None else json.loads(sys.stdin.readline())['query']
        query=query.strip()
        if not query or len(query)>400: raise PlaybackFailure('Specify a Spotify search under 400 characters.')
        result=execute(query)
    except PlaybackFailure as exc: result={'ok':False,'error':str(exc)}
    except ImportError: result={'ok':False,'error':'Spotify dependencies are missing. Install requirements.txt.'}
    except Exception as exc:
        result={'ok':False,'error':f'Spotify automation failed ({type(exc).__name__}); playback was not verified.'}
    result['stage']=STAGE
    try:
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    except OSError: pass
    print(json.dumps(result,ensure_ascii=True))
    return 0 if result['ok'] else 1

if __name__=='__main__': raise SystemExit(main())
