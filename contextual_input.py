"""Small, temporary input prompt for a detail missing from the current task."""
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton


def validate_detail(field,value):
    value=value.strip()
    if not value or len(value)>2000:
        raise ValueError('Enter a detail under 2,000 characters.')
    if field=='email' and not re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+',value):
        raise ValueError('Paste one complete email address, such as name@example.com.')
    if field not in {'email','text'}:raise ValueError('Unsupported input field.')
    return value


class ContextInputDialog(QDialog):
    def __init__(self,request,theme,submit,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Bilal AI Input')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(360);self.request=request;self.submit=submit;self.handled=False
        self.setStyleSheet(f"background:{theme['background']};color:{theme['text']};")
        layout=QVBoxLayout(self);layout.setContentsMargins(16,14,16,14);layout.setSpacing(10)
        question=QLabel(request['question']);question.setTextFormat(Qt.TextFormat.PlainText);question.setWordWrap(True)
        question.setStyleSheet('font-size:14px;font-weight:600;');layout.addWidget(question)
        self.entry=QLineEdit();self.entry.setMaxLength(2000)
        self.entry.setPlaceholderText('Paste the email address' if request['field']=='email' else 'Type or paste here')
        self.entry.setStyleSheet('background:#252326;border:1px solid #494449;border-radius:8px;padding:10px;font-size:13px;')
        layout.addWidget(self.entry)
        self.error=QLabel();self.error.setTextFormat(Qt.TextFormat.PlainText);self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#F6AB81;font-size:11px;');self.error.hide();layout.addWidget(self.error)
        buttons=QHBoxLayout();cancel=QPushButton('Cancel');self.continue_button=QPushButton('Continue')
        self.continue_button.setStyleSheet(f"background:{theme['accent']};color:#23150B;border:0;border-radius:8px;padding:9px;font-weight:600;")
        cancel.setStyleSheet('background:#292629;border:0;border-radius:8px;padding:9px;')
        buttons.addWidget(cancel);buttons.addWidget(self.continue_button);layout.addLayout(buttons)
        cancel.clicked.connect(self.reject);self.continue_button.clicked.connect(self.send_detail);self.entry.returnPressed.connect(self.send_detail)
    def send_detail(self):
        if self.handled or not self.continue_button.isEnabled():return
        try:
            value=validate_detail(self.request['field'],self.entry.text())
            if not self.submit(value):return
        except ValueError as exc:
            self.error.setText(str(exc));self.error.show();return
        self.handled=True;self.accept()
