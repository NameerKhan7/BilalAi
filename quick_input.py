"""QIN: instructions are intent; pasted payloads are immutable local literals."""
import time,uuid
from literal_slots import LiteralVault,looks_secret
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QPlainTextEdit,QCheckBox,QPushButton,QListWidget,QLabel,QMessageBox


class QuickInput(QDialog):
    def __init__(self,controller,parent=None):
        super().__init__(parent);self.controller=controller;self.vault=LiteralVault();self.setWindowTitle('Bilal AI — Quick Input');self.resize(540,420)
        from ui_styles import DIALOG_STYLE
        self.setStyleSheet(DIALOG_STYLE)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Paste exact text here. Only its reference goes to the planner.'))
        self.label=QLineEdit();self.label.setPlaceholderText('Label, e.g. recipient email or config value');layout.addWidget(self.label)
        self.payload=QPlainTextEdit();self.payload.setPlaceholderText('Exact text (kept locally, never rewritten)');self.payload.setStyleSheet('font-family:Consolas,monospace;');layout.addWidget(self.payload)
        self.secret=QCheckBox('Secret — memory only, never saved in history');layout.addWidget(self.secret)
        self.payload.textChanged.connect(self.sync_pending);self.label.textChanged.connect(self.sync_pending);self.secret.toggled.connect(self.sync_pending)
        add=QPushButton('Add exact text');add.clicked.connect(self.add);layout.addWidget(add);self.slots=QListWidget();layout.addWidget(self.slots)
        self.instruction=QPlainTextEdit();self.instruction.setPlaceholderText('Describe what to do with these snippets, or hold the talk shortcut while this panel stays open.');self.instruction.setMaximumHeight(80);layout.addWidget(self.instruction)
        row=QHBoxLayout();send=QPushButton('Send instruction');send.clicked.connect(self.send);row.addWidget(send);clear=QPushButton('Clear local snippets');clear.clicked.connect(self.clear);row.addWidget(clear);layout.addLayout(row)
    def add(self):
        text=self.payload.toPlainText()
        try:
            token=self.vault.add(text,self.label.text() or 'Exact text',self.secret.isChecked())
            self.slots.addItem(self.vault.descriptors([token])[0]['label']+' · '+token)
            self.controller.literal_vault=self.vault
            if not self.vault.values[token].secret and self.controller.runtime:
                with self.controller.runtime.store.db() as db:db.execute('INSERT INTO snippets VALUES(?,?,?,?)',(uuid.uuid4().hex[:12],self.vault.descriptors([token])[0]['label'],text,time.time()))
            self.payload.clear();self.label.clear();self.secret.setChecked(False)
        except ValueError as exc:QMessageBox.information(self,'Exact text',str(exc))
    def sync_pending(self,*_):
        vault=self.vault.clone();text=self.payload.toPlainText()
        if text:
            try:vault.add(text,self.label.text() or 'Current pasted text',self.secret.isChecked())
            except ValueError:return
        self.controller.literal_vault=vault
    def send(self):
        if self.payload.toPlainText():self.add()
        instruction=self.instruction.toPlainText().strip()
        if not instruction:return
        if self.controller.state!='idle':QMessageBox.information(self,'Bilal','Finish recording or transcription first. Background tasks can keep running.');return
        descriptors=self.vault.descriptors()
        self.controller.literal_vault=self.vault.clone()
        import json
        self.controller.send(instruction+('\nLocal exact text references: '+json.dumps(descriptors,ensure_ascii=False) if descriptors else ''))
        self.instruction.clear()
    def clear(self):
        self.vault.clear();self.slots.clear();self.payload.clear();self.controller.literal_vault=None
    def showEvent(self,event):
        super().showEvent(event);self.payload.setFocus()
    def closeEvent(self,event):
        # Already queued tasks have their own immutable copies.
        self.clear();super().closeEvent(event)
