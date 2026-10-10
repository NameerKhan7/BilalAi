"""BilalAI's Gemini text-answer client with bounded session conversation."""
from pathlib import Path
import os
from dotenv import dotenv_values
from google import genai
from google.genai import types,errors
ROOT=Path(__file__).resolve().parent
DEFAULT_MODEL='gemini-3.5-flash-lite'
SYSTEM_PROMPT='''You are BilalAI, Nameer's practical personal Windows assistant. Answer naturally and briefly, usually in one to three sentences. Match the user's language, including natural Urdu-English when appropriate. Use recent conversation for follow-up questions. This build can record speech, transcribe it and answer questions; local tools separately handle opening supported apps and browser searches; webpage reading and spoken replies are not connected yet. Never claim an action happened unless a local tool result in the conversation confirms it. You give information; local code executes commands. Explain that limitation briefly when such an action is requested. Ask a short clarification when a transcript is ambiguous. Do not pretend uncertain app names are confirmed. Return plain conversational text suitable for later speech playback.'''

class AgentError(RuntimeError):
    """Safe text for the UI; never includes the provider's raw credential errors."""

class AgentBrain:
    def __init__(self,model=None,history_pairs=6):
        if history_pairs<1: raise ValueError('history_pairs must be positive.')
        self.model=model or os.environ.get('GEMINI_MODEL') or dotenv_values(ROOT/'.env').get('GEMINI_MODEL') or DEFAULT_MODEL
        self.history_pairs=history_pairs
        self.history=[]

    def clear(self):
        self.history.clear()

    def ask(self,query):
        query=query.strip()
        if not query: raise AgentError('Enter or transcribe a question first.')
        if len(query)>4000: raise AgentError('Please keep this test request under 4,000 characters.')
        values=dotenv_values(ROOT/'.env')
        key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY')
        if not key: raise AgentError('Add GEMINI_API_KEY to your local .env file.')
        contents=[types.Content(role=item['role'],parts=[types.Part.from_text(text=item['text'])]) for item in self.history]
        contents.append(types.Content(role='user',parts=[types.Part.from_text(text=query)]))
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,max_output_tokens=512,temperature=.3,
                                          automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        try:
            with genai.Client(api_key=key,http_options={'timeout':20000}) as client:
                response=client.models.generate_content(model=self.model,contents=contents,config=config)
        except errors.APIError as exc:
            if exc.code in (401,403):
                message='Gemini rejected the key or project access. Check GEMINI_API_KEY in your local .env.'
            elif exc.code==429:
                message='Gemini quota is exhausted. Try later or check the project limits in AI Studio.'
            elif exc.code==404:
                message='The Gemini model is unavailable. Check GEMINI_MODEL in your local .env.'
            else:
                message=f'Gemini could not answer this request (HTTP {exc.code}). Try again.'
            raise AgentError(message) from exc
        except Exception as exc:
            raise AgentError('Could not reach Gemini or the request timed out. Check your connection and retry.') from exc
        text=getattr(response,'text',None)
        if not isinstance(text,str) or not text.strip():
            raise AgentError('Gemini returned no answer. Try rephrasing the request.')
        text=text.strip()
        self.remember(query,text)
        return text

    def remember(self,query,reply):
        self.history.extend([{'role':'user','text':query},{'role':'model','text':reply}])
        self.history=self.history[-2*self.history_pairs:]
