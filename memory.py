"""Local, persistent user-confirmed memory and one-shot pending approvals."""
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,sqlite3,time,uuid
ROOT=Path(__file__).resolve().parent
def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

class LocalState:
    def __init__(self,path=None,recover_inflight=False):
        self.path=Path(path or ROOT/'data/assistant.sqlite3');self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS memories (key TEXT PRIMARY KEY,value TEXT NOT NULL,updated REAL); CREATE TABLE IF NOT EXISTS pending (id TEXT PRIMARY KEY,kind TEXT,payload TEXT,digest TEXT,status TEXT,created REAL,result TEXT);')
            if recover_inflight:db.execute("UPDATE pending SET status='uncertain' WHERE status='executing'")
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
    def memories(self):
        with self.db() as db:return {r['key']:r['value'] for r in db.execute('SELECT key,value FROM memories ORDER BY key')}
    def remember_confirmed(self,key,value):
        if not key.strip() or len(key)>80 or len(value)>2000:raise ValueError('Memory needs a short key and value.')
        with self.db() as db:db.execute('INSERT INTO memories VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated=excluded.updated',(key,value,time.time()))
    def propose(self,kind,payload):
        if kind not in {'memory','gmail_send'}:raise ValueError('Unsupported approval type.')
        action_id=uuid.uuid4().hex;fingerprint=digest(payload)
        with self.db() as db:db.execute('INSERT INTO pending VALUES (?,?,?,?,?,?,NULL)',(action_id,kind,json.dumps(payload),fingerprint,'pending',time.time()))
        return self.get(action_id)
    def get(self,action_id):
        with self.db() as db:r=db.execute('SELECT * FROM pending WHERE id=?',(action_id,)).fetchone()
        if r is None:raise ValueError('That approval no longer exists.')
        row=dict(r);row['payload']=json.loads(row['payload']);return row
    def pending(self):
        with self.db() as db:ids=[r[0] for r in db.execute("SELECT id FROM pending WHERE status='pending' ORDER BY created")]
        return [self.get(i) for i in ids]
    def claim(self,action_id,fingerprint):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT * FROM pending WHERE id=?',(action_id,)).fetchone()
            if not r or r['status']!='pending' or r['digest']!=fingerprint or digest(json.loads(r['payload']))!=fingerprint:
                raise ValueError('Approval is stale, changed, or already used. Review it again.')
            db.execute("UPDATE pending SET status='executing' WHERE id=?",(action_id,))
        return self.get(action_id)
    def finish(self,action_id,status,result=None):
        with self.db() as db:db.execute('UPDATE pending SET status=?,result=? WHERE id=?',(status,json.dumps(result),action_id))
