"""Direct local commands first; only information questions go to Gemini."""
import re
from command_types import CommandDecision,RequestResult
from browser_tools import BrowserTools
from app_tools import open_app

class RequestCancelled(RuntimeError): pass


def normalize_request(text):
    text=text.strip().rstrip('.!?')
    text=re.sub(r'^(?:hey|hi|hello)\s*,?\s*bilal\b[\s,:.!-]*','',text,flags=re.I)
    return re.sub(r'^(?:(?:please|can you|could you|would you)\s+)+','',text,flags=re.I).strip()


def app_command(text):
    text=normalize_request(text)
    match=re.fullmatch(r'(?:open|launch|start|run)\s+(?:the\s+)?(?:google\s+)?(notion|spotify|chrome)(?:\s+(?:app|application|browser))?',text,re.I)
    if not match:
        match=re.fullmatch(r'(notion|spotify|chrome)\s+(?:kholo|open karo|chalao)',text,re.I)
    return match.group(1).lower() if match else None


def browser_command(text):
    text=normalize_request(text)
    match=re.fullmatch(r'(?:open|go to)\s+(google|youtube|wikipedia)(?:\s+in\s+(?:google\s+)?chrome(?:\s+browser)?)?',text,re.I)
    if match: return CommandDecision(action='open_site',site=match.group(1).lower())
    text=re.sub(r'\s+(?:in|using)\s+(?:google\s+)?chrome(?:\s+browser)?$','',text,flags=re.I)
    match=re.fullmatch(r'(?:search|search on)\s+(google|youtube|wikipedia)\s+for\s+(.+)',text,re.I)
    if match: return CommandDecision(action='web_search',site=match.group(1).lower(),query=match.group(2))
    match=re.fullmatch(r'open\s+(google|youtube|wikipedia)\s+and\s+search\s+(?:for\s+)?(.+)',text,re.I)
    if match: return CommandDecision(action='web_search',site=match.group(1).lower(),query=match.group(2))
    match=re.fullmatch(r'search\s+(?:for\s+)?(.+)\s+on\s+(google|youtube|wikipedia)',text,re.I)
    if match: return CommandDecision(action='web_search',site=match.group(2).lower(),query=match.group(1))
    match=re.fullmatch(r'search\s+for\s+(.+)',text,re.I)
    if match: return CommandDecision(action='web_search',site='google',query=match.group(1))
    return None

class RequestProcessor:
    def __init__(self,brain,browser=None,app_opener=None):
        self.brain=brain;self.browser=browser or BrowserTools();self.app_opener=app_opener or open_app

    def handle(self,query,cancel_event=None):
        def check_cancel():
            if cancel_event is not None and cancel_event.is_set(): raise RequestCancelled('Request cancelled.')
        check_cancel()
        app=app_command(query)
        if app:
            result=RequestResult(self.app_opener(app),'app')
        else:
            browser=browser_command(query)
            if browser:
                check_cancel();result=self.browser.execute(browser)
            elif re.match(r'^(?:open|launch|run|close|delete|remove|send|install|uninstall|play)\b',normalize_request(query),re.I):
                result=RequestResult('I can open Notion, Spotify and Chrome, or search Google, YouTube and Wikipedia. That other command is not connected yet.','unsupported')
            else:
                history=list(self.brain.history)
                answer=self.brain.ask(query)
                if cancel_event is not None and cancel_event.is_set():
                    self.brain.history=history;raise RequestCancelled('Request cancelled.')
                return RequestResult(answer,'answer')
        self.brain.remember(query,result.reply)
        return result
