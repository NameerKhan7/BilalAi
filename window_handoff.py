"""Human-selected window handoff, with a right-click selector, not click replay."""
from PySide6.QtCore import Qt,QPoint,QTimer
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QLabel,QComboBox,QLineEdit,QPushButton,QWidget,QMenu,QMessageBox
from ui_styles import DIALOG_STYLE


class WindowSelector(QWidget):
    def __init__(self,on_selected,on_cancel=None):
        super().__init__();self.on_selected=on_selected;self.on_cancel=on_cancel or (lambda:None);self.selected=False;self.cancelled=False;self.point=QPoint(100,100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint);self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setMouseTracking(True);self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())
        label=QLabel('Bilal handoff · right-click the intended window · Esc cancels',self);label.setStyleSheet('background:#191919;color:#FFAC70;padding:12px;border-radius:8px;');label.move(25,25);label.adjustSize()
    def paintEvent(self,event):
        painter=QPainter(self)
        try:painter.fillRect(self.rect(),QColor(0,0,0,12));painter.setPen(QPen(QColor('#FF8A3D'),2));painter.drawEllipse(self.point,14,14)
        finally:painter.end()
    def mouseMoveEvent(self,event):self.point=event.position().toPoint();self.update()
    def mousePressEvent(self,event):event.accept()
    def mouseReleaseEvent(self,event):
        event.accept()
        if event.button()!=Qt.MouseButton.RightButton:return
        import win32gui
        point=event.globalPosition().toPoint();native_point=win32gui.GetCursorPos();self.hide()
        # Resolve beneath the hidden overlay only after the original release has
        # been consumed. Never send the click to the underlying application.
        QTimer.singleShot(120,lambda:self.show_menu(point,native_point))
    def show_menu(self,point,native_point):
        if self.selected or self.cancelled:return
        import win32gui
        try:handle=win32gui.GetAncestor(win32gui.WindowFromPoint(native_point),2)
        except win32gui.error:self.close();return
        menu=QMenu();give=menu.addAction('Give this window to Bilal');cancel=menu.addAction('Cancel handoff')
        choice=menu.exec(point)
        if choice==give:self.selected=True;self.on_selected(handle);self.close()
        else:self.close()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:self.close()
        event.accept()
    def closeEvent(self,event):
        if not self.selected:self.cancelled=True;self.on_cancel()
        super().closeEvent(event)


class WindowHandoff(QDialog):
    def __init__(self,runtime,source_task=None,question=None,parent=None,on_started=None):
        super().__init__(parent);self.runtime=runtime;self.source_task=source_task;self.selector=None;self.token=None;self.on_started=on_started or (lambda task_id:None)
        self.setWindowTitle('Bilal AI — Give control of a window');self.setStyleSheet(DIALOG_STYLE);self.resize(570,260)
        layout=QVBoxLayout(self);label=QLabel(question or 'Open the browser and the correct signed-in tab, then select its window.');label.setWordWrap(True);label.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(label)
        self.tasks=QComboBox();self.tasks.addItem('New task in the selected window',None)
        for task in runtime.store.tasks(['blocked','failed','interrupted'],30):self.tasks.addItem(task['goal'][:130]+' · '+task['id'],task['id'])
        if source_task:
            index=self.tasks.findData(source_task)
            if index>=0:self.tasks.setCurrentIndex(index)
        layout.addWidget(self.tasks);self.goal=QLineEdit();self.goal.setPlaceholderText('What should Bilal do in that window?');layout.addWidget(self.goal);self.tasks.currentIndexChanged.connect(self.choose_task);self.choose_task()
        self.target=QLabel('No window selected. Login sessions stay in your existing browser.');self.target.setWordWrap(True);self.target.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.target)
        point=QPushButton('Point to a window, then right-click');point.clicked.connect(self.select);layout.addWidget(point)
        self.start=QPushButton('Give control and continue this task');self.start.setEnabled(False);self.start.clicked.connect(self.submit);layout.addWidget(self.start)
        stop=QPushButton('Cancel');stop.clicked.connect(self.reject);layout.addWidget(stop)
        layout.addWidget(QLabel('Access is limited to this window and task. Sending/deleting still requires approval.'))
    def choose_task(self,*_):
        source=self.tasks.currentData()
        if source:self.goal.setText(self.runtime.store.task(source)['goal'])
        elif self.source_task:self.goal.setText(self.runtime.store.task(self.source_task)['goal'])
    def select(self):
        self.hide();self.selector=WindowSelector(self.selected,lambda:self.show());self.selector.show();self.selector.raise_();self.selector.activateWindow()
    def selected(self,handle):
        try:
            if self.token:self.runtime.grants.revoke(self.token)
            self.token=self.runtime.grants.issue(handle);identity=self.runtime.grants.entries[self.token]['identity'];self.target.setText('Selected: '+identity['title']+'\nApplication: '+identity['process']);self.start.setEnabled(True)
        except (ValueError,OSError) as exc:QMessageBox.information(self,'Select window',str(exc))
        finally:self.show();self.raise_();self.activateWindow()
    def submit(self):
        if not self.token or not self.goal.text().strip():return
        try:
            task_id=self.runtime.submit_handoff(self.goal.text().strip(),self.token,self.tasks.currentData());self.token=None;self.on_started(task_id);self.accept()
        except (ValueError,RuntimeError) as exc:QMessageBox.information(self,'Handoff',str(exc))
    def done(self,result):
        if self.token:self.runtime.grants.revoke(self.token);self.token=None
        if self.selector:self.selector.selected=True;self.selector.close()
        super().done(result)
