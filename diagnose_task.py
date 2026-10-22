"""Summarize one private task trace without replaying any action or API request."""
import argparse,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def summarize(path):
    trace=json.loads(Path(path).read_text(encoding='utf-8-sig'));steps=trace.get('steps',[])
    counts=Counter(step.get('tool','unknown') for step in steps);seen=set();repeats=0;unreadable=0
    for step in steps:
        key=(step.get('tool'),json.dumps(step.get('arguments',{}),sort_keys=True))
        if key in seen:repeats+=1
        seen.add(key);result=step.get('result',{})
        text=result.get('text','').casefold()
        if step.get('tool')=='read_webpage' and (not result.get('ok') or 'trouble accessing google search' in text):unreadable+=1
    return {'file':Path(path).name,'started_at':trace.get('started_at'),'model':trace.get('model'),
        'outcome':trace.get('outcome'),'model_rounds':trace.get('model_rounds'),
        'elapsed_seconds':trace.get('elapsed_seconds'),'provider_http_code':trace.get('provider_http_code'),
        'tool_counts':dict(counts),'repeated_calls':repeats,'unreadable_pages':unreadable,'steps':steps,'request':trace.get('request')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group();source.add_argument('--latest',action='store_true');source.add_argument('--file',type=Path)
    parser.add_argument('--details',action='store_true',help='Show private request/arguments; review before sharing.')
    args=parser.parse_args();path=args.file or ROOT/'logs/agent_latest.json'
    try:report=summarize(path)
    except (OSError,ValueError) as exc:parser.exit(1,'Could not read that task trace ('+type(exc).__name__+').\n')
    print('Trace:',report['file']);print('Started:',report['started_at']);print('Model:',report['model'])
    print('Model rounds:',report['model_rounds'],'Elapsed seconds:',report['elapsed_seconds'],'Provider HTTP:',report['provider_http_code'])
    print('Tools:',report['tool_counts']);print('Repeated calls:',report['repeated_calls'],'Unreadable page results:',report['unreadable_pages'])
    # Outcomes can quote private content; default output deliberately omits their text.
    status='provider failure' if report['outcome']=='provider failure' else ('guard stopped' if str(report['outcome']).startswith('research guard:') else 'recorded')
    print('Outcome status:',status)
    for index,step in enumerate(report['steps'],1):
        result=step.get('result',{});status='blocked' if result.get('stopped_by_guard') else ('ok' if result.get('ok') else 'failed')
        print(f"{index}. {step.get('tool')}: {status}; {step.get('elapsed_ms','?')}ms; text characters={len(result.get('text',''))}")
    if report['provider_http_code']==429:print('Diagnosis: provider quota/rate limit; do not retry in a loop.')
    if report['unreadable_pages']:print('Diagnosis: page retrieval failed or returned an access page, not usable evidence.')
    if report['repeated_calls']:print('Diagnosis: repeated calls; inspect whether any new evidence was obtained.')
    if args.details:
        print('PRIVATE DETAILS — review before sharing.');print('Request:',report['request']);print('Outcome:',report['outcome'])
        for index,step in enumerate(report['steps'],1):print(index,step.get('tool'),step.get('arguments'))


if __name__=='__main__':main()
