"""Install/remove only Bilal's current-user desktop-background context menu."""
from pathlib import Path
import argparse
KEY=r'Software\Classes\DesktopBackground\Shell\BilalAIHandoff'


def install(root=None):
    import winreg
    root=Path(root or Path(__file__).resolve().parent).resolve();python=root/'venv/Scripts/pythonw.exe';launcher=root/'launch_bilal.pyw'
    if not python.is_file() or not launcher.is_file():raise ValueError('Install the Bilal environment before adding its desktop menu.')
    command='"'+str(python)+'" "'+str(launcher)+'" --handoff'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,KEY) as key:
        winreg.SetValueEx(key,'',0,winreg.REG_SZ,'Give control to Bilal');winreg.SetValueEx(key,'Icon',0,winreg.REG_SZ,str(python))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,KEY+r'\command') as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,command)
    return command


def remove():
    import winreg
    for path in (KEY+r'\command',KEY):
        try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)
        except FileNotFoundError:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--remove',action='store_true');args=parser.parse_args()
    if args.remove:remove();print('Bilal desktop menu removed.')
    else:install();print('Give control to Bilal added to the current-user desktop context menu.')
