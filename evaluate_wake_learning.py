"""Evaluate confirmed examples; never silently change a deployed wake model."""
import argparse,json
from pathlib import Path
from wake_learning import WakeExamples
def evaluate(directory):
    from wakeword import load_detector,score_wav,load_settings
    reviewed,invalid=WakeExamples(directory).reviewed()
    samples=[row for row in reviewed if row.get('session')]
    if not samples:return {'status':'needs_labelled_samples','samples':0,'invalid_reviewed_count':len(invalid),'settings_changed':False}
    settings=load_settings();threshold=settings['threshold'];frames=settings.get('consecutive_frames',2)
    detector=load_detector();rows=[]
    for sample in samples:
        score=score_wav(detector,Path(directory)/(sample['id']+'.wav'),frames)
        rows.append({'id':sample['id'],'label':sample['label'],'session':sample.get('session'),'score':score})
    positives=[r for r in rows if r['label']=='positive'];negatives=[r for r in rows if r['label']=='negative']
    sessions={r['session'] for r in rows if r['session']}
    balanced=[session for session in sessions if sum(r['session']==session for r in positives)>=2 and sum(r['session']==session for r in negatives)>=2]
    sufficient=len(positives)>=10 and len(negatives)>=10 and len(balanced)>=2
    return {'status':'evaluated' if sufficient else 'needs_more_independent_examples',
            'threshold':threshold,'consecutive_frames':frames,'balanced_sessions':len(balanced),'invalid_reviewed_count':len(invalid),
            'positive_count':len(positives),'negative_count':len(negatives),'sessions':len(sessions),
            'positive_hits':sum(r['score']>=threshold for r in positives),
            'negative_hits':sum(r['score']>=threshold for r in negatives),
            'rows':rows,'settings_changed':False,
            'note':'Human-reviewed labels only. This is evaluation, not automatic training or promotion. Use fresh session-held-out examples before changing a model.'}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent/'data/wake_examples')
    args=parser.parse_args();result=evaluate(args.directory)
    args.directory.mkdir(parents=True,exist_ok=True)
    (args.directory/'evaluation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
