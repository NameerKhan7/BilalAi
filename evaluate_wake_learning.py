"""Evaluate confirmed examples; never silently change a deployed wake model."""
import argparse,json
from pathlib import Path
from wake_learning import WakeExamples
def evaluate(directory):
    from wakeword import load_detector,score_wav
    samples=[s for s in WakeExamples(directory).examples() if s.get('label_source')=='explicit_user_feedback']
    if not samples:return {'status':'needs_labelled_samples','samples':0,'settings_changed':False}
    detector=load_detector();rows=[]
    for sample in samples:
        score=score_wav(detector,Path(directory)/(sample['id']+'.wav'))
        rows.append({'id':sample['id'],'label':sample['label'],'session':sample.get('session'),'score':score})
    positives=[r for r in rows if r['label']=='positive'];negatives=[r for r in rows if r['label']=='negative']
    sessions={r['session'] for r in rows if r['session']}
    sufficient=len(positives)>=10 and len(negatives)>=10 and len(sessions)>=2
    return {'status':'evaluated' if sufficient else 'needs_more_independent_examples',
            'positive_count':len(positives),'negative_count':len(negatives),'sessions':len(sessions),
            'positive_hits_at_080':sum(r['score']>=.8 for r in positives),
            'negative_hits_at_080':sum(r['score']>=.8 for r in negatives),
            'rows':rows,'settings_changed':False,
            'note':'Human-reviewed labels only. This is evaluation, not automatic training or promotion. Use fresh session-held-out examples before changing a model.'}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent/'data/wake_examples')
    args=parser.parse_args();result=evaluate(args.directory)
    args.directory.mkdir(parents=True,exist_ok=True)
    (args.directory/'evaluation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
