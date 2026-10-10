import os,signal,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap,QColor
from PySide6.QtCore import qInstallMessageHandler
from main import managed_painter,AssistantWindow,run_ui

class PainterShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_interrupted_painter_releases_device(self):
        image=QPixmap(20,20)
        with self.assertRaises(KeyboardInterrupt):
            with managed_painter(image) as painter:
                painter.fillRect(image.rect(),QColor('orange'))
                raise KeyboardInterrupt()
        with managed_painter(image) as painter:
            self.assertTrue(painter.isActive())
            painter.fillRect(image.rect(),QColor('blue'))

    def test_ctrl_c_during_frame_exits_without_painter_warnings(self):
        window=AssistantWindow(preview=True);window.controller=Mock()
        warnings=[];previous=qInstallMessageHandler(lambda kind,context,message:warnings.append(message))
        original=window.character.draw_pose;interrupt_sent=[]
        def interrupt_frame(*args):
            original(*args)
            if not interrupt_sent:
                interrupt_sent.append(True);signal.raise_signal(signal.SIGINT)
        try:
            window.character.draw_pose=interrupt_frame;window.show()
            run_ui(self.app,window)
            self.assertTrue(interrupt_sent)
            self.assertFalse(window.character.timer.isActive())
            self.assertFalse(any('QPainter' in message or 'QBackingStore' in message for message in warnings),warnings)
            window.controller.close.assert_called()
        finally:
            qInstallMessageHandler(previous);window.hide()

if __name__=='__main__':unittest.main()
