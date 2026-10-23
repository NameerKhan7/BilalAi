"""Authenticated connectors with draft-bound approval; no model-exposed send tool."""
import base64,json,re
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from urllib.parse import quote
import requests
from memory import LocalState,digest
from secret_store import load_secret
class ConnectionRequired(RuntimeError):pass

def canonical_email(raw):
    msg=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
    if any(part.get_content_disposition()=='attachment' for part in msg.walk()):
        raise ValueError('Attachment sending is not connected; remove attachments and review this plain-text draft again.')
    body=msg.get_body(preferencelist=('plain',)) if msg.is_multipart() else msg
    return {'to':str(msg.get('To','')),'cc':str(msg.get('Cc','')),'bcc':str(msg.get('Bcc','')),
            'from':str(msg.get('From','')),'subject':str(msg.get('Subject','')),
            'body':body.get_content().replace('\r\n','\n').rstrip('\n') if body else ''}

class GmailClient:
    def __init__(self,session=None):self.session=session;self.account_email=None
    def api(self,method,path,body=None,params=None):
        if self.session is None:
            info=load_secret('gmail')
            if not info:raise ConnectionRequired('Connect Gmail in Bilal before using email drafts.')
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import AuthorizedSession
            self.session=AuthorizedSession(Credentials.from_authorized_user_info(info));self.account_email=info.get('bilal_account_email')
        response=self.session.request(method,'https://gmail.googleapis.com/gmail/v1/users/me/'+path,
                                      json=body,params=params,timeout=15)
        if response.status_code>=400:raise RuntimeError(f'Gmail request failed (HTTP {response.status_code}); no success is assumed.')
        return response.json()
    def create(self,to,subject,body):
        if '\r' in to or '\n' in to or '\r' in subject or '\n' in subject:raise ValueError('Invalid email headers.')
        addresses=getaddresses([to])
        if not addresses or len(addresses)>20 or any(not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',a) for _,a in addresses):
            raise ValueError('Provide a complete recipient email address; names alone are ambiguous.')
        message=EmailMessage();message['To']=to;message['Subject']=subject;message.set_content(body)
        raw=base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft=self.api('POST','drafts',{'message':{'raw':raw}})
        snapshot=self.get(draft['id'])
        if not snapshot.get('from') and self.account_email:snapshot['from']=self.account_email
        return {'draft_id':draft['id'],'message':snapshot}
    def get(self,draft_id):
        data=self.api('GET','drafts/'+quote(draft_id,safe=''),params={'format':'raw'})
        snapshot=canonical_email(data['message']['raw'])
        if not snapshot.get('from') and self.account_email:snapshot['from']=self.account_email
        return snapshot
    def send(self,draft_id,approved_message):
        message=EmailMessage()
        for key,header in [('to','To'),('cc','Cc'),('bcc','Bcc'),('from','From'),('subject','Subject')]:
            if approved_message.get(key):message[header]=approved_message[key]
        message.set_content(approved_message['body'])
        raw=base64.urlsafe_b64encode(message.as_bytes()).decode()
        # Explicit raw content binds the send to the reviewed snapshot even if the server draft changes in between.
        sent=self.api('POST','drafts/send',{'id':draft_id,'message':{'raw':raw}})
        if not sent.get('id'):raise RuntimeError('Gmail did not return a sent-message receipt.')
        receipt=self.api('GET','messages/'+quote(sent['id'],safe=''),params={'format':'metadata'})
        return {'message_id':sent['id'],'verified':'SENT' in receipt.get('labelIds',[]),
                'reply':'Email sent.' if 'SENT' in receipt.get('labelIds',[]) else 'Gmail accepted the send; its Sent label could not yet be verified.'}

class NotionClient:
    def __init__(self,session=None,token=None):self.session=session or requests.Session();self.token=token
    def api(self,method,path,body=None,params=None):
        token=self.token or (load_secret('notion') or {}).get('token')
        if not token:raise ConnectionRequired('Connect a Notion integration and share the target page with it first.')
        response=self.session.request(method,'https://api.notion.com/v1/'+path,
            headers={'Authorization':'Bearer '+token,'Notion-Version':'2025-09-03'},
            json=body,params=params,timeout=15)
        if response.status_code>=400:raise RuntimeError(f'Notion request failed (HTTP {response.status_code}). Check connection/page access.')
        return response.json()
    def search(self,query):
        results=[];cursor=None
        for _ in range(10):
            body={'query':query,'filter':{'value':'page','property':'object'},'page_size':100}
            if cursor:body['start_cursor']=cursor
            data=self.api('POST','search',body)
            for page in data.get('results',[]):
                title=next((v for v in page.get('properties',{}).values() if v.get('type')=='title'),{})
                results.append({'id':page['id'],'url':page.get('url'),'title':''.join(t.get('plain_text',t.get('text',{}).get('content','')) for t in title.get('title',[]))})
            if not data.get('has_more'):return {'ok':True,'verified':True,'pages':results,'truncated':False}
            next_cursor=data.get('next_cursor')
            if not next_cursor or next_cursor==cursor:break
            cursor=next_cursor
        return {'ok':True,'verified':True,'pages':results,'truncated':True}
    def read(self,page_id):
        text=[];budget=[600];truncated=[False]
        def blocks(block_id,depth=0):
            if depth>5:truncated[0]=True;return
            cursor=None
            while budget[0]>0:
                params={'page_size':100}
                if cursor:params['start_cursor']=cursor
                data=self.api('GET','blocks/'+quote(block_id,safe='')+'/children',params=params)
                for block in data.get('results',[]):
                    budget[0]-=1
                    content=block.get(block.get('type',''),{})
                    line=''.join(t.get('plain_text',t.get('text',{}).get('content','')) for t in content.get('rich_text',[]))
                    if line:text.append(line)
                    if block.get('has_children'):blocks(block['id'],depth+1)
                    if budget[0]<=0:truncated[0]=True;return
                if not data.get('has_more'):return
                nxt=data.get('next_cursor')
                if not nxt or nxt==cursor:truncated[0]=True;return
                cursor=nxt
        blocks(page_id)
        full='\n'.join(text)
        return {'ok':True,'verified':True,'page_id':page_id,'text':full[:18000],'truncated':truncated[0] or len(full)>18000}
    def create_note(self,parent_id,title,body):
        chunks=[body[i:i+1800] for i in range(0,len(body),1800)]
        payload={'parent':{'page_id':parent_id},'properties':{'title':{'type':'title','title':[{'type':'text','text':{'content':title}}]}},
                 'children':[{'object':'block','type':'paragraph','paragraph':{'rich_text':[{'type':'text','text':{'content':part}} for part in chunks]}}]}
        page=self.api('POST','pages',payload)
        actual=self.api('GET','pages/'+quote(page['id'],safe=''))
        stored=next((v for v in actual.get('properties',{}).values() if v.get('type')=='title'),{})
        actual_title=''.join(t.get('plain_text',t.get('text',{}).get('content','')) for t in stored.get('title',[]))
        content=self.read(page['id'])
        verified=actual_title==title and content['text']==body and not content['truncated']
        return {'ok':True,'verified':verified,'page_id':page['id'],'url':page.get('url'),
                'reply':'Created and verified the Notion note.' if verified else 'Notion created the page, but full content verification did not pass.'}

class BusinessWorkflows:
    def __init__(self,state=None,gmail=None,notion=None,power=None):
        self.state=state or LocalState();self.gmail=gmail or GmailClient();self.notion=notion or NotionClient()
        from power_tools import PowerActions
        self.power=power or PowerActions(self.state)
    def draft(self,to,subject,body):
        draft=self.gmail.create(to,subject,body)
        approval=self.state.propose('gmail_send',draft)
        return {'ok':True,'verified':False,'draft_id':draft['draft_id'],'approval_id':approval['id'],
                'reply':'Draft created and read back. It is unsent and awaits your review/approval.','draft':draft['message']}
    def propose_memory(self,key,value):
        if not key.strip() or len(key)>80 or len(value)>2000:raise ValueError('Use a short memory key and value.')
        if re.search(r'password|api.?key|access.?token|refresh.?token|secret',key+' '+value,re.I):
            raise ValueError('Credentials cannot be stored as learned memory.')
        pending=self.state.propose('memory',{'key':key,'value':value})
        return {'ok':True,'approval_id':pending['id'],'reply':'Memory suggestion awaits your confirmation; it has not been learned yet.'}
    def resolve(self,action_id,fingerprint,approve,cancel_event=None):
        row=self.state.claim(action_id,fingerprint);payload=row['payload']
        if not approve:
            self.state.finish(action_id,'rejected');return {'ok':True,'reply':'Rejected. No action was executed.'}
        sending=False
        try:
            if cancel_event is not None and cancel_event.is_set():
                self.state.finish(action_id,'cancelled');return {'ok':False,'reply':'Cancelled before execution.'}
            if row['kind']=='memory':
                self.state.remember_confirmed(payload['key'],payload['value'])
                result={'ok':True,'verified':True,'reply':'Confirmed preference saved locally.'}
            elif row['kind']=='system_power':
                self.power.check_fresh(row)
                sending=True
                result=self.power.execute_approved(row,cancel_event)
            elif row['kind']=='gmail_send':
                actual=self.gmail.get(payload['draft_id'])
                if digest(actual)!=digest(payload['message']):
                    self.state.finish(action_id,'changed')
                    replacement=self.state.propose('gmail_send',{'draft_id':payload['draft_id'],'message':actual})
                    return {'ok':False,'reply':'The draft changed. Review the updated recipient/content before sending.','approval_id':replacement['id']}
                if cancel_event is not None and cancel_event.is_set():
                    self.state.finish(action_id,'cancelled');return {'ok':False,'reply':'Cancelled before sending.'}
                sending=True
                result={'ok':True,**self.gmail.send(payload['draft_id'],payload['message'])}
            else:raise ValueError('Unsupported action.')
            self.state.finish(action_id,'done',result);return result
        except Exception:
            # A timed-out send may already have reached Gmail. Never retry it automatically.
            self.state.finish(action_id,'uncertain' if sending else 'failed')
            if row['kind']=='system_power':
                raise RuntimeError('The power request failed or expired, or its outcome could not be verified. Ask again only after checking the laptop state.') from None
            message='The send outcome could not be verified. Check Gmail Sent before retrying.' if sending else 'The approved action could not be prepared; no email send was attempted. Review the connection and try again.'
            raise RuntimeError(message) from None
