"""QIN-2/4/5: exact payloads remain local; planners receive opaque slots only."""
import re,secrets,threading
from dataclasses import dataclass

SECRET_PATTERN=re.compile(r'(?i)(?:AIza[\w-]{20,}|AQ\.[\w-]{20,}|(?:sk-|gsk_|ntn_|ghp_|github_pat_)[\w-]{12,}|(?:password|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*\S+)')


def looks_secret(text):
    if SECRET_PATTERN.search(text):return True
    for candidate in re.findall(r'(?:\d[ -]?){13,19}',text):
        digits=re.sub(r'\D','',candidate)
        if 13<=len(digits)<=19:
            values=[int(n) for n in digits][::-1]
            if sum((v*2//10+v*2%10) if i%2 else v for i,v in enumerate(values))%10==0:return True
    return False


def redact(value):
    if isinstance(value,str):
        value=SECRET_PATTERN.sub('[REDACTED SECRET]',value)
        return re.sub(r'(?:\d[ -]?){13,19}',lambda m:'[REDACTED SECRET]' if looks_secret(m.group()) else m.group(),value)
    if isinstance(value,dict):return {k:('[REDACTED SECRET]' if re.search(r'(?i)password|api.?key|access.?token|refresh.?token|secret',k) else redact(v)) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [redact(v) for v in value]
    return value


@dataclass(frozen=True)
class Literal:
    token:str
    label:str
    value:str
    secret:bool


class LiteralVault:
    def __init__(self):self.values={};self.lock=threading.RLock()
    def add(self,text,label='Exact text',secret=None):
        if not isinstance(text,str) or not text:raise ValueError('Enter exact text first.')
        if len(text.encode('utf-8'))>2_000_000:raise ValueError('Literal exceeds 2 MB.')
        with self.lock:
            token='[[LIT_'+secrets.token_hex(5).upper()+']]'
            item=Literal(token,redact(label[:100]),text,looks_secret(text) or bool(secret))
            self.values[token]=item
            return token
    def descriptors(self,tokens=None):
        with self.lock:
            return [{'slot':x.token,'label':self.mask(x.label),'secret':x.secret,'characters':len(x.value)} for x in self.values.values() if tokens is None or x.token in tokens]
    def resolve(self,value):
        if isinstance(value,str):
            with self.lock:
                def substitute(match):
                    item=self.values.get(match.group())
                    if item is None:raise ValueError('An exact-input slot is missing or expired.')
                    return item.value
                # A payload may itself contain token-like text. Substitute once
                # in the original argument; never reinterpret a literal's bytes.
                return re.sub(r'\[\[LIT_[A-Z0-9_]+\]\]',substitute,value)
        if isinstance(value,dict):return {k:self.resolve(v) for k,v in value.items()}
        if isinstance(value,list):return [self.resolve(v) for v in value]
        return value
    def mask(self,value):
        if isinstance(value,str):
            with self.lock:
                replacements={item.value:item.token for item in self.values.values()}
                if replacements:
                    pattern='|'.join(re.escape(x) for x in sorted(replacements,key=len,reverse=True))+r'|\[\[LIT_[A-Z0-9_]+\]\]'
                    value=re.sub(pattern,lambda m:m.group() if m.group() in self.values else replacements.get(m.group(),m.group()),value)
            return redact(value)
        if isinstance(value,dict):return {k:self.mask(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [self.mask(v) for v in value]
        return value
    def contains_secret(self,value):
        import json
        text=json.dumps(value,ensure_ascii=False)
        with self.lock:return any(x.secret and (x.token in text or x.value in text) for x in self.values.values()) or looks_secret(text)
    def clear(self):
        with self.lock:self.values.clear()
    def clone(self):
        other=LiteralVault()
        with self.lock:other.values=dict(self.values)
        return other
    def redact_secrets(self,value):
        if isinstance(value,str):
            with self.lock:
                for item in self.values.values():
                    if item.secret:value=value.replace(item.value,'[REDACTED SECRET]')
            return redact(value)
        if isinstance(value,dict):return {k:self.redact_secrets(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [self.redact_secrets(v) for v in value]
        return value
