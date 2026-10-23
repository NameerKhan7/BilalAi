"""TSK-1..9: bounded workers, durable tasks, controls, dependencies and schedules."""
import threading,time,queue,json
from concurrent.futures import ThreadPoolExecutor
from literal_slots import LiteralVault


class TaskCancelled(RuntimeError):pass


class TaskControl:
    def __init__(self):self.cancel=threading.Event();self.running=threading.Event();self.running.set();self.cleanups=[];self.interrupted=False
    def checkpoint(self):
        while not self.running.wait(.1):
            if self.cancel.is_set():raise TaskCancelled('Task cancelled.')
        if self.cancel.is_set():raise TaskCancelled('Task cancelled.')
    def stop(self,shutdown=False):
        self.interrupted=shutdown
        self.cancel.set();self.running.set()
        for function in list(self.cleanups):
            try:function()
            except Exception:pass


class TaskEngine:
    def __init__(self,store,runner,planner=None,on_event=None,concurrency=3,recover=True):
        self.store=store;self.runner=runner;self.planner=planner;self.on_event=on_event or (lambda name,data:None)
        self.pool=ThreadPoolExecutor(max_workers=max(1,min(concurrency,8)),thread_name_prefix='bilal-task')
        self.controls={};self.contexts={};self.lock=threading.RLock();self.closed=threading.Event()
        self.interrupted=store.recover() if recover else []
        self.scheduler=threading.Thread(target=self._schedule_loop,daemon=True);self.scheduler.start()
    def submit(self,goal,owner='bilal',plan=None,dependency=None,parent=None,context=None):
        if self.closed.is_set():raise RuntimeError('Task engine is closed.')
        task_id=self.store.create_task(goal,owner,plan,parent,dependency)
        with self.lock:self.controls[task_id]=TaskControl();self.contexts[task_id]=context or {}
        self.pool.submit(self._run,task_id);return task_id
    def submit_command(self,goal,context=None):return self.submit(goal,owner='planner' if self.planner else 'bilal',context=context)
    def _run(self,task_id):
        control=self.controls[task_id];context=self.contexts[task_id]
        try:
            control.checkpoint()
            task=self.store.task(task_id)
            if task['dependency']:
                # Never occupy a worker while waiting for another worker.
                dependency=self.store.task(task['dependency'])
                if dependency['state'] not in {'done','failed','cancelled','blocked','interrupted'}:
                    timer=threading.Timer(.2,lambda:self.pool.submit(self._run,task_id) if not self.closed.is_set() else None);timer.daemon=True;timer.start();return
                if dependency['state']!='done':self.store.set_state(task_id,'blocked',error='Dependency did not complete.');return
            control.checkpoint();self.store.set_state(task_id,'running')
            if task['owner']=='planner':
                planned=self.planner.plan(task['goal'],context.get('planner_context',{}));children=[]
                for index,item in enumerate(planned):
                    dep=item.get('dependency',-1)
                    if not isinstance(dep,int) or not -1<=dep<index:raise ValueError('Invalid dependency in plan.')
                    child_context=dict(context)
                    if 'literals' in context:child_context['literals']=context['literals'].clone()
                    child=self.submit(item['goal'],item.get('owner','bilal'),dependency=children[dep] if dep>=0 else None,parent=task_id,context=child_context);children.append(child)
                result={'ok':True,'verified':True,'tasks':children,'reply':f'{len(children)} task'+('s' if len(children)!=1 else '')+' queued.'}
            else:result=self.runner(task,control,context)
            control.checkpoint()
            if result.get('approval_id'):
                self.store.set_state(task_id,'waiting_approval',result=result);self.on_event('task_approval',{'task_id':task_id,**result});return
            if result.get('input_request'):
                self.store.set_state(task_id,'blocked',result=result,error='Waiting for clarification.');self.on_event('task_input',{'task_id':task_id,**result});return
            if result.get('screen_request'):
                self.store.set_state(task_id,'blocked',result=result,error='Waiting for explicit screen sharing.');self.on_event('task_screen',{'task_id':task_id,**result});return
            if result.get('window_request'):
                self.store.set_state(task_id,'blocked',result=result,error='Waiting for the user to hand over the intended window.');self.on_event('task_window',{'task_id':task_id,**result});return
            verified=result.get('ok') is True and result.get('verified') is True
            state='done' if verified else 'failed'
            if not self.store.set_state(task_id,state,result=result,error=None if verified else result.get('error','Completion was not verified.')):return
            self.on_event('task_finished',{'task_id':task_id,'state':state,'reply':result.get('reply','Task completed.' if verified else 'Task failed.'),'owner':task['owner'],'answer_only':result.get('answer_only',False)})
        except TaskCancelled:
            state='interrupted' if control.interrupted else 'cancelled';self.store.set_state(task_id,state);self.on_event('task_finished',{'task_id':task_id,'state':state,'reply':'Task '+state+'.'})
        except Exception as exc:
            self.store.set_state(task_id,'failed',error=str(exc));self.on_event('task_finished',{'task_id':task_id,'state':'failed','reply':str(exc)[:200]})
        finally:
            if self.store.task(task_id)['state'] in {'done','failed','cancelled'}:
                context.pop('frame',None)
                vault=context.get('literals')
                if vault:vault.clear()
    def resolve_target(self,target='last'):
        tasks=self.store.tasks(limit=100)
        if target.casefold() in {'last','latest','that','the last one'}:
            return next((t for t in tasks if t['owner']!='planner'),tasks[0] if tasks else None)
        matches=[t for t in tasks if t['id'].startswith(target) or target.casefold() in t['goal'].casefold() or target.casefold()==t['owner']]
        active=[t for t in matches if t['state'] in {'queued','running','paused','waiting_approval','blocked'}]
        return (active or matches or [None])[0]
    def cancel(self,target='last'):
        task=self.resolve_target(target)
        if not task:raise ValueError('No matching task.')
        control=self.controls.get(task['id'])
        if control:control.stop()
        self.contexts.get(task['id'],{}).pop('frame',None)
        self.store.set_state(task['id'],'cancelled');self.on_event('task_revoked',{'task_id':task['id']});return task['id']
    def pause(self,target='last'):
        task=self.resolve_target(target)
        if not task or task['id'] not in self.controls:raise ValueError('No active task to pause.')
        self.controls[task['id']].running.clear();self.store.set_state(task['id'],'paused');return task['id']
    def resume(self,target='last',approval_id=None):
        task=self.resolve_target(target)
        if not task:raise ValueError('No matching task.')
        if task['state']=='paused' and task['id'] in self.controls:
            self.controls[task['id']].running.set();self.store.set_state(task['id'],'running');return task['id']
        if task['state'] not in {'interrupted','blocked','waiting_approval','failed'}:raise ValueError('Task is not resumable.')
        context=self.contexts.get(task['id'],{});context=dict(context)
        if approval_id:context['approval_id']=approval_id
        # Restart never replays a possibly completed write without fresh approval.
        if task['state']=='interrupted' and task['plan'] and any(x.get('level',0)>=1 for x in task['plan']):raise ValueError('Interrupted write needs inspection and a new reviewed task.')
        if task['state']=='waiting_approval' and not (context.get('continuation') or context.get('continuation_plan')):
            raise ValueError('This task has no safe continuation. Review its steps before creating a new task.')
        if task['state'] in {'interrupted','failed'} and self.store.steps(task['id']):
            raise ValueError('Inspect recorded effects before restarting this task; writes are never replayed automatically.')
        with self.lock:self.controls[task['id']]=TaskControl();self.contexts[task['id']]=context
        self.store.set_state(task['id'],'queued',force=True);self.pool.submit(self._run,task['id']);return task['id']
    def cancel_all(self):
        for task in self.store.tasks(['queued','running','paused','waiting_approval','blocked'],1000):
            control=self.controls.get(task['id'])
            if control:control.stop()
            context=self.contexts.get(task['id'],{});context.pop('frame',None)
            if context.get('literals'):context['literals'].clear()
            self.store.set_state(task['id'],'cancelled')
            self.on_event('task_revoked',{'task_id':task['id']})
        self.on_event('all_stopped',{'reply':'All tasks stopped.'})
    def status(self):
        tasks=self.store.tasks(['queued','running','paused','waiting_approval','blocked','interrupted'])
        counts={state:sum(t['state']==state for t in tasks) for state in {t['state'] for t in tasks}}
        return {'ok':True,'verified':True,'tasks':tasks,'reply':', '.join(f'{n} {state.replace("_"," ")}' for state,n in counts.items()) or 'Nothing pending.'}
    def schedule(self,goal,when,owner='bilal',interval_seconds=0,weekdays=False):
        import uuid,math
        from datetime import datetime
        stamp=datetime.fromisoformat(when)
        if stamp.tzinfo is None:raise ValueError('Include the timezone offset in the scheduled time.')
        if not math.isfinite(interval_seconds) or interval_seconds and not 60<=interval_seconds<=366*86400:raise ValueError('Recurring schedules must be between one minute and one year apart.')
        schedule_id=uuid.uuid4().hex[:12]
        with self.store.db() as db:db.execute('INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?)',(schedule_id,goal,owner,stamp.timestamp(),interval_seconds,int(weekdays),1,time.time()))
        self.store.audit('schedule.created',{'id':schedule_id,'goal':goal,'when':when});return schedule_id
    def _schedule_loop(self):
        from datetime import datetime,timezone,timedelta
        while not self.closed.wait(1.):
            try:
                with self.store.db() as db:due=[dict(r) for r in db.execute('SELECT * FROM schedules WHERE enabled=1 AND next_run<=?',(time.time(),))]
                for item in due:
                    now=datetime.now(timezone(timedelta(hours=5)))
                    if not item['weekdays_only'] or now.weekday()<5:self.submit(item['goal'],item['owner'])
                    interval=item['interval_seconds'];next_run=item['next_run']
                    if interval:
                        while next_run<=time.time():next_run+=interval
                    with self.store.db() as db:db.execute('UPDATE schedules SET next_run=?,enabled=? WHERE id=?',(next_run,int(bool(interval)),item['id']))
            except Exception as exc:
                self.store.audit('scheduler.failed',{'type':type(exc).__name__})
                self.on_event('scheduler_failed',{'reply':'A scheduled task could not start. Check task history.'})
    def close(self):
        self.closed.set()
        for task in self.store.tasks(['queued','running','paused'],1000):
            control=self.controls.get(task['id'])
            if control:control.stop(shutdown=True)
            self.store.set_state(task['id'],'interrupted',error='Bilal stopped; inspect and explicitly resume.')
        self.pool.shutdown(wait=False,cancel_futures=True)
