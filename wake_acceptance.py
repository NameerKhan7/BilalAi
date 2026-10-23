"""Fresh independent evidence is required before enabling wake activation."""
import json,time
from pathlib import Path


def accepted(path=None):
    path=Path(path or Path(__file__).resolve().parent/'data/wake_acceptance.json')
    try:
        report=json.loads(path.read_text(encoding='utf-8'))
        return (report.get('independent') is True and 0<=time.time()-float(report['tested_at'])<=30*86400
                and report['positive_trials']>=50 and report['true_activations']/report['positive_trials']>=.90
                and report['negative_seconds']>=3600 and report['false_activations']/(report['negative_seconds']/3600)<1)
    except (OSError,ValueError,KeyError,TypeError,ZeroDivisionError):return False
