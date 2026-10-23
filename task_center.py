"""Local task review, artifact search, policy approvals and folder settings."""
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QListWidget,QTextBrowser,QLineEdit,QPushButton,QFileDialog,QCheckBox,QInputDialog,QMessageBox,QLabel)


class TaskCenter(QDialog):
    def __init__(self,runtime,parent=None):
        super().__init__(parent);self.runtime=runtime;self.setWindowTitle('Bilal AI — Tasks and history');self.resize(760,570)
        from ui_styles import DIALOG_STYLE
        self.setStyleSheet(DIALOG_STYLE)
        layout=QVBoxLayout(self);tabs=QTabWidget();layout.addWidget(tabs)
        tasks=QDialog();body=QVBoxLayout(tasks);self.tasks=QListWidget();body.addWidget(self.tasks);self.detail=QTextBrowser();self.detail.setOpenExternalLinks(False);body.addWidget(self.detail)
        self.tasks.currentRowChanged.connect(self.select);buttons=QHBoxLayout()
        for label,action in [('Pause','pause'),('Resume','resume'),('Cancel','cancel')]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,a=action:self.control(a));buttons.addWidget(button)
        stop=QPushButton('Stop all');stop.clicked.connect(runtime.stop_all);buttons.addWidget(stop);body.addLayout(buttons);tabs.addTab(tasks,'Tasks')
        history=QDialog();history_body=QVBoxLayout(history);self.search=QLineEdit();self.search.setPlaceholderText('Search saved answers, drafts and agent output');history_body.addWidget(self.search);self.results=QListWidget();history_body.addWidget(self.results);self.artifact=QTextBrowser();self.artifact.setOpenExternalLinks(False);history_body.addWidget(self.artifact)
        self.search.returnPressed.connect(self.find);self.results.currentRowChanged.connect(self.read_artifact);tabs.addTab(history,'History')
        approvals=QDialog();approve_body=QVBoxLayout(approvals);self.approvals=QListWidget();approve_body.addWidget(self.approvals);self.plan=QTextBrowser();self.plan.setStyleSheet('font-family:Consolas,monospace;');approve_body.addWidget(self.plan)
        self.approvals.currentRowChanged.connect(self.select_approval)
        reveal=QPushButton('Reveal exact payload locally');reveal.clicked.connect(lambda:self.select_approval(self.approvals.currentRow(),True));approve_body.addWidget(reveal)
        edit=QPushButton('Edit deterministic plan and review again');edit.clicked.connect(self.edit_plan);approve_body.addWidget(edit)
        row=QHBoxLayout()
        for label,approve in [('Reject',False),('Approve this exact action',True)]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,a=approve:self.resolve(a));row.addWidget(button)
        approve_body.addLayout(row);tabs.addTab(approvals,'Approvals')
        settings=QDialog();settings_body=QVBoxLayout(settings);self.folders=QListWidget();settings_body.addWidget(self.folders)
        settings_body.addWidget(QLabel('Audio → Groq · requests and relevant observations → Gemini.\nExact pasted snippets stay local. Codex receives only its task and selected artifact.'))
        folder=QPushButton('Allow a folder…');folder.clicked.connect(self.add_folder);settings_body.addWidget(folder)
        remove=QPushButton('Remove selected folder');remove.clicked.connect(self.remove_folder);settings_body.addWidget(remove)
        domains=QPushButton('Set allowed browser domains');domains.clicked.connect(self.change_domains);settings_body.addWidget(domains)
        screen_guard=QPushButton('Edit sensitive window block list');screen_guard.clicked.connect(self.change_screen_guard);settings_body.addWidget(screen_guard)
        chord=QPushButton('Change talk shortcut (restart Bilal to apply)');chord.clicked.connect(self.change_shortcut);settings_body.addWidget(chord)
        workers=QPushButton('Set background worker limit (restart to apply)');workers.clicked.connect(self.change_workers);settings_body.addWidget(workers)
        toggle=QCheckBox('Toggle talk on key press instead of hold (restart to apply)');toggle.setChecked(runtime.store.setting('talk_shortcut',{}).get('toggle',False));toggle.toggled.connect(self.change_toggle);settings_body.addWidget(toggle)
        dry=QCheckBox('Dry run: show planned tool calls without executing');dry.setChecked(runtime.store.setting('dry_run',False));dry.toggled.connect(lambda checked:runtime.store.set_setting('dry_run',checked));settings_body.addWidget(dry)
        audit=QPushButton('Verify audit chain');audit.clicked.connect(lambda:QMessageBox.information(self,'Audit','Audit chain verified.' if runtime.store.verify_audit() else 'Audit integrity failed.'));settings_body.addWidget(audit)
        keys=QPushButton('Set a provider API key in Windows Credential Manager');keys.clicked.connect(self.set_key);settings_body.addWidget(keys)
        migrate=QPushButton('Move legacy .env keys to Windows Credential Manager');migrate.clicked.connect(self.migrate_keys);settings_body.addWidget(migrate)
        self.audit_view=QTextBrowser();self.audit_view.setOpenExternalLinks(False);tabs.addTab(self.audit_view,'Audit');self.audit_view.setPlainText(json.dumps(runtime.store.audit_rows(),indent=2,ensure_ascii=False))
        tabs.addTab(settings,'Settings');self.rows=[];self.approval_rows=[];self.artifacts=[]
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start();self.refresh()
    def refresh(self):
        selected=self.tasks.currentRow();rows=self.runtime.store.tasks()
        labels=[f"{x['state'].replace('_',' ')} · {x['owner']} · {x['goal'][:90]} · {x['id']}" for x in rows]
        if labels!=[self.tasks.item(i).text() for i in range(self.tasks.count())]:
            self.tasks.blockSignals(True);self.tasks.clear();self.tasks.addItems(labels);self.rows=rows;self.tasks.blockSignals(False);self.tasks.setCurrentRow(min(max(0,selected),len(rows)-1))
        pending=self.runtime.policy.pending()
        if [x['id'] for x in pending]!=[x['id'] for x in self.approval_rows]:
            self.approval_rows=pending;self.approvals.clear();self.approvals.addItems([f"L{x['level']} · Task {x['task_id']} · {x['id']}" for x in pending]);self.approvals.setCurrentRow(0)
            if not pending:self.plan.clear()
        self.folders.clear();self.folders.addItems(self.runtime.store.setting('allowed_folders',[]))
    def select(self,index):
        if 0<=index<len(self.rows):
            task=self.runtime.store.task(self.rows[index]['id']);task['steps']=self.runtime.store.steps(task['id']);self.detail.setPlainText(json.dumps(task,ensure_ascii=False,indent=2))
    def control(self,action):
        try:
            row=self.tasks.currentRow()
            if row>=0:getattr(self.runtime.engine,action)(self.rows[row]['id']);self.refresh()
        except (ValueError,RuntimeError) as exc:QMessageBox.information(self,'Task',str(exc))
    def find(self):
        self.artifacts=self.runtime.store.search(self.search.text());self.results.clear();self.results.addItems([x['title']+' · '+x['id'] for x in self.artifacts])
    def read_artifact(self,index):
        if 0<=index<len(self.artifacts):self.artifact.setPlainText(self.artifacts[index]['content'])
    def select_approval(self,index,reveal=False):
        if not 0<=index<len(self.approval_rows):return
        row=self.approval_rows[index];plan=json.loads(row['plan']);context=self.runtime.engine.contexts.get(row['task_id'],{});vault=context.get('literals')
        if vault:
            try:plan=vault.resolve(plan)
            except ValueError:
                self.plan.setPlainText('Local exact text expired. Reject this action and paste the text again for a fresh review.');return
            if not reveal:plan=vault.redact_secrets(plan)
        observations=[json.loads(s['result']) for s in self.runtime.store.steps(row['task_id']) if s['tool'] in {'browser_read','inspect_window'} and s['result']][-1:]
        self.plan.setPlainText(json.dumps(plan,ensure_ascii=False,indent=2)+'\n\nApproval executes only this step; earlier actions are never replayed.'+('\nObserved target context:\n'+json.dumps(observations,ensure_ascii=False,indent=2) if observations else ''))
    def resolve(self,approve):
        index=self.approvals.currentRow()
        if not 0<=index<len(self.approval_rows):return
        row=self.approval_rows[index];typed=None
        if approve and row['level']>=3:
            typed,ok=QInputDialog.getText(self,'Hard confirmation','Type CONFIRM to execute this high-risk action.')
            if not ok:return
        try:self.runtime.approve(row['id'],approve,typed);self.refresh()
        except (ValueError,RuntimeError) as exc:QMessageBox.information(self,'Approval',str(exc))
    def edit_plan(self):
        index=self.approvals.currentRow()
        if not 0<=index<len(self.approval_rows):return
        row=self.approval_rows[index];text,ok=QInputDialog.getMultiLineText(self,'Edit plan','Typed tool calls only. Changes invalidate the previous approval:',json.dumps(json.loads(row['plan']),ensure_ascii=False,indent=2))
        if not ok:return
        try:self.runtime.replace_plan(row['id'],json.loads(text));self.refresh()
        except (ValueError,RuntimeError) as exc:QMessageBox.information(self,'Plan',str(exc))
    def add_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Choose a folder Bilal may read and propose changes in')
        if path:
            roots=self.runtime.store.setting('allowed_folders',[])
            if path not in roots:self.runtime.store.set_setting('allowed_folders',roots+[path])
            self.refresh()
    def remove_folder(self):
        roots=self.runtime.store.setting('allowed_folders',[]);index=self.folders.currentRow()
        if index>=0:self.runtime.store.set_setting('allowed_folders',[x for i,x in enumerate(roots) if i!=index]);self.refresh()
    def change_shortcut(self):
        from hold_to_talk import parse_chord
        text,ok=QInputDialog.getText(self,'Talk shortcut','Use left modifiers, e.g. Ctrl+Shift+Space or Ctrl+Shift:')
        if not ok:return
        try:
            keys=parse_chord(text);stop={0xA2,0xA4,0x08}
            if set(keys)<=stop or stop<=set(keys):raise ValueError('Talk overlaps the stop-all shortcut Ctrl+Alt+Backspace.')
            value=self.runtime.store.setting('talk_shortcut',{});value['keys']=keys;self.runtime.store.set_setting('talk_shortcut',value)
        except ValueError as exc:QMessageBox.information(self,'Shortcut',str(exc))
    def change_workers(self):
        count,ok=QInputDialog.getInt(self,'Background tasks','Concurrent workers:',self.runtime.store.setting('task_concurrency',3),1,8)
        if ok:self.runtime.store.set_setting('task_concurrency',count)
    def change_toggle(self,toggle):
        value=self.runtime.store.setting('talk_shortcut',{'keys':[0xA2,0xA0]});value['toggle']=toggle;self.runtime.store.set_setting('talk_shortcut',value)
    def change_domains(self):
        from urllib.parse import urlparse
        text,ok=QInputDialog.getText(self,'Browser domains','Exact hostnames, comma separated (no wildcard):',text=', '.join(self.runtime.store.setting('allowed_domains',[])))
        if not ok:return
        domains=[x.strip().casefold() for x in text.split(',') if x.strip()]
        if any(urlparse('https://'+x).hostname!=x or '/' in x or ':' in x or '*' in x for x in domains):QMessageBox.information(self,'Domains','Use hostnames such as example.com.');return
        self.runtime.store.set_setting('allowed_domains',domains)
    def change_screen_guard(self):
        from screen_awareness import DEFAULT_BLOCKED
        text,ok=QInputDialog.getText(self,'Sensitive windows','Block titles/processes containing these terms, comma separated:',text=', '.join(self.runtime.store.setting('sensitive_windows',DEFAULT_BLOCKED)))
        if ok:self.runtime.store.set_setting('sensitive_windows',[x.strip().casefold() for x in text.split(',') if x.strip()])
    def set_key(self):
        from provider_keys import NAMES,save_key
        name,ok=QInputDialog.getItem(self,'Provider key','Provider:',sorted(NAMES),0,False)
        if not ok:return
        key,ok=QInputDialog.getText(self,'Provider key','Stored only in Windows Credential Manager:',QLineEdit.EchoMode.Password)
        if ok:
            try:save_key(name,key);QMessageBox.information(self,'Provider','Key saved and read-back verified.')
            except (ValueError,RuntimeError,OSError):QMessageBox.information(self,'Provider','Credential storage failed. The key was not logged.')
    def migrate_keys(self):
        from provider_keys import migrate_env
        try:names=migrate_env();QMessageBox.information(self,'Provider','Migrated: '+(', '.join(names) or 'No legacy keys found.'))
        except (ValueError,RuntimeError,OSError):QMessageBox.information(self,'Provider','Migration failed; legacy keys were retained unless their encrypted copies were verified.')
