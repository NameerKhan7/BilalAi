import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from contextual_input import ContextInputDialog,validate_detail

class ContextInputTests(unittest.TestCase):
    def test_email_requires_one_full_address(self):
        self.assertEqual(validate_detail('email',' person@example.org '),'person@example.org')
        for value in ['Nameer','a@example.org; b@example.org','a@example.org\nBcc: x@example.org','']:
            with self.assertRaises(ValueError):validate_detail('email',value)
    def test_popup_validates_and_submits_once_then_closes(self):
        app=QApplication.instance() or QApplication([])
        submit=Mock(return_value=True)
        dialog=ContextInputDialog({'question':'Tell me the email address.','field':'email'},
            {'background':'#121212','text':'#FFFFFF','accent':'#FF8734'},submit)
        dialog.show();app.processEvents()
        dialog.entry.setText('Nameer');dialog.send_detail();submit.assert_not_called()
        self.assertTrue(dialog.isVisible())
        dialog.entry.setText('person@example.org');dialog.send_detail();dialog.send_detail()
        submit.assert_called_once_with('person@example.org');self.assertFalse(dialog.isVisible())
