"""Bilal AI: floating native character, wake activation and a model-driven agent."""
import argparse,json,math,os,sys,time
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,QPropertyAnimation,QEasingCurve,QLockFile
from PySide6.QtGui import QColor,QPainter,QPixmap,QPen,QRadialGradient,QIcon,QAction,QFontDatabase,QFont
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QFrame,
    QPushButton,QPlainTextEdit,QTextBrowser,QCheckBox,QSystemTrayIcon,QMenu)
from PySide6.QtTextToSpeech import QTextToSpeech
from ui_controller import AssistantController

ROOT=Path(__file__).resolve().parent
THEME=json.loads((ROOT/'brand_theme.json').read_text(encoding='utf-8-sig'))
STATES=['idle','listening','processing','speaking','success','error','loading','inactive']
TITLES={'idle':'Right here with you.','listening':'I’m listening.','processing':'Working on it.',
        'speaking':'Here’s what I found.','success':'All done.','error':'Let’s try that again.',
        'loading':'One moment.','inactive':'Taking a little rest.'}

def color(key): return QColor(THEME[key])

class CharacterStage(QWidget):
    def __init__(self):
        super().__init__();self.setFixedHeight(315);self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        sheet=QPixmap(str(ROOT/'assets/character/poses.png'))
        self.poses={}
        for i,state in enumerate(STATES):
            self.poses[state]=sheet.copy((i%4)*sheet.width()//4,(i//4)*sheet.height()//2,sheet.width()//4,sheet.height()//2)
        self.orb=QPixmap(str(ROOT/'assets/character/orb-idle.png'))
        self.state='idle';self.old='idle';self.changed=time.monotonic();self.started=self.changed
        self.level=0.;self.energy=0.;self.timer=QTimer(self);self.timer.timeout.connect(self.update);self.timer.start(33)
    def set_state(self,state):
        if state!=self.state:
            self.old=self.state;self.state=state;self.changed=time.monotonic();self.update()
    def draw_pose(self,p,state,opacity,bob):
        p.setOpacity(opacity)
        if state=='idle' and not self.orb.isNull():
            p.drawPixmap(QRectF(67,0+bob,346,411),self.orb,QRectF(self.orb.rect()))
        else:
            p.drawPixmap(QRectF(95,6+bob,290,303),self.poses[state],QRectF(self.poses[state].rect()))
            gradient=QRadialGradient(QPointF(240,276+bob),65)
            gradient.setColorAt(0,QColor('#FFC378'));gradient.setColorAt(.52,color('accent'))
            gradient.setColorAt(.85,color('orb_pink'));gradient.setColorAt(1,QColor('#B95E75'))
            p.setBrush(gradient);p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(QPointF(240,276+bob),65,58)
        p.setOpacity(1)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(self.width()/480,self.height()/315)
        t=time.monotonic()-self.started;self.energy+=.18*(self.level-self.energy)
        bob=math.sin(t*1.8)*2.4 if self.state!='inactive' else 0
        radius=109+math.sin(t*2)*5+(self.energy*15 if self.state=='listening' else 0)
        glow=QRadialGradient(QPointF(240,265),radius)
        warm=color('accent');warm.setAlpha(85 if self.state!='inactive' else 30)
        glow.setColorAt(0,warm);glow.setColorAt(1,QColor(255,138,61,0))
        p.setBrush(glow);p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(QPointF(240,265),radius,radius*.65)
        mix=min(1,(time.monotonic()-self.changed)/.32)
        if mix<1:self.draw_pose(p,self.old,1-mix,bob)
        self.draw_pose(p,self.state,mix,bob)
        if self.state in {'loading','processing'}:
            for i in range(3):
                angle=t*(1.3 if self.state=='loading' else .8)+i*2.094
                p.setBrush(color('accent'));p.drawEllipse(QPointF(240+98*math.cos(angle),267+22*math.sin(angle)),3,3)
        p.end()

class VoiceWave(QWidget):
    def __init__(self,character):
        super().__init__();self.character=character;self.setFixedHeight(26)
        timer=QTimer(self);timer.timeout.connect(self.update);timer.start(50);self.timer=timer
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        level=self.character.energy if self.character.state=='listening' else .08
        t=time.monotonic();p.setPen(Qt.PenStyle.NoPen);p.setBrush(color('accent'))
        for i in range(17):
            h=3+min(21,level*22)*(.25+.75*abs(math.sin(t*3+i*.65)))
            p.drawRoundedRect(QRectF(self.width()/2+(i-8)*8-2,(26-h)/2,4,h),2,2)
        p.end()

class AssistantWindow(QWidget):
    def __init__(self,preview=False):
        super().__init__();self.preview=preview;self.visual='idle';self.verified=False
        self.setWindowTitle('Bilal AI');self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setMinimumWidth(460);self.resize(480,730)
        self.setStyleSheet(f"QWidget {{font-family:'{THEME['font']}';color:{THEME['text']};}}")
        layout=QVBoxLayout(self);layout.setContentsMargins(18,0,18,18);layout.setSpacing(0)
        self.character=CharacterStage();layout.addWidget(self.character)
        card=QFrame();card.setObjectName('card');card.setStyleSheet(f"#card {{background:{THEME['background']};border:1px solid #39302B;border-radius:25px;}}")
        layout.addWidget(card);self.card=card
        body=QVBoxLayout(card);body.setContentsMargins(24,18,24,20);body.setSpacing(9)
        top=QHBoxLayout();brand=QLabel('B I L A L');brand.setStyleSheet(f"color:{THEME['accent']};font-size:11px;font-weight:700;")
        top.addWidget(brand);top.addStretch()
        self.hide_button=QPushButton('−');self.hide_button.setToolTip('Hide to the system tray')
        self.hide_button.setFixedSize(26,24);self.hide_button.clicked.connect(self.hide)
        self.hide_button.setStyleSheet('background:transparent;border:0;color:#A8A4A1;font-size:20px;')
        top.addWidget(self.hide_button);body.addLayout(top)
        self.title=QLabel(TITLES['idle']);self.title.setStyleSheet('font-size:23px;font-weight:650;');body.addWidget(self.title)
        self.subtitle=QLabel('Say “Hey Bilal”, or tap the microphone.');self.subtitle.setWordWrap(True);self.subtitle.setMaximumHeight(40)
        self.subtitle.setStyleSheet(f"color:{THEME['muted']};font-size:12px;");body.addWidget(self.subtitle)
        body.addWidget(VoiceWave(self.character))
        self.transcript=QTextBrowser();self.transcript.setOpenExternalLinks(False)
        self.transcript.setStyleSheet('background:transparent;border:0;font-size:12px;color:#BDB7B2;padding:3px 0;');self.transcript.setFixedHeight(44);self.transcript.hide();body.addWidget(self.transcript)
        self.reply=QTextBrowser();self.reply.setOpenExternalLinks(False);self.reply.setFixedHeight(98)
        self.reply.setStyleSheet('background:transparent;border:0;font-size:13px;');self.reply.hide();body.addWidget(self.reply)
        self.input=QPlainTextEdit();self.input.setPlaceholderText('Or type what you need…');self.input.setFixedHeight(57)
        self.input.setStyleSheet(f"background:{THEME['surface']};border:1px solid #333033;border-radius:12px;padding:9px;font-size:12px;")
        body.addWidget(self.input)
        actions=QHBoxLayout();self.mic=QPushButton('●  Talk to Bilal');self.send=QPushButton('Send');self.cancel=QPushButton('Cancel')
        self.mic.setStyleSheet(f"background:{THEME['accent']};color:#24160D;border:0;border-radius:12px;padding:12px;font-size:12px;font-weight:700;")
        for button in (self.send,self.cancel):button.setStyleSheet('background:#292629;border:0;border-radius:12px;padding:12px;font-size:12px;')
        actions.addWidget(self.mic,1);actions.addWidget(self.send);actions.addWidget(self.cancel);self.cancel.hide();body.addLayout(actions)
        prefs=QHBoxLayout();self.wake=QCheckBox('Hey Bilal');self.wake.setChecked(not preview);self.voice=QCheckBox('Speak replies');self.voice.setChecked(not preview)
        for checkbox in (self.wake,self.voice):checkbox.setStyleSheet('font-size:11px;color:#AAA39D;')
        prefs.addWidget(self.wake);prefs.addStretch();prefs.addWidget(self.voice);body.addLayout(prefs)
        self.privacy=QLabel('Wake listening stays local · Esc cancels')
        self.privacy.setToolTip('Commands go to Groq for transcription. Gemini receives the request and relevant app observations. Recordings and task logs stay on this PC.')
        self.privacy.setStyleSheet('font-size:10px;color:#77716D;');body.addWidget(self.privacy)
        self.controller=None;self.speech=None;self.tray=None
        if not preview:
            self.controller=AssistantController();self.controller.event.connect(self.handle_event)
            self.mic.clicked.connect(self.record);self.send.clicked.connect(self.send_text)
            self.cancel.clicked.connect(self.cancel_task);self.wake.toggled.connect(self.toggle_wake)
            if QTextToSpeech.availableEngines():
                self.speech=QTextToSpeech('sapi' if 'sapi' in QTextToSpeech.availableEngines() else QTextToSpeech.availableEngines()[0],self);self.speech.stateChanged.connect(self.speech_state)
            else:self.voice.setChecked(False);self.voice.setEnabled(False)
            icon=QPixmap(64,64);icon.fill(Qt.GlobalColor.transparent)
            painter=QPainter(icon);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color('accent'));painter.drawEllipse(8,8,48,48);painter.end()
            self.tray=QSystemTrayIcon(QIcon(icon),self);menu=QMenu()
            show=menu.addAction('Talk to Bilal');show.triggered.connect(self.show_center)
            clear=menu.addAction('Clear conversation');clear.triggered.connect(self.clear_conversation)
            quit_action=menu.addAction('Quit Bilal');quit_action.triggered.connect(self.quit)
            self.tray.setContextMenu(menu);self.tray.setToolTip('Bilal AI — your desktop companion')
            self.tray.activated.connect(lambda reason:self.show_center() if reason==QSystemTrayIcon.ActivationReason.Trigger else None)
            self.tray.show()
        self.drag=None
    def set_visual(self,state,subtitle=None):
        self.visual=state;self.character.set_state(state);self.title.setText(TITLES[state])
        if subtitle:self.subtitle.setText(subtitle)
    def show_center(self):
        screen=QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        area=screen.availableGeometry();self.character.setFixedHeight(min(315,max(140,area.height()-560)));self.adjustSize()
        self.move(area.center().x()-self.width()//2,area.center().y()-self.height()//2)
        self.show();self.raise_()
        self.fade=QPropertyAnimation(self,b'windowOpacity');self.fade.setDuration(240);self.fade.setStartValue(.1);self.fade.setEndValue(1);self.fade.setEasingCurve(QEasingCurve.Type.OutCubic);self.fade.start()
    def busy(self,value):
        self.send.setEnabled(not value);self.input.setReadOnly(value);self.cancel.setVisible(value)
        self.mic.setEnabled(not value or self.visual=='listening')
        self.mic.setText('■  Finish recording' if self.visual=='listening' else '●  Talk to Bilal')
    def record(self):
        if self.controller.state=='recording':self.controller.finish_recording();self.mic.setEnabled(False)
        elif self.controller.state=='idle':
            self.reply.hide();self.transcript.hide();self.controller.record()
    def send_text(self):
        text=self.input.toPlainText().strip()
        if text:self.reply.hide();self.controller.send(text);self.input.clear()
    def cancel_task(self):
        if self.speech:self.speech.stop()
        self.controller.cancel_request();self.subtitle.setText('Stopping the current request…')
        if self.controller.state=='idle':self.busy(False);self.set_visual('idle');self.controller.resume_wake()
    def toggle_wake(self,enabled):
        self.controller.set_wake(enabled)
        if self.controller.state=='idle':self.set_visual('idle' if enabled else 'inactive','Say “Hey Bilal”, or tap the microphone.' if enabled else 'Tap the microphone whenever you need me.')
    def handle_event(self,name,data):
        if name=='wake' and self.controller.state=='idle':
            self.show_center();self.reply.hide();self.transcript.hide();self.controller.record(from_wake=True)
        elif name=='wake_error':
            self.wake.setChecked(False);self.subtitle.setText(data)
        elif name=='preparing':
            self.set_visual('loading','Getting ready to listen…');self.busy(True)
        elif name=='ready':
            self.set_visual('listening','Take your time. I’ll wait through short pauses.');self.busy(True);self.mic.setEnabled(True);self.mic.setText('■  Finish recording')
        elif name=='level':
            self.character.level=min(1,data['rms']*20)
            self.subtitle.setText('Still here. Keep going when you’re ready.' if data.get('silence_seconds',0)>.7 else 'I’m listening. Finish whenever you’re ready.')
        elif name=='transcribing':
            self.character.level=0;self.set_visual('loading','Getting your words ready…');self.mic.setEnabled(False)
        elif name=='transcript':
            self.transcript.setPlainText(data);self.transcript.show()
        elif name=='thinking':
            self.set_visual('processing','Understanding your request and choosing the next step.');self.busy(True)
        elif name=='progress':
            label=data.replace('Working: ','')
            descriptions={'list apps':'Finding the app.','list windows':'Looking at your open windows.','inspect window':'Checking what’s on screen.','spotify play':'Finding your music.','activate control':'Taking the next step.','enter text':'Writing your text.','browser search':'Opening your search.','media status':'Checking playback.'}
            self.subtitle.setText(descriptions.get(label,'Working through your request.'))
        elif name=='reply':
            text=data['text'] if isinstance(data,dict) else data
            self.verified=isinstance(data,dict) and data.get('verified',False)
            self.reply.setPlainText(text);self.reply.show();self.show_center();self.set_visual('success' if self.verified else 'idle','Your reply is ready.')
            if self.voice.isChecked() and self.speech:
                self.controller.monitor.pause() if self.controller.monitor else None
                self.set_visual('speaking','');self.busy(True);self.speech.say(text)
        elif name in {'error','empty'}:
            self.reply.setPlainText(data);self.reply.show();self.show_center();self.set_visual('error','Your request could not finish. See the details below.');self.character.level=0
        elif name=='cancelled':self.set_visual('idle','Request cancelled. Ready when you are.')
        elif name=='finished':
            if not self.speech or self.speech.state()!=QTextToSpeech.State.Speaking:
                self.busy(False);self.controller.resume_wake()
    def speech_state(self,state):
        if state==QTextToSpeech.State.Speaking:self.set_visual('speaking')
        elif state in {QTextToSpeech.State.Ready,QTextToSpeech.State.Error}:
            self.busy(False);self.set_visual('success' if self.verified else 'idle','Ready whenever you need me.');self.controller.resume_wake()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            if self.controller and (self.controller.state!='idle' or self.visual=='speaking'):self.cancel_task()
            else:self.hide()
        elif event.key()==Qt.Key.Key_Space and self.input is not QApplication.focusWidget() and not event.isAutoRepeat() and self.controller:self.record()
        else:super().keyPressEvent(event)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.drag=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        if self.drag is not None and event.buttons() & Qt.MouseButton.LeftButton:self.move(event.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,event):self.drag=None
    def closeEvent(self,event):
        if not self.preview:event.ignore();self.hide()
        else:event.accept()
    def clear_conversation(self):
        if self.controller.state!='idle':return
        self.controller.brain.clear();self.reply.clear();self.reply.hide();self.transcript.clear();self.transcript.hide()
        self.set_visual('idle','A fresh conversation. Ready when you are.')

    def quit(self):
        self.controller.close()
        if self.speech:self.speech.stop()
        if self.tray:self.tray.hide()
        QApplication.quit()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview-all',action='store_true');args=parser.parse_args()
    if args.preview_all:os.environ['QT_QPA_PLATFORM']='offscreen'
    app=QApplication(sys.argv[:1]);app.setQuitOnLastWindowClosed(False)
    if not args.preview_all:
        (ROOT/'logs').mkdir(exist_ok=True)
        app_lock=QLockFile(str(ROOT/'logs/bilal_ui.lock'))
        if not app_lock.tryLock(0):
            print('Bilal is already running. Open it from the system tray.');return
    # Offscreen previews also need explicit access to Windows' native fonts.
    for name in ['segoeui.ttf','seguisb.ttf','segoeuib.ttf']:
        font_path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
        if font_path.is_file(): QFontDatabase.addApplicationFont(str(font_path))
    if THEME['font'] not in QFontDatabase.families(): THEME['font']='Segoe UI'
    app.setFont(QFont(THEME['font'],10))
    window=AssistantWindow(preview=args.preview_all)
    if args.preview_all:
        output=ROOT/'ui_preview';output.mkdir(exist_ok=True);window.show();app.processEvents()
        for state in STATES:
            window.set_visual(state,'Take your time. I’m right here.' if state=='listening' else 'Your desktop companion.')
            window.character.changed=time.monotonic()-1
            if state=='listening':window.character.level=.6
            else:window.character.level=0
            app.processEvents();window.grab().save(str(output/(state+'.png')))
        window.busy(False);window.reply.setPlainText('Playing Blinding Lights by The Weeknd on Spotify.');window.reply.show()
        window.transcript.setPlainText('Play blind Lights on Spotify by The Weeknd.');window.transcript.show()
        window.set_visual('success','Playback verified.');window.character.changed=time.monotonic()-1
        window.show_center();window.setWindowOpacity(1);app.processEvents();window.grab().save(str(output/'result.png'))
        print('Rendered eight UI states and a result preview in ui_preview/.');return
    window.show_center()
    def startup_status():
        (ROOT/'logs/ui_startup.json').write_text(json.dumps({'visible':window.isVisible(),'size':[window.width(),window.height()],
            'speech_engine':window.speech.engine() if window.speech else None,'wake_enabled':window.wake.isChecked()}),encoding='utf-8')
    QTimer.singleShot(2000,startup_status)
    app.exec()

if __name__=='__main__':main()
