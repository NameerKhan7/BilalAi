"""SAF-7: Windows Credential Manager with an explicit legacy env migration."""
import os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES={'GEMINI_API_KEY','GROQ_API_KEY','ANTHROPIC_API_KEY'}


def save_key(name,value):
    if name not in NAMES or not value.strip():raise ValueError('Unknown provider or empty key.')
    import win32cred
    win32cred.CredWrite({'Type':win32cred.CRED_TYPE_GENERIC,'TargetName':'BilalAI/'+name,
        'CredentialBlob':value,'Persist':win32cred.CRED_PERSIST_LOCAL_MACHINE,'UserName':'BilalAI'},0)
    if credential_key(name)!=value:raise RuntimeError('Credential readback did not match.')


def credential_key(name):
    if name not in NAMES:raise ValueError('Unknown provider.')
    if os.name!='nt':return None
    import win32cred
    try:result=win32cred.CredRead('BilalAI/'+name,win32cred.CRED_TYPE_GENERIC)
    except Exception as exc:
        if getattr(exc,'winerror',None)==1168 or (exc.args and exc.args[0]==1168):return None
        raise RuntimeError('Windows provider credential could not be read.') from None
    value=result['CredentialBlob'];return value.decode('utf-16-le') if isinstance(value,bytes) else value


def get_key(name):
    if name not in NAMES:raise ValueError('Unknown provider.')
    if os.environ.get(name):return os.environ[name]
    value=credential_key(name)
    if value:return value
    from dotenv import dotenv_values
    return dotenv_values(ROOT/'.env').get(name)


def migrate_env(path=None):
    from dotenv import dotenv_values
    path=Path(path or ROOT/'.env');values=dotenv_values(path);moved=[]
    for name in NAMES:
        if values.get(name):save_key(name,values[name]);moved.append(name)
    if moved:
        lines=path.read_text(encoding='utf-8-sig').splitlines()
        kept=[]
        for line in lines:
            matched=next((name for name in moved if re.match(r'^\s*(?:export\s+)?'+re.escape(name)+r'\s*=',line)),None)
            kept.append(matched+'=' if matched else line)
        temporary=path.with_suffix('.migration.tmp');temporary.write_text('\n'.join(kept)+'\n',encoding='utf-8');temporary.replace(path)
    return moved
