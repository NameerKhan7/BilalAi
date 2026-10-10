"""Open installed Chrome and fixed website/search URLs; no shell commands."""
from pathlib import Path
import os
import subprocess
from urllib.parse import urlencode
from command_types import CommandDecision,RequestResult

HOME_URLS={'google':'https://www.google.com/','youtube':'https://www.youtube.com/','wikipedia':'https://en.wikipedia.org/'}

class BrowserActionError(RuntimeError): pass


def find_chrome():
    candidates=[]
    if os.name=='nt':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for flags in (winreg.KEY_READ,winreg.KEY_READ|winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',0,flags) as key:
                        candidates.append(Path(winreg.QueryValue(key,None)))
                except OSError: pass
    for variable in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
        value=os.environ.get(variable)
        if value: candidates.append(Path(value)/'Google/Chrome/Application/chrome.exe')
    for path in candidates:
        if path.name.lower()=='chrome.exe' and path.is_file(): return path
    raise BrowserActionError('Chrome was not found. Install Chrome or configure it before using browser commands.')


def search_url(site,query):
    if site not in HOME_URLS: raise BrowserActionError('That website is not supported yet.')
    query=query.strip()
    if not query or len(query)>400: raise BrowserActionError('Say the search words clearly, using a shorter request.')
    if site=='google': return 'https://www.google.com/search?'+urlencode({'q':query})
    if site=='youtube': return 'https://www.youtube.com/results?'+urlencode({'search_query':query})
    return 'https://en.wikipedia.org/w/index.php?'+urlencode({'search':query})

class BrowserTools:
    def execute(self,decision:CommandDecision):
        # Local validation applies even if a caller passes a constructed or modified object.
        decision=CommandDecision.model_validate(decision.model_dump())
        if decision.action not in ('open_browser','open_site','web_search'):
            raise BrowserActionError('That request is not a supported browser action.')
        chrome=find_chrome()
        url=None
        if decision.action=='open_site': url=HOME_URLS[decision.site]
        elif decision.action=='web_search': url=search_url(decision.site,decision.query)
        command=[str(chrome)]
        if url: command.extend(['--new-tab',url])
        try:
            subprocess.Popen(command,shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise BrowserActionError('Chrome could not be launched. Try opening Chrome manually.') from exc
        if decision.action=='open_browser': reply='Opened Chrome.'
        elif decision.action=='open_site': reply=f'Opened {decision.site.title()} in Chrome.'
        else: reply=f'Opened a {decision.site.title()} search for "{decision.query}" in Chrome.'
        return RequestResult(reply,'browser',url)
