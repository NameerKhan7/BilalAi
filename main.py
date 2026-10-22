"""Bilal AI: floating native character, wake activation and a model-driven agent."""
import argparse,json,math,os,sys,time,signal,threading
from contextlib import contextmanager
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,QPropertyAnimation,QEasingCurve,QLockFile
from PySide6.QtGui import QColor,QPainter,QPixmap,QPen,QRadialGradient,QIcon,QAction,QFontDatabase,QFont
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QFrame,
    QPushButton,QPlainTextEdit,QTextBrowser,QCheckBox,QSystemTrayIcon,QMenu,QDialog)
from PySide6.QtTextToSpeech import QTextToSpeech
from ui_controller import AssistantController
from contextual_input import ContextInputDialog
from conversation import ConversationSession
from hold_to_talk import HoldToTalk

ROOT=Path(__file__).resolve().parent
THEME=json.loads((ROOT/'brand_theme.json').read_text(encoding='utf-8-sig'))
STATES=['idle','listening','processing','speaking','success','error','loading','inactive']
TITLES={'idle':'Right here with you.','listening':'I’m listening.','processing':'Working on it.',
        'speaking':'Here’s what I found.','success':'All done.','error':'Let’s try that again.',
        'loading':'One moment.','inactive':'Taking a little rest.'}

def color(key): return QColor(THEME[key])

@contextmanager
def managed_painter(device):
    painter=QPainter(device)
    try:
        yield painter
    finally:
        if painter.isActive():painter.end()


class CharacterStage(QWidget):
    def __init__(self):
        super().__init__();self.setFixedHeight(315);self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        sheet=QPixmap(str(ROOT/'assets/character/poses.png'))
        self.poses={}
        for i,state in enumerate(STATES):
            self.poses[state]=sheet.copy((i%4)*sheet.width()//4,(i//4)*sheet.height()//2,sheet.width()//4,sheet.height()//2)
        self.orb=QPixmap(str(ROOT/'assets/character/orb-idle.png'))
        closed=self.poses['inactive'];neutral=self.poses['idle']
        self.eye_patch=self.feather_patch(closed,QRectF(closed.width()*.30,closed.height()*.37,closed.width()*.42,closed.height()*.08),132,26)
        self.mouth_patch=self.feather_patch(neutral,QRectF(neutral.width()*.38,neutral.height()*.575,neutral.width()*.24,neutral.height()*.10),80,36)
        self.state='idle';self.old='idle';self.changed=time.monotonic();self.started=self.changed
        self.level=0.;self.energy=0.;self.timer=QTimer(self);self.timer.timeout.connect(self.update);self.timer.start(33)
    @staticmethod
    def feather_patch(image,source,width,height):
        patch=QPixmap(width,height);patch.fill(Qt.GlobalColor.transparent)
        with managed_painter(patch) as painter:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(QRectF(0,0,width,height),image,source)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            painter.scale(1,height/width)
            mask=QRadialGradient(QPointF(width/2,width/2),width/2)
            mask.setColorAt(0,QColor(255,255,255,255));mask.setColorAt(.7,QColor(255,255,255,255));mask.setColorAt(1,QColor(255,255,255,0))
            painter.fillRect(QRectF(0,0,width,width),mask);
        return patch
    def set_state(self,state):
        if state!=self.state:
            self.old=self.state;self.state=state;self.changed=time.monotonic();self.update()
    def draw_pose(self,p,state,opacity,bob):
        p.setOpacity(opacity)
        t=time.monotonic()-self.started;age=time.monotonic()-self.changed
        if state=='idle' and not self.orb.isNull():
            image=self.orb;target=QRectF(67,0,346,411);split=.47
        else:
            image=self.poses[state];target=QRectF(95,6,290,303);split=.74
        source_height=image.height()*split
        head_height=target.height()*split
        # Upper body/face is articulated separately from the stationary torso.
        p.drawPixmap(QRectF(target.x(),target.y()+head_height,target.width(),target.height()-head_height),
                     image,QRectF(0,source_height,image.width(),image.height()-source_height))
        angles={'idle':math.sin(t*.8)*1.1,'listening':-4+math.sin(t*1.7),
                'processing':math.sin(t*1.3)*2.5,'speaking':math.sin(t*3.8)*1.8,
                'success':math.sin(age*9)*4*math.exp(-age*2),
                'error':math.sin(age*12)*4*math.exp(-age*1.5),'loading':0,'inactive':0}
        p.save();p.translate(240,target.y()+head_height);p.rotate(angles[state]);p.translate(-240,-target.y()-head_height)
        p.drawPixmap(QRectF(target.x(),target.y(),target.width(),head_height),image,QRectF(0,0,image.width(),source_height))
        # Reuse the supplied closed-eye artwork for a brief natural blink.
        blink=(t%5.2)-4.65
        if state!='inactive' and 0<blink<.26:
            closed=self.poses['inactive'];amount=math.sin(blink/.26*math.pi)
            eye_target=QRectF(174,94,132,25) if state=='idle' else QRectF(182,140,120,24)
            p.setOpacity(opacity*amount)
            p.drawPixmap(eye_target,self.eye_patch,QRectF(self.eye_patch.rect()))
            p.setOpacity(opacity)
        if state=='speaking':
            neutral=self.poses['idle']
            elapsed=time.monotonic()-getattr(self,'mouth_at',0)
            # Word events drive articulation when available; speaking state provides a fallback.
            opening=max(0,1-elapsed/getattr(self,'word_duration',.22)) if getattr(self,'mouth_at',0) and elapsed<.6 else .5+.5*math.sin(t*12)
            p.setOpacity(opacity*(1-opening))
            p.drawPixmap(QRectF(205,180,70,31),self.mouth_patch,QRectF(self.mouth_patch.rect()))
            p.setOpacity(opacity)
        p.restore()
        if state!='idle':
            gradient=QRadialGradient(QPointF(240,276),65)
            gradient.setColorAt(0,QColor('#FFC378'));gradient.setColorAt(.52,color('accent'))
            gradient.setColorAt(.85,color('orb_pink'));gradient.setColorAt(1,QColor('#B95E75'))
            p.setBrush(gradient);p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(QPointF(240,276),65,58)
        p.setOpacity(1)
    def paintEvent(self,event):
        with managed_painter(self) as p:
            p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scale=min(self.width()/330,self.height()/315)
            p.translate(self.width()/2-240*scale,(self.height()-315*scale)/2)
            p.scale(scale,scale)
            t=time.monotonic()-self.started;self.energy+=.18*(self.level-self.energy)
            bob=0  # No vertical floating: character gestures animate around a fixed anchor.
            radius=109+math.sin(t*2)*5+(self.energy*15 if self.state in {'listening','speaking'} else 0)
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

class VoiceWave(QWidget):
    def __init__(self,character):
        super().__init__();self.character=character;self.setFixedHeight(26)
        timer=QTimer(self);timer.timeout.connect(self.update);timer.start(50);self.timer=timer
    def paintEvent(self,event):
        with managed_painter(self) as p:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            level=self.character.energy if self.character.state=='listening' else .08
            t=time.monotonic();p.setPen(Qt.PenStyle.NoPen);p.setBrush(color('accent'))
            for i in range(17):
                h=3+min(21,level*22)*(.25+.75*abs(math.sin(t*3+i*.65)))
                p.drawRoundedRect(QRectF(self.width()/2+(i-8)*8-2,(26-h)/2,4,h),2,2)

class AssistantWindow(QWidget):
    def __init__(self,preview=False,conversation_enabled=None):
        super().__init__();self.preview=preview;self.visual='idle';self.verified=False;self.speech_pending=False;self.pending_dialog=None;self.input_dialog=None;self.last_wake_sample=None
        self.conversation_enabled=False if conversation_enabled is None else conversation_enabled
        self.hold_started=False;self.hold_background=False
        self.conversation=ConversationSession();self.hotkey=None
        self.turn_timer=QTimer(self);self.turn_timer.setSingleShot(True);self.turn_timer.timeout.connect(self.continue_conversation)
        self.setWindowTitle('Bilal AI');self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setFixedSize(96,120)
        self.setStyleSheet(f"QWidget {{font-family:'{THEME['font']}';color:{THEME['text']};}}")
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.character=CharacterStage();self.character.setFixedSize(96,120);layout.addWidget(self.character)
        card=QFrame();card.setObjectName('card');card.setStyleSheet(f"#card {{background:{THEME['background']};border:1px solid #39302B;border-radius:25px;}}")
        self.card=card;card.hide();self.details=None
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
                if hasattr(self.speech,'sayingWord'): self.speech.sayingWord.connect(self.spoken_word)
            else:self.voice.setChecked(False);self.voice.setEnabled(False)
            icon=QPixmap(64,64);icon.fill(Qt.GlobalColor.transparent)
            with managed_painter(icon) as painter:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color('accent'));painter.drawEllipse(8,8,48,48)
            self.tray=QSystemTrayIcon(QIcon(icon),self);menu=QMenu()
            show=menu.addAction('Show Bilal');show.triggered.connect(self.show_requested)
            listen=menu.addAction('Start / finish recording');listen.triggered.connect(self.record)
            cancel=menu.addAction('Cancel request');cancel.triggered.connect(self.cancel_task)
            details=menu.addAction('Read reply / type a request');details.triggered.connect(self.show_details)
            wake_action=menu.addAction('Listen for Hey Bilal');wake_action.setCheckable(True);wake_action.setChecked(True);wake_action.toggled.connect(self.wake.setChecked)
            self.wake.toggled.connect(wake_action.setChecked)
            voice_action=menu.addAction('Speak replies');voice_action.setCheckable(True);voice_action.setChecked(self.voice.isChecked());voice_action.toggled.connect(self.voice.setChecked)
            self.voice.toggled.connect(voice_action.setChecked)
            collect=menu.addAction('Collect reviewed wake examples');collect.triggered.connect(self.controller.collect_wake_examples)
            pending=menu.addAction('Pending approvals');pending.triggered.connect(self.show_pending)
            correct=menu.addAction('Last wake was correct');correct.triggered.connect(lambda:self.label_wake('positive'))
            false=menu.addAction('Last wake was a false trigger');false.triggered.connect(lambda:self.label_wake('negative'))
            clear=menu.addAction('Clear conversation');clear.triggered.connect(self.clear_conversation)
            quit_action=menu.addAction('Quit Bilal');quit_action.triggered.connect(self.quit)
            self.tray.setContextMenu(menu);self.tray.setToolTip('Bilal AI — your desktop companion')
            self.tray.activated.connect(lambda reason:self.show_requested() if reason==QSystemTrayIcon.ActivationReason.Trigger else None)
            self.tray.show()
            self.hotkey=HoldToTalk(self);self.hotkey.changed.connect(self.hold_changed);self.hotkey.start()
        self.drag=None;self.moved=False
        self.setToolTip('Say Hey Bilal or hold left Ctrl + left Shift to talk. Right-click for controls.')
    def begin_conversation(self):
        if not self.conversation_enabled:return
        self.conversation.begin();self.controller.conversation_active=True;self.turn_timer.stop()
    def end_conversation(self):
        self.conversation.end();self.turn_timer.stop()
        if self.controller:self.controller.conversation_active=False
    def hold_changed(self,held):
        if not self.controller or getattr(self,'shutting_down',False):return
        self.conversation.held=held
        if not held:
            self.controller.hold_event.clear()
            if not self.hold_started:return
            self.hold_started=False;self.hold_background=True;self.end_conversation();self.hide()
            if self.controller.state=='recording':self.controller.finish_recording()
            else:self.dismiss_when_idle()
            return
        # A shortcut must never submit input or approve an action.
        if self.input_dialog or self.pending_dialog:return
        if self.controller.pending_input and self.controller.pending_input.get('field')=='email':return
        if self.controller.state not in {'idle','recording'}:return
        self.hold_started=True;self.hold_background=False
        self.controller.hold_event.set();self.begin_conversation();self.show_center()
        if self.speech:self.speech.stop()
        if self.controller.state=='idle':self.controller.record(mode='hold')
    def continue_conversation(self):
        if not self.controller or getattr(self,'shutting_down',False):return
        if self.controller.state!='idle' or self.speech_pending:return
        if self.speech and self.speech.state()==QTextToSpeech.State.Speaking:return
        if self.input_dialog or self.pending_dialog:return
        if self.controller.pending_input and self.controller.pending_input.get('field')=='email':return
        if self.conversation_enabled and self.conversation.active:
            self.controller.record(mode='hold' if self.conversation.held else 'followup')
        else:
            self.controller.resume_wake();self.hide_if_idle()
    def set_visual(self,state,subtitle=None):
        self.visual=state;self.character.set_state(state);self.title.setText(TITLES[state])
        if subtitle:self.subtitle.setText(subtitle)
    def show_center(self):
        if self.hold_background and not self.conversation.held:return
        # Keep the familiar entry point, but anchor the companion above the taskbar.
        screen=QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        area=screen.availableGeometry()
        self.move(area.center().x()-self.width()//2,area.bottom()-self.height()-10)
        self.show();self.raise_()
        self.fade=QPropertyAnimation(self,b'windowOpacity');self.fade.setDuration(180)
        self.fade.setStartValue(.25);self.fade.setEndValue(1);self.fade.start()
    def show_requested(self):
        self.hold_background=False;self.show_center()
    def show_details(self):
        if self.details is None:
            self.details=QDialog()
            self.details.setWindowTitle('Bilal AI Conversation')
            self.details.setStyleSheet(f"background:{THEME['background']};color:{THEME['text']};")
            layout=QVBoxLayout(self.details);layout.setContentsMargins(0,0,0,0);layout.addWidget(self.card)
            self.hide_button.clicked.disconnect();self.hide_button.clicked.connect(self.details.hide)
            self.card.show();self.details.resize(430,470)
        self.details.show();self.details.raise_();self.details.activateWindow()
    def show_context_input(self,request):
        if self.input_dialog is not None:return
        def submit(value):
            if self.speech:self.speech.stop()
            return self.controller.submit_input(value)
        dialog=ContextInputDialog(request,THEME,submit,self)
        dialog.continue_button.setEnabled(self.controller.state=='idle')
        self.input_dialog=dialog
        def closed(result):
            self.input_dialog=None
            if not dialog.handled and not getattr(self,'shutting_down',False):
                self.controller.cancel_request();self.controller.resume_wake();self.dismiss_when_idle()
        dialog.finished.connect(closed)
        dialog.adjustSize()
        screen=QApplication.screenAt(self.pos()) or QApplication.primaryScreen();area=screen.availableGeometry()
        dialog.move(max(area.left(),min(self.x()+self.width()//2-dialog.width()//2,area.right()-dialog.width())),
                    max(area.top(),area.bottom()-self.height()-dialog.height()-20))
        dialog.show();dialog.raise_();dialog.activateWindow();dialog.entry.setFocus()
    def label_wake(self,label):
        monitor=self.controller.monitor
        sample=self.last_wake_sample or (monitor.last_sample if monitor else None)
        if sample and monitor:
            monitor.examples.label(sample,label)
            self.setToolTip('Wake feedback saved locally. No model was changed automatically.')
    def show_pending(self):
        pending=self.controller.state_store.pending()
        if pending:self.show_approval(pending[0])
    def show_approval(self,row):
        if self.pending_dialog is not None:return
        dialog=QDialog(self);dialog.setWindowTitle('Bilal AI Approval');dialog.resize(380,230) if row['kind']=='system_power' else dialog.resize(480,440)
        dialog.setStyleSheet(f"background:{THEME['background']};color:{THEME['text']};")
        layout=QVBoxLayout(dialog)
        from power_tools import ACTIONS
        power_label=ACTIONS.get(row['payload'].get('action'),'Power action') if row['kind']=='system_power' else None
        heading=QLabel('Confirm '+power_label.lower() if power_label else ('Review before sending' if row['kind']=='gmail_send' else 'Confirm what Bilal should remember'))
        heading.setStyleSheet('font-size:18px;font-weight:600;');layout.addWidget(heading)
        text=QTextBrowser();text.setStyleSheet('border:0;font-size:13px;')
        payload=row['payload']
        if row['kind']=='gmail_send':
            message=payload['message']
            text.setPlainText('From: '+(message.get('from') or 'Connected Gmail account')+'\nTo: '+message['to']+'\nCc: '+message.get('cc','')+'\nBcc: '+message.get('bcc','')+'\nSubject: '+message['subject']+'\n\n'+message['body'])
        elif row['kind']=='system_power':text.setPlainText(power_label+' this laptop now?\n\nSave your work before confirming. Windows may ask open apps to save. This confirmation expires after two minutes.')
        else:text.setPlainText(payload['key']+'\n\n'+payload['value'])
        layout.addWidget(text);buttons=QHBoxLayout()
        approve=QPushButton(power_label+' now' if power_label else ('Approve sending' if row['kind']=='gmail_send' else 'Remember this'))
        reject=QPushButton('Reject')
        approve.setStyleSheet(f'background:{THEME["accent"]};color:#23150B;border-radius:9px;padding:11px;font-weight:600;')
        reject.setStyleSheet('background:#292629;border-radius:9px;padding:11px;')
        buttons.addWidget(reject);buttons.addWidget(approve);layout.addLayout(buttons)
        dialog.handled=False
        def resolve(decision):
            if dialog.handled or getattr(self,'shutting_down',False):return
            dialog.handled=True;self.pending_dialog=None
            if self.speech:self.speech.stop()
            dialog.close();self.controller.resolve_approval(row['id'],row['digest'],decision)
        approve.clicked.connect(lambda:resolve(True));reject.clicked.connect(lambda:resolve(False));dialog.rejected.connect(lambda:resolve(False))
        self.controller.reviewed_action=(row['id'],row['digest']);self.pending_dialog=dialog
        dialog.show();dialog.raise_()
    def busy(self,value):
        self.send.setEnabled(not value);self.input.setReadOnly(value);self.cancel.setVisible(value)
        self.mic.setEnabled(not value or self.visual=='listening')
        self.mic.setText('■  Finish recording' if self.visual=='listening' else '●  Talk to Bilal')
    def record(self):
        if self.controller.state=='recording':self.controller.finish_recording();self.mic.setEnabled(False)
        elif self.controller.state=='idle':
            self.hold_background=False
            self.begin_conversation()
            if self.speech:self.speech.stop()
            self.reply.hide();self.transcript.hide();self.controller.record()
    def send_text(self):
        text=self.input.toPlainText().strip()
        if text and self.controller.pending_input and self.controller.pending_input.get('field')=='text':
            if self.controller.submit_input(text):self.input.clear()
            return
        if text:self.begin_conversation();self.reply.hide();self.controller.send(text);self.input.clear()
    def cancel_task(self):
        self.end_conversation()
        if self.speech:self.speech.stop()
        self.controller.cancel_request();self.subtitle.setText('Stopping the current request…')
        if self.controller.state=='idle':self.busy(False);self.set_visual('idle');self.controller.resume_wake()
    def toggle_wake(self,enabled):
        self.controller.set_wake(enabled)
        if self.controller.state=='idle':self.set_visual('idle' if enabled else 'inactive','Say “Hey Bilal”, or tap the microphone.' if enabled else 'Tap the microphone whenever you need me.')
    def handle_event(self,name,data):
        if name=='wake_activated':
            self.hold_background=False
            self.begin_conversation()
            self.last_wake_sample=data.get('sample_id')
            self.show_center();self.reply.hide();self.transcript.hide()
        elif name=='wake_rejected':
            self.end_conversation()
            self.character.level=0;self.verified=False;self.set_visual('idle');self.hide_if_idle()
        elif name=='input_needed':
            if data.get('field')=='email':self.show_context_input(data)
            else:self.setToolTip('Hold left Ctrl + left Shift to answer the spoken question.')
        elif name=='input_cancelled':
            if self.input_dialog:
                self.input_dialog.handled=True;self.input_dialog.close();self.input_dialog=None
        elif name=='approval':self.show_approval(data)
        elif name=='approval_cancelled':
            if self.pending_dialog:
                self.pending_dialog.handled=True;self.pending_dialog.close();self.pending_dialog=None
        elif name=='cancelling':self.end_conversation();self.set_visual('inactive','Stopping pending actions.')
        elif name in {'conversation_timeout','conversation_ended'}:
            self.end_conversation()
            if name=='conversation_timeout':self.set_visual('idle','Conversation paused. Say Hey Bilal whenever you need me.')
        elif name=='wake_ready':
            if self.tray:self.tray.setToolTip('Bilal AI ? listening for Hey Bilal')
            self.save_runtime_status()
        elif name=='wake_retry':
            if self.tray:self.tray.setToolTip('Bilal AI ? waiting for microphone, retrying')
            self.save_runtime_status()
        elif name=='wake_error':
            self.wake.setChecked(False);self.subtitle.setText(data)
        elif name=='preparing':
            self.show_center()
            self.verified=False
            self.set_visual('loading','Getting ready to listen…');self.busy(True)
        elif name=='ready':
            self.set_visual('listening','Hold the keys while you speak; release to send.' if self.conversation.held else ('I’m here for your next thought. I’ll wait 15 seconds.' if self.controller.capture_mode=='followup' else 'Take your time. I’ll wait through short pauses.'));self.busy(True);self.mic.setEnabled(True);self.mic.setText('■  Finish recording')
        elif name=='level':
            self.character.level=min(1,data['rms']*20)
            self.subtitle.setText('Still here. Keep going when you’re ready.' if data.get('silence_seconds',0)>.7 else 'I’m listening. Finish whenever you’re ready.')
        elif name=='transcribing':
            self.character.level=0;self.set_visual('loading','Getting your words ready…');self.mic.setEnabled(False)
        elif name=='transcript':
            self.transcript.setPlainText(data);self.transcript.show()
        elif name=='thinking':
            self.show_center()
            self.set_visual('processing','Understanding your request and choosing the next step.');self.busy(True)
        elif name=='progress':
            label=data.replace('Working: ','')
            descriptions={'list apps':'Finding the app.','list windows':'Looking at your open windows.','inspect window':'Checking what’s on screen.','spotify play':'Finding your music.','activate control':'Taking the next step.','enter text':'Writing your text.','browser search':'Opening your search.','media status':'Checking playback.'}
            self.subtitle.setText(descriptions.get(label,'Working through your request.'))
        elif name=='reply':
            text=data['text'] if isinstance(data,dict) else data
            self.verified=isinstance(data,dict) and data.get('verified',False)
            self.reply.setPlainText(text);self.reply.show();self.setToolTip('Reply ready. Right-click to read it.');self.show_center();self.set_visual('success' if self.verified else 'idle','Your reply is ready.')
            self.speak_message(text)
        elif name in {'error','empty'}:
            self.verified=False
            self.reply.setPlainText(data);self.reply.show();self.setToolTip('A task needs attention. Right-click to read the details.');self.show_center();self.set_visual('error','Your request could not finish. See the details below.');self.character.level=0
            self.speak_message(data)
        elif name=='cancelled':self.set_visual('idle','Request cancelled. Ready when you are.')
        elif name=='finished':
            if self.input_dialog:self.input_dialog.continue_button.setEnabled(True)
            if not self.speech_pending and (not self.speech or self.speech.state()!=QTextToSpeech.State.Speaking):
                self.busy(False);self.dismiss_when_idle()
    def speak_message(self,text):
        if self.voice.isChecked() and self.speech and text:
            if self.controller.monitor:self.controller.monitor.pause()
            self.speech_pending=True
            self.set_visual('speaking','');self.busy(True);self.speech.say(text)
    def spoken_word(self,word,*args):
        self.character.mouth_at=time.monotonic()
        self.character.word_duration=.08+min(.35,len(word)*.025)
        self.character.level=.4+min(.3,len(word)*.02)
    def speech_state(self,state):
        if state==QTextToSpeech.State.Speaking:self.set_visual('speaking')
        elif state in {QTextToSpeech.State.Ready,QTextToSpeech.State.Error}:
            completed_reply=self.speech_pending;self.speech_pending=False
            self.character.level=0
            self.busy(False);self.set_visual('success' if self.verified else 'idle','Ready whenever you need me.')
            if completed_reply:self.dismiss_when_idle()
    def dismiss_when_idle(self):
        # One restartable timer prevents duplicate captures from reply/finished signals.
        self.turn_timer.start(220)
    def hide_if_idle(self):
        if self.conversation.keep_visible:return
        if self.input_dialog is not None and self.input_dialog.isVisible():return
        if self.pending_dialog is not None and self.pending_dialog.isVisible():return
        if self.controller and self.controller.state=='idle' and not self.speech_pending:
            if not self.speech or self.speech.state()!=QTextToSpeech.State.Speaking:
                self.hide()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            if self.controller and (self.controller.state!='idle' or self.visual=='speaking'):self.cancel_task()
            else:self.end_conversation();self.hide()
        elif event.key()==Qt.Key.Key_Space and self.input is not QApplication.focusWidget() and not event.isAutoRepeat() and self.controller:self.record()
        else:super().keyPressEvent(event)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.RightButton and self.tray:self.tray.contextMenu().exec(event.globalPosition().toPoint())
        elif event.button()==Qt.MouseButton.LeftButton:self.drag=event.globalPosition().toPoint()-self.pos();self.moved=False
    def mouseMoveEvent(self,event):
        if self.drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
            position=event.globalPosition().toPoint()-self.drag
            if (position-self.pos()).manhattanLength()>3:self.moved=True
            if self.moved:self.move(position)
    def mouseReleaseEvent(self,event):
        clicked=self.drag is not None and not self.moved;self.drag=None
        if clicked:self.avatar_clicked()
    def avatar_clicked(self):
        if not self.controller or self.controller.state!='idle' or self.speech_pending:return
        if self.visual in {'processing','loading','listening','speaking'}:return
        if self.pending_dialog or self.input_dialog:return
        if self.speech and self.speech.state()==QTextToSpeech.State.Speaking:return
        self.record()
    def closeEvent(self,event):
        if not self.preview:
            event.ignore();self.cancel_task();self.hide()
        else:event.accept()
    def clear_conversation(self):
        if self.controller.state!='idle':return
        if self.controller.pending_input:self.controller.cancel_request()
        self.controller.brain.clear();self.reply.clear();self.reply.hide();self.transcript.clear();self.transcript.hide()
        self.set_visual('idle','A fresh conversation. Ready when you are.')

    def save_runtime_status(self):
        if self.preview:return
        monitor=self.controller.monitor
        try:
            (ROOT/'logs/ui_startup.json').write_text(json.dumps({'pid':os.getpid(),'visible':self.isVisible(),
                'size':[self.width(),self.height()],'speech_engine':self.speech.engine() if self.speech else None,
                'wake_enabled':self.wake.isChecked(),'wake_status':monitor.status if monitor else 'disabled',
                'wake_guard':'offline_full_phrase','wake_verifier_loaded':bool(monitor and getattr(monitor.verifier,'model',None) is not None),
                'hold_to_talk':bool(self.hotkey and self.hotkey.available),'conversation_active':self.conversation.active}),encoding='utf-8')
        except OSError:pass
    def quit(self):
        if getattr(self,'shutting_down',False):return
        self.shutting_down=True
        self.turn_timer.stop()
        if self.hotkey:self.hotkey.stop()
        self.character.timer.stop()
        for wave in self.findChildren(VoiceWave):wave.timer.stop()
        if hasattr(self,'fade'):self.fade.stop()
        self.controller.close()
        if self.speech:self.speech.stop()
        if self.tray:self.tray.hide()
        # Give cancellation checks time to stop microphone/tool workers.
        QTimer.singleShot(200,QApplication.quit)

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
    window.hide()  # Wake monitoring and the tray remain active while the avatar is hidden.
    QTimer.singleShot(2000,window.save_runtime_status)
    run_ui(app,window)

def run_ui(app,window):
    # Never raise KeyboardInterrupt inside a Qt paint callback.
    # The signal handler marks a request; the GUI timer performs cleanup.
    shutdown_requested=threading.Event()
    previous_sigint=signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT,lambda signum,frame:shutdown_requested.set())
    shutdown_timer=QTimer()
    shutdown_timer.setInterval(50)
    shutdown_timer.timeout.connect(lambda:window.quit() if shutdown_requested.is_set() else None)
    shutdown_timer.start()
    try:
        app.exec()
    finally:
        shutdown_timer.stop()
        signal.signal(signal.SIGINT,previous_sigint)
        window.controller.close()
if __name__=='__main__':main()
