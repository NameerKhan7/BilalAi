"""TSK/MEM/SAF: durable task, artifact, history and append-only audit state."""
import json,time,uuid,sqlite3,hashlib
from pathlib import Path
from contextlib import contextmanager
from literal_slots import redact
ROOT=Path(__file__).resolve().parent
STATES={'queued','running','waiting_approval','blocked','done','failed','cancelled','paused','interrupted'}


class TaskStore:
    def __init__(self,path=None):
        self.path=Path(path or ROOT/'data/assistant.sqlite3');self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,goal TEXT,owner TEXT,state TEXT,created REAL,updated REAL,plan TEXT,result TEXT,error TEXT,parent TEXT,dependency TEXT,session_id TEXT);
            CREATE TABLE IF NOT EXISTS task_steps(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT,ordinal INTEGER,tool TEXT,args TEXT,state TEXT,result TEXT,created REAL,updated REAL);
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,task_id TEXT,kind TEXT,title TEXT,content TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS command_history(id INTEGER PRIMARY KEY AUTOINCREMENT,session TEXT,role TEXT,content TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS profiles(name TEXT PRIMARY KEY,content TEXT,updated REAL);
            CREATE TABLE IF NOT EXISTS contacts(id TEXT PRIMARY KEY,name TEXT,email TEXT,notes TEXT,updated REAL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE IF NOT EXISTS tool_approvals(id TEXT PRIMARY KEY,task_id TEXT,plan TEXT,digest TEXT,state TEXT,created REAL,expires REAL,level INTEGER);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created REAL,event TEXT,task_id TEXT,payload TEXT,previous_hash TEXT,hash TEXT);
            CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append only'); END;
            CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append only'); END;
            CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,goal TEXT,owner TEXT,next_run REAL,interval_seconds REAL,weekdays_only INTEGER,enabled INTEGER,created REAL);
            CREATE TABLE IF NOT EXISTS snippets(id TEXT PRIMARY KEY,label TEXT,content TEXT,created REAL);
            CREATE VIRTUAL TABLE IF NOT EXISTS artifact_search USING fts5(artifact_id UNINDEXED,task_id UNINDEXED,title,content);
            ''')
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row;db.execute('PRAGMA busy_timeout=15000')
        try:
            with db:yield db
        finally:db.close()
    def audit(self,event,payload=None,task_id=None):
        text=json.dumps(redact(payload or {}),ensure_ascii=False,sort_keys=True)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');last=db.execute('SELECT hash FROM audit ORDER BY id DESC LIMIT 1').fetchone()
            previous=last[0] if last else '';stamp=time.time()
            digest=hashlib.sha256(json.dumps([stamp,event,task_id,text,previous],ensure_ascii=False).encode()).hexdigest()
            db.execute('INSERT INTO audit(created,event,task_id,payload,previous_hash,hash) VALUES(?,?,?,?,?,?)',(stamp,event,task_id,text,previous,digest))
        return digest
    def audit_rows(self,limit=200):
        with self.db() as db:return [dict(x) for x in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT ?', (min(limit,1000),))]
    def verify_audit(self):
        previous=''
        with self.db() as db:
            for row in db.execute('SELECT * FROM audit ORDER BY id'):
                expected=hashlib.sha256(json.dumps([row['created'],row['event'],row['task_id'],row['payload'],previous],ensure_ascii=False).encode()).hexdigest()
                if row['previous_hash']!=previous or row['hash']!=expected:return False
                previous=row['hash']
        return True
    def create_task(self,goal,owner='bilal',plan=None,parent=None,dependency=None):
        task_id=uuid.uuid4().hex[:12];now=time.time()
        with self.db() as db:db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(task_id,redact(goal),owner,'queued',now,now,json.dumps(redact(plan or [])),None,None,parent,dependency,None))
        self.audit('task.created',{'owner':owner,'goal':goal},task_id);return task_id
    def task(self,task_id):
        with self.db() as db:row=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        if row is None:raise ValueError('Task not found.')
        result=dict(row);result['plan']=json.loads(result['plan']);result['result']=json.loads(result['result']) if result['result'] else None;return result
    def tasks(self,states=None,limit=100):
        with self.db() as db:
            if states:rows=db.execute('SELECT * FROM tasks WHERE state IN ('+','.join('?' for _ in states)+') ORDER BY created DESC LIMIT ?',(*states,min(limit,1000)))
            else:rows=db.execute('SELECT * FROM tasks ORDER BY created DESC LIMIT ?',(min(limit,1000),))
            return [self.task(row['id']) for row in list(rows)]
    def set_state(self,task_id,state,result=None,error=None,force=False):
        if state not in STATES:raise ValueError('Unknown task state.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT state FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not old:raise ValueError('Task not found.')
            if not force and old[0] in {'cancelled','done','failed'} and old[0]!=state:return False
            db.execute('UPDATE tasks SET state=?,updated=?,result=COALESCE(?,result),error=? WHERE id=?',(state,time.time(),json.dumps(redact(result)) if result is not None else None,redact(error) if error else None,task_id))
        self.audit('task.'+state,{'error':error},task_id)
        return True
    def recover(self):
        running=self.tasks(['running','queued','paused'])
        for task in running:self.set_state(task['id'],'interrupted',error='Process stopped; explicit resume required.')
        return running
    def step(self,task_id,tool,args,ordinal):
        now=time.time()
        with self.db() as db:cursor=db.execute('INSERT INTO task_steps(task_id,ordinal,tool,args,state,created,updated) VALUES(?,?,?,?,?,?,?)',(task_id,ordinal,tool,json.dumps(redact(args)),'running',now,now));return cursor.lastrowid
    def finish_step(self,step_id,result):
        state='done' if result.get('ok') and (result.get('verified') is True or result.get('step_verified') is True) else ('blocked' if result.get('approval_id') else 'failed')
        with self.db() as db:db.execute('UPDATE task_steps SET state=?,result=?,updated=? WHERE id=?',(state,json.dumps(redact(result)),time.time(),step_id))
        return state
    def steps(self,task_id):
        with self.db() as db:return [dict(x) for x in db.execute('SELECT * FROM task_steps WHERE task_id=? ORDER BY ordinal,id',(task_id,))]
    def artifact(self,task_id,content,kind='text',title='Result'):
        artifact_id=uuid.uuid4().hex[:16];content=redact(content)
        with self.db() as db:
            db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?)',(artifact_id,task_id,kind,title,content,time.time()))
            db.execute('INSERT INTO artifact_search VALUES(?,?,?,?)',(artifact_id,task_id,title,content))
        return artifact_id
    def get_artifact(self,artifact_id):
        with self.db() as db:row=db.execute('SELECT * FROM artifacts WHERE id=?',(artifact_id,)).fetchone()
        if not row:raise ValueError('Artifact not found.')
        return dict(row)
    def search(self,query,limit=10):
        terms=' AND '.join('"'+t.replace('"','""')+'"' for t in query.split()[:12])
        if not terms:return []
        with self.db() as db:return [dict(x) for x in db.execute('SELECT a.* FROM artifact_search s JOIN artifacts a ON a.id=s.artifact_id WHERE artifact_search MATCH ? ORDER BY rank LIMIT ?',(terms,min(limit,50)))]
    def history(self,session='default',limit=12):
        with self.db() as db:rows=list(db.execute('SELECT role,content FROM command_history WHERE session=? ORDER BY id DESC LIMIT ?',(session,limit)))
        return [{'role':x['role'],'text':x['content']} for x in reversed(rows)]
    def remember_turn(self,role,content,session='default'):
        with self.db() as db:db.execute('INSERT INTO command_history(session,role,content,created) VALUES(?,?,?,?)',(session,role,redact(content),time.time()))
    def setting(self,key,default=None):
        with self.db() as db:row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set_setting(self,key,value):
        with self.db() as db:db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(redact(value))))
    def profile(self,name,content=None):
        if content is not None:
            with self.db() as db:db.execute('INSERT INTO profiles VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET content=excluded.content,updated=excluded.updated',(name,json.dumps(redact(content)),time.time()))
        with self.db() as db:row=db.execute('SELECT content FROM profiles WHERE name=?',(name,)).fetchone()
        return json.loads(row[0]) if row else None
    def profiles(self):
        with self.db() as db:return {r['name']:json.loads(r['content']) for r in db.execute('SELECT * FROM profiles')}
    def put_contact(self,name,email,notes=''):
        from contextual_input import validate_detail
        validate_detail('email',email);contact_id=uuid.uuid4().hex[:12]
        with self.db() as db:db.execute('INSERT INTO contacts VALUES(?,?,?,?,?)',(contact_id,name,email,redact(notes),time.time()))
        return contact_id
    def contacts(self,name=''):
        with self.db() as db:return [dict(x) for x in db.execute('SELECT * FROM contacts WHERE name LIKE ? ORDER BY name',('%'+name+'%',))]
