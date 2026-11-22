"""Main window: two-tier nav — Toys and Games, inner tabs each.

talos doctrine (ludus's spirit, tighter):
- toys: zero-commitment sims, no saves; games: systems + saves
- every tab is a self-contained QWidget; engines stay Qt-free
- window is sized to tabs and locked (no maximize/resizing games)
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
)

from .life_tab import LifeTab
from .matter_tab import MatterTab

TITLE = "talos"
BG = "#111113"
FG = "#d8d8dc"
ACCENT = "#6d4aff"

TAB_CSS = f"""
    QTabBar::tab {{ background: transparent; color: #8a8a90;
        padding: 6px 18px; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {ACCENT};
        border-bottom: 2px solid {ACCENT}; }}
    QTabWidget::pane {{ border: none; }}"""


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


class BucketPage(QWidget):
    """An inner tab bar holding one bucket's residents."""

    def __init__(self, tabs: list[tuple[str, QWidget]]):
        super().__init__()
        bar = QTabWidget()
        bar.setDocumentMode(True)
        bar.setStyleSheet(TAB_CSS)
        for name, tab in tabs:
            bar.addTab(tab, name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(bar)


class GamesPlaceholder(QWidget):
    def __init__(self):
        super().__init__()
        from PySide6.QtWidgets import QLabel
        lbl = QLabel(
            "Games — systems, saves, memory.\n\n"
            "Queued: Blackjack (core + double/split) · Slots/reels\n"
            "Later: ASCII dungeon crawler · SanctuaryRPG-style adventure\n\n"
            "Saves will live in ~/.local/share/talos/saves/")
        lbl.setStyleSheet(f"color: #8a8a90; padding: 24px;")
        lay = QVBoxLayout(self)
        lay.addWidget(lbl)
        lay.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setFixedSize(980, 700)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(TAB_CSS)

        self.tabs.addTab(
            BucketPage([("Life", LifeTab()),
                        ("Matter", MatterTab())]),
            "Toys")
        self.tabs.addTab(GamesPlaceholder(), "Games")

        self.setCentralWidget(self.tabs)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(TITLE)
    apply_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
