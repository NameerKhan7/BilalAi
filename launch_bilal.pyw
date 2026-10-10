"""Silent Windows entry point; sign-in shortcut runs this with the project venv."""
from pathlib import Path
import os,sys,traceback
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
(ROOT/'logs').mkdir(exist_ok=True)
output=(ROOT/'logs/background.log').open('a',encoding='utf-8',buffering=1)
sys.stdout=output;sys.stderr=output
if sys.stdin is None:sys.stdin=open(os.devnull,'r',encoding='utf-8')
try:
    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(lambda kind,context,message:print('Qt:',message,file=sys.stderr,flush=True))
    from main import main
    main()
except Exception:
    traceback.print_exc()
finally:
    output.flush()
