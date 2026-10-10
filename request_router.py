"""Direct local commands first; only information questions go to Gemini."""
import re
from command_types import CommandDecision,RequestResult
from browser_tools import BrowserTools
from app_tools import open_app
from spotify_tools import play_spotify

class RequestCancelled(RuntimeError): pass


def normalize_request(text):
    text=text.strip().rstrip('.!?')
    for _ in range(12):
        previous=text
        text=re.sub(r'^(?:hey|hi|hello)\s*,?\s*bilal\b[\s,:.!-]*','',text,flags=re.I)
        text=re.sub(r'^(?:okay|ok|alright|all right|so|well|actually)[\s,:]+','',text,flags=re.I)
        text=re.sub(r"^(?:i said(?: that)?|i want you to|i need you to|i would like you to|i'd like you to|i am asking you to|i'm asking you to|please|can you|could you|would you)[\s,:]+",'',text,flags=re.I).strip()
        if text==previous: break
    return text


def unresolved_app_request(text):
    text=normalize_request(text)
    # Explanations and negated requests must never become launch actions.
    if re.search(r"\b(?:how to|how do|how can|don't|do not|never)\b",text,re.I): return False
    if re.match(r'^(?:what|why|how|when|where|who|which|explain|describe)\b',text,re.I): return False
    return bool(re.search(r'\b(?:open|launch|run)\s+(?:up\s+)?(?:the\s+)?(?:notion|spotify|chrome|app)\b',text,re.I))


def app_command(text):
    text=normalize_request(text)
    match=re.fullmatch(r'(?:open|launch|start|run)\s+(?:up\s+)?(?:the\s+)?(?:google\s+)?(notion|spotify|chrome)(?:\s+(?:app|application|browser))?(?:\s+and\s+play\s+.+)?',text,re.I)
    if not match:
        match=re.fullmatch(r'(notion|spotify|chrome)\s+(?:kholo|open karo|chalao)',text,re.I)
    return match.group(1).lower() if match else None


def spotify_command(text):
    text=normalize_request(text)
    # The platform can appear before or after the artist, or before the title.
    text,opened_spotify=re.subn(r'^(?:open|launch|start|run)\s+(?:up\s+)?(?:the\s+)?spotify(?:\s+(?:app|application))?\s+and\s+', '', text, count=1, flags=re.I)
    match=re.fullmatch(r'(?:search\s+(?:for\s+)?)?play\s+(.+)',text,re.I)
    if not match: return None
    query,platform_count=re.subn(r'\b(?:on|in|using)\s+(?:the\s+)?spotify(?:\s+app)?\b', '', match.group(1), flags=re.I)
    if platform_count>1 or (not opened_spotify and not platform_count): return None
    query=re.sub(r'\s+',' ',query).strip(' ,')
    query=re.sub(r'^some\s+','',query,flags=re.I).strip()
    return query or None


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
    def __init__(self,brain,browser=None,app_opener=None,spotify_player=None):
        self.brain=brain;self.browser=browser or BrowserTools();self.app_opener=app_opener or open_app
        self.spotify_player=spotify_player or play_spotify

    def handle(self,query,cancel_event=None):
        def check_cancel():
            if cancel_event is not None and cancel_event.is_set(): raise RequestCancelled('Request cancelled.')
        check_cancel()
        playback=spotify_command(query)
        app=app_command(query)
        if playback:
            check_cancel()
            result=RequestResult(self.spotify_player(playback,cancel_event=cancel_event),'app')
        elif app:
            if re.search(r'\band\s+play\b',normalize_request(query),re.I):
                result=RequestResult('Playback is connected for Spotify. Specify what to play on Spotify.','unsupported')
            else:
                result=RequestResult(self.app_opener(app),'app')
        else:
            browser=browser_command(query)
            if browser:
                check_cancel();result=self.browser.execute(browser)
            elif unresolved_app_request(query) or re.match(r'^(?:open|launch|run|close|delete|remove|send|install|uninstall|play)\b',normalize_request(query),re.I):
                result=RequestResult('I can open Notion, Spotify and Chrome, play a song on Spotify, or search Google, YouTube and Wikipedia. That other command is not connected yet.','unsupported')
            else:
                history=list(self.brain.history)
                answer=self.brain.ask(query)
                if cancel_event is not None and cancel_event.is_set():
                    self.brain.history=history;raise RequestCancelled('Request cancelled.')
                return RequestResult(answer,'answer')
        self.brain.remember(query,result.reply)
        return result
