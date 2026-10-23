"""Production bridge: voice -> durable queue -> isolated agent/tool instances."""
import json,re
from literal_slots import LiteralVault,looks_secret
from task_store import TaskStore
from task_engine import TaskEngine
from tool_policy import PolicyGate,ToolContext
from capability_tools import CapabilityTools


class TaskRuntime:
    def __init__(self,state,on_event=None,store=None,planner=None,brain_factory=None):
        from provider_interfaces import GeminiPlanner
        self.state=state;self.store=store or TaskStore();self.policy=PolicyGate(self.store)
        self.on_event=on_event or (lambda name,data:None);self.brain_factory=brain_factory
        from dom_bridge import DOMBridge
        self.dom=DOMBridge()
        self.engine=TaskEngine(self.store,self.run,planner=planner or GeminiPlanner(),on_event=self.on_event,concurrency=int(self.store.setting('task_concurrency',3)))
    def submit(self,goal,literals=None):
        vault=literals.clone() if literals else LiteralVault()
        if looks_secret(goal):raise ValueError('Paste credentials into the secret slot in Quick Input, then describe the action separately.')
        goal=vault.mask(goal)
        control=self.control_command(goal)
        if control:return control
        project=self.store.setting('active_project')
        task_id=self.engine.submit_command(goal,{'literals':vault,'planner_context':{'recent_turns':self.store.history(limit=8),'literal_slots':vault.descriptors(),'selected_project':self.store.profile(project) if project else None}})
        return {'ok':True,'verified':True,'task_id':task_id,'reply':'Queued. You can give me another task.'}
    def control_command(self,goal):
        text=goal.strip().lower().rstrip('?.!')
        if text in {'stop everything','stop all','cancel all tasks'}:
            self.stop_all();return {'ok':True,'verified':True,'reply':'All tasks stopped. Completed changes remain.'}
        if text in {'what are you doing','what is pending',"what's pending",'task status','show tasks'}:return self.engine.status()
        match=re.fullmatch(r'did (claude|codex) finish',text)
        if match:
            task=next((t for t in self.store.tasks() if t['owner']==match[1]),None)
            return {'ok':True,'verified':True,'reply':match[1].title()+(' is '+task['state'].replace('_',' ')+'.' if task else ' has no recorded task.')}
        match=re.fullmatch(r'(cancel|pause|resume) (?:task )?(.+)',text)
        if match:
            task_id=getattr(self.engine,match[1])(match[2]);return {'ok':True,'verified':True,'task_id':task_id,'reply':'Task '+match[1]+' requested.'}
        return None
    def run(self,task,control,context):
        from agent_core import AgentBrain
        from agent_tools import AgentToolExecutor
        vault=context.get('literals') or LiteralVault()
        if task['owner']=='vision':
            from screen_awareness import answer_frame
            frame=context.pop('frame',None)
            if not frame:raise ValueError('This memory-only frame expired. Request a fresh capture.')
            reply=answer_frame(frame,task['goal'],context.get('grounding',[]));control.checkpoint()
            artifact=self.store.artifact(task['id'],reply,'screen_answer',task['goal'][:100])
            if task.get('parent') and self.store.task(task['parent'])['state']=='blocked':self.store.set_state(task['parent'],'done',result={'ok':True,'verified':True,'artifact_id':artifact,'reply':reply})
            return {'ok':True,'verified':True,'reply':reply,'artifact_id':artifact,'answer_only':True}
        if task['owner'] in {'claude','codex'}:
            from delegation import HeadlessAgents
            artifact=self.store.get_artifact(context['artifact_id']) if context.get('artifact_id') else None
            result=HeadlessAgents(self.store).run(task['owner'],task['goal'],control,artifact)
            result['artifact_id']=self.store.artifact(task['id'],result.pop('content'),'agent_answer',task['owner'].title()+' answer')
            with self.store.db() as db:db.execute('UPDATE tasks SET session_id=? WHERE id=?',(result.get('session_id'),task['id']))
            return result
        tool_context=ToolContext(task_id=task['id'],literals=vault,approval_id=context.get('approval_id'),dry_run=self.store.setting('dry_run',False))
        executor=AgentToolExecutor(state=self.state,policy=self.policy,context=tool_context,capabilities=CapabilityTools(self.store,self.engine,self.policy,tool_context),control=control,dom=self.dom)
        control.cleanups.append(executor.close)
        try:
            if context.get('continuation_plan'):
                plan=context['continuation_plan'];tool_context.force_review=True
                for index in range(context.get('plan_cursor',0),len(plan)):
                    control.checkpoint();call=plan[index];result=executor.execute(call['tool'],call['args'],control.cancel)
                    if result.get('ok') is not True or result.get('verified') is not True:return {**result,'error':result.get('error','The reviewed step was not verified. The plan stopped; earlier steps were not repeated.')}
                    context['plan_cursor']=index+1
                return {'ok':True,'verified':True,'reply':str(len(plan))+' reviewed steps completed and verified.'}
            if context.get('continuation'):
                call=context['continuation']
                result=executor.execute(call['tool'],call['args'],control.cancel)
                # Only this exact reviewed step is resumed. Never replay the
                # entire model run, which could repeat previously completed writes.
                result.setdefault('reply','The reviewed step finished. Check task details for its verified result.')
                if result.get('ok'):
                    result['step_only']=True
                    self.store.artifact(task['id'],json.dumps(vault.mask(result),ensure_ascii=False),'step_result','Reviewed step result')
                return result
            brain=self.brain_factory() if self.brain_factory else AgentBrain(state=self.state,persistent=self.store,trace_enabled=False)
            if self.brain_factory is None:brain.history=self.store.history(limit=12)
            descriptors=vault.descriptors()
            query=task['goal']+('\nLocal exact input slots (use their tokens as literal tool argument values): '+json.dumps(descriptors,ensure_ascii=False) if descriptors else '')
            reply=brain.run(query,executor,cancel_event=control.cancel)
            trace=executor.trace
            self.store.artifact(task['id'],vault.mask(reply),'answer',task['goal'][:100])
            for step in trace:
                result=step['result']
                if result.get('policy_approval'):
                    if result.get('policy_plan'):context['continuation_plan']=result['policy_plan'];context['plan_cursor']=0
                    else:context['continuation']={'tool':step['tool'],'args':step['arguments']}
                    return result
                if result.get('approval_id'):return {**result,'reply':reply,'business_approval':True}
                if result.get('input_request'):return {**result,'reply':reply,'original_goal':task['goal']}
                if result.get('screen_request'):return result
            # Pure answers are complete when the provider returned text. Actions
            # require evidence; opening a page or claiming success is insufficient.
            verified=not trace or (all(s['result'].get('ok') is True and (s['result'].get('verified') is True or s['result'].get('step_verified') is True) for s in trace) and any(s['result'].get('verified') is True for s in trace))
            from tool_policy import LEGACY_SPECS
            from capability_tools import SPECS
            answer_only=all(not (SPECS.get(s['tool']) or LEGACY_SPECS.get(s['tool'])).mutates for s in trace if SPECS.get(s['tool']) or LEGACY_SPECS.get(s['tool']))
            return {'ok':verified,'verified':verified,'reply':reply,'answer_only':answer_only,'error':None if verified else 'The requested effect was not verified.'}
        finally:
            executor.close()
            if executor.close in control.cleanups:control.cleanups.remove(executor.close)
    def approve(self,approval_id,approve,typed=None):
        if approve:
            row=next((r for r in self.policy.pending() if r['id']==approval_id),None)
            if not row:raise ValueError('Approval expired or already used.')
            task=self.store.task(row['task_id']);context=self.engine.contexts.get(task['id'],{})
            if task['state']!='waiting_approval':raise ValueError('This task is no longer waiting for approval.')
            if '[[LIT_' in row['plan']:
                vault=context.get('literals')
                if not vault:raise ValueError('Local exact text expired. Paste it again for a fresh review.')
                vault.resolve(json.loads(row['plan']))
            if not (context.get('continuation') or context.get('continuation_plan')):
                plan=json.loads(row['plan'])
                if '[[LIT_' in row['plan'] or '[REDACTED' in row['plan']:raise ValueError('Local exact text expired on restart. Paste it again for a fresh review.')
                CapabilityTools(self.store).validate_plan(plan)
                self.engine.contexts[task['id']]={'continuation_plan':plan,'plan_cursor':0}
        task_id=self.policy.resolve(approval_id,approve,typed)
        if approve:return self.engine.resume(task_id,approval_id)
        return self.engine.cancel(task_id)
    def replace_plan(self,approval_id,plan):
        row=next((r for r in self.policy.pending() if r['id']==approval_id),None)
        if not row:raise ValueError('Approval is no longer pending.')
        plan=CapabilityTools(self.store).validate_plan(plan);context=self.engine.contexts.setdefault(row['task_id'],{})
        vault=context.setdefault('literals',LiteralVault())
        def slots(value):
            if isinstance(value,str) and looks_secret(value):return vault.add(value,'Edited local secret',True)
            if isinstance(value,dict):return {k:slots(v) for k,v in value.items()}
            if isinstance(value,list):return [slots(v) for v in value]
            return value
        plan=vault.mask(slots(plan));vault.resolve(plan)
        context['continuation_plan']=plan;context['plan_cursor']=0;context.pop('continuation',None)
        with self.store.db() as db:
            db.execute("UPDATE tool_approvals SET state='superseded' WHERE id=? AND state='pending'",(approval_id,))
            db.execute('UPDATE tasks SET plan=? WHERE id=?',(json.dumps(plan),row['task_id']))
        return self.policy.request(row['task_id'],plan,row['level'])
    def stop_all(self):
        self.engine.cancel_all();self.dom.close()
        for row in self.policy.pending():
            try:self.policy.resolve(row['id'],False)
            except ValueError:pass
        for row in self.state.pending():
            try:self.state.claim(row['id'],row['digest']);self.state.finish(row['id'],'cancelled')
            except ValueError:pass
    def close(self):
        self.engine.close()
        if self.dom:self.dom.close()
        for context in self.engine.contexts.values():
            context.pop('frame',None)
            if context.get('literals'):context['literals'].clear()
