"""Shared readable dark styling for local task and exact-input dialogs."""
DIALOG_STYLE="""
QDialog {background:#151515;color:#F5EFE8;font-family:'Segoe UI';font-size:12px;}
QLabel,QCheckBox {color:#F5EFE8;background:transparent;}
QLineEdit,QPlainTextEdit,QTextBrowser,QListWidget {background:#232123;color:#F5EFE8;border:1px solid #40393A;border-radius:7px;padding:7px;selection-background-color:#835130;}
QPushButton {background:#FF8A3D;color:#251409;border:0;border-radius:7px;padding:9px;font-weight:600;}
QPushButton:hover {background:#FFA461;}
QTabWidget::pane {border:1px solid #40393A;} QTabBar::tab {background:#252225;color:#F5EFE8;padding:9px;}
QTabBar::tab:selected {background:#63432D;} QListWidget::item:selected {background:#63432D;}
"""
