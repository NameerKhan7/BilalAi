"""Install/remove the current user's Windows sign-in shortcut for Bilal."""
from pathlib import Path
import argparse,json,os
ROOT=Path(__file__).resolve().parent
SHORTCUT_NAME='Bilal AI.lnk'

def shortcut_path():
    if os.name!='nt':raise RuntimeError('Windows startup installation requires Windows.')
    from win32com.shell import shell,shellcon
    return Path(shell.SHGetFolderPath(0,shellcon.CSIDL_STARTUP,None,0))/SHORTCUT_NAME

def configure(remove=False):
    import pythoncom
    from win32com.client import Dispatch
    pythonw=ROOT/'venv/Scripts/pythonw.exe';launcher=ROOT/'launch_bilal.pyw'
    if not remove and (not pythonw.is_file() or not launcher.is_file()):
        raise RuntimeError('Install the virtual environment and launcher first.')
    target=shortcut_path()
    pythoncom.CoInitialize()
    try:
        shell=Dispatch('WScript.Shell')
        link=shell.CreateShortcut(str(target))
        expected_arguments='"'+str(launcher)+'"'
        if target.exists():
            # Never overwrite/remove a different application using the same name.
            if os.path.normcase(link.TargetPath)!=os.path.normcase(str(pythonw)) or link.Arguments!=expected_arguments:
                raise RuntimeError('An unrelated shortcut already uses this name; it was left unchanged.')
        if remove:
            if target.is_file():target.unlink()
            return {'enabled':False,'shortcut':str(target)}
        target.parent.mkdir(parents=True,exist_ok=True)
        link.TargetPath=str(pythonw);link.Arguments=expected_arguments
        link.WorkingDirectory=str(ROOT);link.WindowStyle=7
        link.Description='Bilal AI — hidden local wake listening at Windows sign-in'
        link.Save()
        # Read back the actual persisted shortcut, not just our intended settings.
        saved=shell.CreateShortcut(str(target))
        if os.path.normcase(saved.TargetPath)!=os.path.normcase(str(pythonw)) or saved.Arguments!=expected_arguments:
            raise RuntimeError('Windows did not save the expected startup shortcut.')
        return {'enabled':True,'shortcut':str(target),'target':saved.TargetPath,
                'arguments':saved.Arguments,'working_directory':saved.WorkingDirectory}
    finally:
        # Release COM proxies while the apartment is still initialized.
        saved=None;link=None;shell=None
        pythoncom.CoUninitialize()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--remove',action='store_true')
    args=parser.parse_args()
    print(json.dumps(configure(args.remove),ensure_ascii=True,indent=2))
