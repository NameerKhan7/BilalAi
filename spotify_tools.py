"""Bounded Spotify executor with cancellation and a separate Windows process."""
from pathlib import Path
from runtime_paths import worker_python
import json, subprocess, sys, time
from app_tools import AppLaunchError

class SpotifyActionError(AppLaunchError): pass

def play_spotify(query, cancel_event=None):
    query=query.strip()
    if not query or len(query)>400:
        raise SpotifyActionError('Specify a Spotify search under 400 characters.')
    with subprocess.Popen([worker_python(),str(Path(__file__).with_name('spotify_worker.py'))],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf-8',shell=False,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as worker:
        worker.stdin.write(json.dumps({'query':query})+'\n');worker.stdin.flush()
        deadline=time.monotonic()+35
        while worker.poll() is None:
            cancelled=cancel_event is not None and cancel_event.is_set()
            if cancelled or time.monotonic()>deadline:
                worker.kill();worker.wait()
                if cancelled:
                    from request_router import RequestCancelled
                    raise RequestCancelled('Stopped Spotify automation. Playback already started may continue.')
                raise SpotifyActionError('Spotify automation timed out; playback was not verified. Keep Spotify visible and retry.')
            time.sleep(.1)
        try: result=json.loads(worker.stdout.read())
        except ValueError:
            raise SpotifyActionError('Spotify automation could not start. Install requirements.txt and retry.') from None
        if not result.get('ok'):
            raise SpotifyActionError(result.get('error','Spotify playback was not verified.'))
        return result['reply']
