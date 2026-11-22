"""Main window: one locked-size window, one tab bar, room to grow.

talos doctrine (ludus's spirit, tighter):
- every tab is a self-contained QWidget; engines stay Qt-free
- window is sized to tabs and locked (no maximize/resizing games)
- working tabs ship first, placeholders go at the end
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from .life_tab import LifeTab

TITLE = "talos"
BG = "#111113"
FG = "#d8d8dc"
ACCENT = "#6d4aff"


def apply_theme(app: QApplication):
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(FG))
    pal.setColor(QPalette.Base, QColor("#17171a"))
    pal.setColor(QPalette.Text, QColor(FG))
    pal.setColor(QPalette.Button, QColor("#17171a"))
    pal.setColor(QPalette.ButtonText, QColor(FG))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor(FG))
    app.setPalette(pal)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setFixedSize(900, 620)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{ background: transparent; color: #8a8a90;
                padding: 6px 18px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: {ACCENT};
                border-bottom: 2px solid {ACCENT}; }}
            QTabWidget::pane {{ border: none; }}""")

        self.tabs.addTab(LifeTab(), "Life")

        self.setCentralWidget(self.tabs)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(TITLE)
    apply_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
