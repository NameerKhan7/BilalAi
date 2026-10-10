"""Credentials encrypted with Windows DPAPI for the current Windows user."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
def path_for(name):
    if name not in {'gmail','notion'}:raise ValueError('Unknown connection.')
    return ROOT/'.secrets'/(name+'.bin')
def save_secret(name,data):
    import win32crypt
    path=path_for(name);path.parent.mkdir(exist_ok=True)
    encrypted=win32crypt.CryptProtectData(json.dumps(data).encode(),'Bilal AI',None,None,None,0)
    path.write_bytes(encrypted)
def load_secret(name):
    import win32crypt
    path=path_for(name)
    if not path.is_file():return None
    try:return json.loads(win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,0)[1])
    except Exception:raise RuntimeError('The connection could not be read for this Windows user. Reconnect it.') from None
