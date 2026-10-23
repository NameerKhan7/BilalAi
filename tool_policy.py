"""SAF-1/2/4/5: one explicit, logged decision before a tool executes."""
from dataclasses import dataclass,field
from pathlib import Path
import json,time,uuid,hashlib
from literal_slots import LiteralVault


@dataclass(frozen=True)
class ToolSpec:
    name:str
    level:int=0
    timeout:float=20.
    mutates:bool=False
    idempotent:bool=False
    external:bool=False
    path_fields:tuple=()
    capability:str=''
    description:str=''


@dataclass
class ToolContext:
    task_id:str='interactive'
    approval_id:str|None=None
    untrusted_observation:bool=False
    dry_run:bool=False
    capture_requested:bool=False
    force_review:bool=False
    window_target:dict|None=None
    literals:LiteralVault=field(default_factory=LiteralVault)


class PolicyGate:
    def __init__(self,store):self.store=store
    def fingerprint(self,plan):return hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    def request(self,task_id,plan,level=2):
        signature=self.fingerprint(plan)
        with self.store.db() as db:
            old=db.execute("SELECT id FROM tool_approvals WHERE task_id=? AND digest=? AND level>=? AND expires>? AND state='pending'",(task_id,signature,level,time.time())).fetchone()
            if old:return old[0]
            approval_id=uuid.uuid4().hex[:16]
            db.execute('INSERT INTO tool_approvals VALUES(?,?,?,?,?,?,?,?)',(approval_id,task_id,json.dumps(plan),signature,'pending',time.time(),time.time()+600,level))
        self.store.audit('approval.requested',{'approval_id':approval_id,'plan':plan,'level':level},task_id)
        return approval_id
    def pending(self):
        with self.store.db() as db:
            db.execute("UPDATE tool_approvals SET state='expired' WHERE state='pending' AND expires<?",(time.time(),))
            return [dict(x) for x in db.execute("SELECT * FROM tool_approvals WHERE state='pending' ORDER BY created")]
    def trusted_business_decision(self,row,approve):
        if row.get('kind') not in {'memory','gmail_send','system_power'}:raise ValueError('Unregistered trusted approval action.')
        self.store.audit('policy.allowed' if approve else 'policy.rejected',{'tool':row['kind'],'level':1 if row['kind']=='memory' else 2,'approval_id':row['id'],'origin':'human approval card'})
    def resolve(self,approval_id,approve,typed_confirmation=None):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM tool_approvals WHERE id=?',(approval_id,)).fetchone()
            if not row or row['state']!='pending' or row['expires']<time.time():raise ValueError('Approval expired or already used.')
            if approve and row['level']>=3 and typed_confirmation!='CONFIRM':raise ValueError('Type CONFIRM for this high-risk action.')
            db.execute('UPDATE tool_approvals SET state=? WHERE id=?',('approved' if approve else 'rejected',approval_id))
        self.store.audit('approval.approved' if approve else 'approval.rejected',{'approval_id':approval_id,'level':row['level']},row['task_id'])
        return row['task_id']
    def consume(self,approval_id,task_id,call,level=2):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM tool_approvals WHERE id=?',(approval_id,)).fetchone()
            if not row or row['task_id']!=task_id or row['state']!='approved' or row['expires']<time.time() or row['level']<level:return False
            plan=json.loads(row['plan'])
            if self.fingerprint(plan)!=row['digest'] or call not in plan:return False
            # Remove one approved step atomically. Other steps keep the same exact approval.
            plan.remove(call)
            db.execute('UPDATE tool_approvals SET plan=?,digest=?,state=? WHERE id=?',(json.dumps(plan),self.fingerprint(plan),'approved' if plan else 'consumed',approval_id))
        self.store.audit('approval.consumed',{'approval_id':approval_id,'call':call},task_id);return True
    def decide(self,spec,args,context):
        if context.window_target and spec.name not in {'request_window_handoff','request_input','task_status','list_windows','inspect_window','activate_control','enter_text','window_action','selected_browser_state','selected_browser_open_gmail','selected_gmail_search'}:
            self.store.audit('policy.denied',{'tool':spec.name,'reason':'outside handed-over window scope'},context.task_id)
            return {'ok':False,'verified':False,'error':'This task is limited to the handed-over window. Use selected-browser or observed window tools; do not open another browser/profile or use another account connector.'}
        call={'tool':spec.name,'args':context.literals.mask(args)}
        resolved=context.literals.resolve(args)
        level=spec.level
        if context.force_review:level=max(level,2)
        if spec.name=='window_action' and resolved.get('action')=='close':level=max(level,2)
        if context.untrusted_observation and spec.mutates:level=max(level,2)
        if spec.name!='propose_plan' and context.literals.contains_secret(args):level=max(level,2)
        allowed_roots=self.store.setting('allowed_folders',[])
        for key in spec.path_fields:
            if key not in resolved:continue
            path=Path(resolved[key]).expanduser().resolve()
            if not any(path==Path(root).resolve() or Path(root).resolve() in path.parents for root in allowed_roots):
                self.store.audit('policy.denied',{'tool':spec.name,'reason':'outside allowed folders'},context.task_id)
                return {'ok':False,'verified':False,'error':'That path is outside the allowed folders. Add it in Settings first.'}
        if spec.name.startswith('screen_') and not context.capture_requested:
            self.store.audit('policy.denied',{'tool':spec.name,'reason':'screen not summoned'},context.task_id)
            return {'ok':False,'error':'Screen capture requires a visible user-triggered capture session.'}
        if context.dry_run:
            self.store.audit('policy.dry_run',{'call':call,'level':level},context.task_id)
            return {'ok':True,'verified':True,'dry_run':True,'plan':call,'level':level,'reply':'Dry run only; nothing executed.'}
        if level>=2 and not (context.approval_id and self.consume(context.approval_id,context.task_id,call,level)):
            approval_id=self.request(context.task_id,[call],level)
            self.store.audit('policy.waiting_approval',{'tool':spec.name,'level':level,'approval_id':approval_id},context.task_id)
            return {'ok':False,'approval_id':approval_id,'policy_approval':True,'level':level,'reply':'Approval required. Review the exact action in Bilal.'}
        self.store.audit('policy.allowed',{'tool':spec.name,'level':level,'approval_id':context.approval_id},context.task_id)
        return None


LEGACY_SPECS={}
for name in ['list_apps','list_windows','inspect_window','media_status','web_search','read_webpage','prayer_times','request_input']:
    LEGACY_SPECS[name]=ToolSpec(name,external=name in {'web_search','read_webpage','prayer_times'},idempotent=True)
for name in ['launch_app','browser_search','open_site','open_url','spotify_play']:
    LEGACY_SPECS[name]=ToolSpec(name,mutates=True)
for name in ['enter_text','activate_control','gmail_create_draft','notion_create_note']:
    LEGACY_SPECS[name]=ToolSpec(name,level=1,mutates=True,external=name in {'gmail_create_draft','notion_create_note'})
for name in ['notion_search','notion_read']:LEGACY_SPECS[name]=ToolSpec(name,external=True,idempotent=True)
for name in ['propose_memory','request_system_power']:LEGACY_SPECS[name]=ToolSpec(name,level=1,description='Proposal only; separate trusted approval executor.')
LEGACY_SPECS['window_action']=ToolSpec('window_action',level=1,mutates=True)
LEGACY_SPECS['clipboard_read']=ToolSpec('clipboard_read',idempotent=True)
LEGACY_SPECS['clipboard_write']=ToolSpec('clipboard_write',level=1,mutates=True)
for name in ('media_control','system_volume'):LEGACY_SPECS[name]=ToolSpec(name,mutates=True)
for name in ('selected_browser_state','selected_browser_open_gmail','selected_gmail_search'):LEGACY_SPECS[name]=ToolSpec(name,idempotent=True)
for name in ('browser_tabs','browser_read'):LEGACY_SPECS[name]=ToolSpec(name,idempotent=True,external=True)
for name in ('browser_open','browser_fill','browser_click'):LEGACY_SPECS[name]=ToolSpec(name,level=1,mutates=True,external=True)
