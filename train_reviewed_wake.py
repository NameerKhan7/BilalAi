"""Prepare session-held-out training only from human-labelled local examples."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time
from wake_learning import WakeExamples
ROOT=Path(__file__).resolve().parent
def prepare(directory):
    rows=[r for r in WakeExamples(directory).examples() if r.get('label_source')=='explicit_user_feedback' and r.get('session')]
    positives=sum(r['label']=='positive' for r in rows);negatives=sum(r['label']=='negative' for r in rows)
    sessions=sorted({r['session'] for r in rows})
    balanced=[session for session in sessions if sum(r['label']=='positive' and r['session']==session for r in rows)>=2 and sum(r['label']=='negative' and r['session']==session for r in rows)>=2]
    if positives<10 or negatives<10 or len(balanced)<2:
        return {'ready':False,'positive_count':positives,'negative_count':negatives,'sessions':len(sessions),
                'reason':'Need at least 10 reviewed examples per class from at least two sessions containing both classes. No model changed.'}
    stamp=time.strftime('%Y%m%d_%H%M%S');target=ROOT/'training/recordings'/('reviewed_'+stamp)
    target.mkdir(parents=True,exist_ok=False);samples=[]
    for i,row in enumerate(rows):
        source=Path(directory)/(row['id']+'.wav');filename=f'{i:04d}.wav'
        shutil.copy2(source,target/filename)
        samples.append({'file':filename,'number':sessions.index(row['session'])+1,'session':row['session'],
                        'label':'hey_bilal' if row['label']=='positive' else 'hee_haa'})
    (target/'samples.json').write_text(json.dumps({'samples':samples},indent=2),encoding='utf-8')
    return {'ready':True,'session':str(target),'output':str(ROOT/'models/candidates'/stamp),'positive_count':positives,'negative_count':negatives,'sessions':len(sessions)}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=ROOT/'data/wake_examples');parser.add_argument('--train-candidate',action='store_true')
    args=parser.parse_args();result=prepare(args.directory);print(json.dumps(result,indent=2))
    if result['ready'] and args.train_candidate:
        subprocess.run([sys.executable,str(ROOT/'training/train_personalized.py'),'--session',result['session'],'--output',result['output']],check=True,cwd=ROOT)
        print('Candidate trained separately. Fresh microphone validation is required before changing the deployed model.')
