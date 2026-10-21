"""Download fixed public model files once. No microphone or audio upload."""
import hashlib,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
REVISION='3d3d5dee26484f91867d81cb899cfcf72b96be6c'
FILES={'config.json':(2227,None),'tokenizer.json':(2128466,None),'vocabulary.txt':(422309,None),
       'model.bin':(145216508,'2a166925539a16005f14ff328359f9b9adb9dc4fb631bb3b227526862e93e2ef')}


def install_file(target,name,size,expected_hash):
    path=target/name
    if path.is_file() and path.stat().st_size==size and (expected_hash is None or hashlib.sha256(path.read_bytes()).hexdigest()==expected_hash):
        print(name+' already installed.',flush=True);return
    partial=target/(name+'.part')
    for attempt in range(3):
        offset=partial.stat().st_size if partial.exists() else 0
        if offset>size:partial.unlink();offset=0
        if offset<size:
            try:
                url='https://huggingface.co/Systran/faster-whisper-base.en/resolve/'+REVISION+'/'+name
                with requests.get(url,headers={'Range':'bytes='+str(offset)+'-'} if offset else {},stream=True,timeout=(20,60)) as response:
                    response.raise_for_status()
                    if offset and response.status_code!=206:offset=0
                    count=offset;reported=count//(8*1024*1024)
                    with partial.open('ab' if offset else 'wb') as output:
                        for chunk in response.iter_content(256*1024):
                            output.write(chunk);count+=len(chunk)
                            if count//(8*1024*1024)>reported:
                                reported=count//(8*1024*1024);print(name+': '+str(round(count/size*100))+'%',flush=True)
            except requests.RequestException:
                if attempt==2:raise RuntimeError('Download interrupted; run setup_wake_verifier.py again to resume.') from None
                time.sleep(1);continue
        if partial.stat().st_size!=size:continue
        if expected_hash and hashlib.sha256(partial.read_bytes()).hexdigest()!=expected_hash:
            partial.unlink();raise RuntimeError('Downloaded model checksum did not match.')
        partial.replace(path);print(name+' installed.',flush=True);return
    raise RuntimeError('Model download incomplete; run setup_wake_verifier.py again to resume.')


def main():
    target=ROOT/'models/wake_asr';target.mkdir(parents=True,exist_ok=True)
    for name,(size,checksum) in FILES.items():install_file(target,name,size,checksum)
    print('Offline wake verifier installed. Restart Bilal to use it.',flush=True)

if __name__=='__main__':main()
