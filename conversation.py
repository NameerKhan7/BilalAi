"""Conversation presence policy, separate from model reasoning and audio I/O."""
import re

FOLLOWUP_WAIT_SECONDS=15.0


def is_conversation_end(text):
    words=re.sub(r"[^\w\s]",'',text.casefold())
    words=re.sub(r'\s+',' ',words).strip()
    words=re.sub(r'^(?:okay|ok|all right|alright)\s+','',words)
    return words in {'we are done',"were done",'we are done for now',"im done",'i am done','done','thats all','that is all',
        'goodbye','goodbye bilal','bye bilal','stop listening','end conversation',
        'end the conversation','thanks thats all','thank you thats all'}


class ConversationSession:
    def __init__(self):self.active=False;self.held=False
    def begin(self):self.active=True
    def end(self):self.active=False
    @property
    def keep_visible(self):return self.active or self.held
