"""Launch installed apps locally. Gemini is not involved."""
from pathlib import Path
import os,subprocess,re,json
from functools import lru_cache
LABELS={'notion':'Notion','spotify':'Spotify','chrome':'Chrome'}

class AppLaunchError(RuntimeError): pass


@lru_cache(maxsize=1)
def store_catalog():
    script="[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-StartApps | Where-Object { $_.Name -match '^(Notion|Spotify)$' } | ConvertTo-Json -Compress"
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
            capture_output=True,check=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        rows=json.loads(result.stdout.decode('utf-8-sig') or '[]')
        if isinstance(rows,dict): rows=[rows]
        return {row['Name'].lower():row['AppID'] for row in rows if row.get('Name') and row.get('AppID')}
    except (OSError,subprocess.SubprocessError,ValueError): return {}

def open_app(name):
    if name not in LABELS: raise AppLaunchError('That app is not supported yet.')
    candidates=[]
    if name=='notion':
        for base in ('LOCALAPPDATA',):
            value=os.environ.get(base)
            if value: candidates.extend([Path(value)/'Programs/Notion/Notion.exe',Path(value)/'Notion/Notion.exe'])
    elif name=='spotify':
        value=os.environ.get('APPDATA')
        if value: candidates.append(Path(value)/'Spotify/Spotify.exe')
    else:
        from browser_tools import find_chrome
        candidates.append(find_chrome())
    executable=next((path for path in candidates if path.is_file()),None)
    if executable is not None:
        command=[str(executable)]
    else:
        app_id=store_catalog().get(name)
        if not app_id or not re.fullmatch(r'[A-Za-z0-9_.!]+',app_id):
            raise AppLaunchError(f'{LABELS[name]} was not found on this computer.')
        command=[str(Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'), 'shell:AppsFolder\\'+app_id]
    try:
        subprocess.Popen(command,shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise AppLaunchError(f'Could not open {LABELS[name]}. Check that it is installed.') from exc
    return f'Opened {LABELS[name]}.'
