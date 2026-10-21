"""Local readiness checks. No account API requests, sends, notes or training."""
import argparse,json,os,subprocess,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from runtime_paths import worker_python
ROOT=Path(__file__).resolve().parent


def startup_status():
    if os.name!='nt':return {'status':'windows_required'}
    import pythoncom
    from win32com.client import Dispatch
    from startup_windows import shortcut_path
    target=shortcut_path()
    if not target.is_file():return {'status':'not_installed'}
    pythoncom.CoInitialize();shell=None;link=None
    try:
        shell=Dispatch('WScript.Shell');link=shell.CreateShortcut(str(target))
        expected=ROOT/'venv/Scripts/pythonw.exe'
        correct=os.path.normcase(os.path.abspath(link.TargetPath))==os.path.normcase(str(expected)) and link.Arguments=='"'+str(ROOT/'launch_bilal.pyw')+'"' and os.path.normcase(os.path.abspath(link.WorkingDirectory))==os.path.normcase(str(ROOT))
        return {'status':'configured' if correct and expected.is_file() else 'repair_needed','sign_in_field_test':'pending'}
    finally:link=None;shell=None;pythoncom.CoUninitialize()


def collect(run_tests=False):
    from wake_learning import WakeExamples
    from wakeword import load_settings
    from secret_store import path_for
    from PySide6.QtTextToSpeech import QTextToSpeech
    reviewed,invalid=WakeExamples().reviewed();reviewed=[r for r in reviewed if r.get('session')];sessions={r.get('session') for r in reviewed if r.get('session')}
    counts={label:sum(r['label']==label for r in reviewed) for label in ['positive','negative']}
    balanced=sum(all(sum(r['label']==label and r.get('session')==session for r in reviewed)>=2 for label in counts) for session in sessions)
    training_ready=counts['positive']>=10 and counts['negative']>=10 and balanced>=2
    checks={'wake':{'status':'ready_for_candidate_training' if training_ready else 'needs_reviewed_recordings',**counts,'balanced_sessions':balanced,'invalid_reviewed_count':len(invalid),'policy':load_settings(),'fresh_field_acceptance':'pending'},'accounts':{name:{'status':'stored_not_verified' if path_for(name).is_file() else 'not_connected'} for name in ['gmail','notion']},'physical_voice_acceptance':'pending'}
    try:
        import sounddevice as sd
        sd.check_input_settings(samplerate=16000,channels=1,dtype='int16')
        checks['microphone']={'status':'format_supported','physical_recording_test':'pending'}
    except Exception as exc:checks['microphone']={'status':'unavailable','error_type':type(exc).__name__}
    checks['speech']={'engines':QTextToSpeech.availableEngines(),'speaker_audibility_test':'pending'}
    from wake_verifier import MODEL_DIRECTORY
    checks['wake_verifier']={'status':'installed' if all((MODEL_DIRECTORY/name).is_file() for name in ['model.bin','config.json','tokenizer.json','vocabulary.txt']) else 'setup_required','candidate_audio_upload':False}
    try:checks['startup']=startup_status()
    except Exception as exc:checks['startup']={'status':'check_failed','error_type':type(exc).__name__}
    if run_tests:
        start=time.monotonic()
        result=subprocess.run([worker_python(),'-m','unittest','discover','-s','tests','-q'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        checks['automated_tests']={'status':'passed' if result.returncode==0 else 'failed','seconds':round(time.monotonic()-start,2),'summary':(result.stderr+result.stdout)[-2000:]}
    else:checks['automated_tests']={'status':'not_run'}
    return {'checked_at':datetime.now(timezone(timedelta(hours=5),'Asia/Karachi')).isoformat(),'mvp_field_validated':False,'checks':checks,'note':'Simulated tests, configured startup and stored tokens do not establish physical voice or live account write acceptance. No account API was contacted.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tests',action='store_true')
    args=parser.parse_args();report=collect(args.tests)
    output=ROOT/'logs/mvp_readiness.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
