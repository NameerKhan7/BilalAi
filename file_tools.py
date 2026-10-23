"""CTL-7/SAF-5/8: folder-scoped files with exact UTF-8 writes and version snapshots."""
from pathlib import Path
import os,hashlib,json,uuid,shutil
from literal_slots import looks_secret


class FileTools:
    def __init__(self,store):self.store=store;self.versions=store.path.parent/'versions'
    def checked(self,path,write=False):
        path=Path(path).expanduser().resolve()
        roots=[Path(x).expanduser().resolve() for x in self.store.setting('allowed_folders',[])]
        if not any(path==root or root in path.parents for root in roots):raise ValueError('Path is outside allowed folders.')
        if any(part.casefold() in {'.git','.secrets','.ssh','.codex','.aws','venv','.venv'} for part in path.parts):raise ValueError('Private/system directories are blocked.')
        if any(':' in part for part in path.parts[1:]) or path.is_reserved():raise ValueError('Reserved or alternate-stream paths are blocked.')
        if not write and (path.name.casefold().startswith('.env') or path.name.casefold() in {'auth.json','credentials.json','token.json','id_rsa','id_ed25519'} or path.suffix.lower() in {'.pem','.key','.pfx'}):raise ValueError('Secret files cannot be read into model context.')
        return path
    def read(self,path):
        path=self.checked(path)
        if not path.is_file() or path.stat().st_size>2_000_000:raise ValueError('Choose a text/document file under 2 MB.')
        if path.suffix.lower()=='.pdf':
            from pypdf import PdfReader
            text='\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
        elif path.suffix.lower()=='.docx':
            from docx import Document
            text='\n'.join(p.text for p in Document(path).paragraphs)
        else:text=path.read_text(encoding='utf-8-sig')
        if looks_secret(text):raise ValueError('This file appears to contain credentials; it will not enter model context.')
        return {'ok':True,'verified':True,'path':str(path),'text':text[:100000],'truncated':len(text)>100000,'untrusted_content':True}
    def search(self,path,query):
        root=self.checked(path);results=[]
        for index,item in enumerate(root.rglob('*')):
            if index>10000:break
            try:
                checked=self.checked(item)
                if checked.is_file() and checked.suffix.lower() in {'.md','.txt','.pdf','.docx'}:
                    if query.casefold() in checked.name.casefold() or query.casefold() in self.read(str(checked))['text'].casefold():results.append(str(checked))
            except (ValueError,OSError,UnicodeError):continue
            if len(results)>=50:break
        return {'ok':True,'verified':True,'files':results,'untrusted_content':True}
    def snapshot(self,path):
        if not path.exists():return None
        if not path.is_file() or path.stat().st_size>20_000_000:raise ValueError('Version snapshots require a file below 20 MB.')
        data=path.read_bytes();version_id=uuid.uuid4().hex[:16];self.versions.mkdir(parents=True,exist_ok=True)
        if os.name=='nt':
            import win32crypt
            stored=b'DPAPI\0'+win32crypt.CryptProtectData(data,'Bilal file version',None,None,None,0)
        else:
            if looks_secret(data.decode('utf-8',errors='ignore')):raise ValueError('Encrypted version storage is required for secret files.')
            stored=b'RAW\0'+data
        (self.versions/version_id).write_bytes(stored)
        self.store.set_setting('version:'+version_id,{'path':str(path),'sha256':hashlib.sha256(data).hexdigest()})
        return version_id
    def write(self,path,content):
        path=self.checked(path,write=True);path.parent.mkdir(parents=True,exist_ok=True)
        previous=self.snapshot(path);payload=content.encode('utf-8');temporary=path.with_name(path.name+'.bilal-'+uuid.uuid4().hex[:8])
        temporary.write_bytes(payload);temporary.replace(path)
        verified=path.read_bytes()==payload
        return {'ok':verified,'verified':verified,'path':str(path),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'version_id':previous,'reply':'File saved and verified.'}
    def copy(self,source,destination,move=False):
        source=self.checked(source);destination=self.checked(destination,write=True)
        if not source.is_file() or source.stat().st_size>50_000_000 or destination.exists():raise ValueError('Copy/move needs a file below 50 MB and a new destination.')
        destination.parent.mkdir(parents=True,exist_ok=True);before=hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source,destination)
        verified=hashlib.sha256(destination.read_bytes()).hexdigest()==before
        if move and verified:source.unlink()
        return {'ok':verified,'verified':verified,'path':str(destination),'reply':'File moved.' if move else 'File copied.'}
    def recycle(self,path):
        path=self.checked(path,write=True)
        if path.is_dir():raise ValueError('Directory deletion is not supported; select individual files for review.')
        version=self.snapshot(path)
        from win32com.shell import shell,shellcon
        code,aborted=shell.SHFileOperation((0,shellcon.FO_DELETE,str(path)+'\0',None,shellcon.FOF_ALLOWUNDO|shellcon.FOF_NOCONFIRMATION|shellcon.FOF_NOERRORUI|shellcon.FOF_SILENT,None,None))
        verified=code==0 and not aborted and not path.exists()
        return {'ok':verified,'verified':verified,'version_id':version,'reply':'Moved to Recycle Bin.' if verified else 'Recycle operation was not verified.'}
    def restore(self,version_id):
        meta=self.store.setting('version:'+version_id)
        if not meta:raise ValueError('Version not found.')
        path=self.checked(meta['path'],write=True);data=(self.versions/version_id).read_bytes()
        if data.startswith(b'DPAPI\0'):
            import win32crypt
            data=win32crypt.CryptUnprotectData(data[6:],None,None,None,0)[1]
        elif data.startswith(b'RAW\0'):data=data[4:]
        else:raise ValueError('Unknown version format.')
        if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Version integrity check failed.')
        self.snapshot(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return {'ok':True,'verified':path.read_bytes()==data,'path':str(path),'reply':'Previous file version restored.'}
