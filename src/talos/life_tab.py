"""Life tab — a canvas you draw on and watch evolve.

Click/drag to paint cells, mouse wheel... no. Toolbar: play/pause,
step, clear, randomize, speed slider. Draw while it runs.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from . import life

CELL = "#e8e8ec"       # living cells — near-white
GRID_BG = "#111113"     # matches the fleet palette


class LifeCanvas(QWidget):
    """Paints the grid scaled to fit; clicks toggle cells."""

    paused_state = Signal(bool)

    def __init__(self, cols: int = 160, rows: int = 100):
        super().__init__()
        self.cols, self.rows = cols, rows
        self.grid = life.make_grid(cols, rows)
        self.setMinimumSize(400, 250)
        self.setMouseTracking(False)
        self._drag_paint_value = 1
        self._image = QImage(cols, rows, QImage.Format_RGB32)

    # ── interaction ────────────────────────────────────────────────
    def mousePressEvent(self, e):
        self._drag_paint_value = 0 if self._cell_at(e.position()) else 1
        self._paint_at(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & (Qt.LeftButton | Qt.RightButton):
            self._paint_at(e.position())

    def mouseReleaseEvent(self, e):
        self.update()

    def _cell_at(self, pos) -> tuple[int, int]:
        cw = self.width() / self.cols
        ch = self.height() / self.rows
        return int(pos.y() // ch), int(pos.x() // cw)

    def _paint_at(self, pos):
        y, x = self._cell_at(pos)
        self.grid[y][x] = self._drag_paint_value
        self.update()

    # ── painting ───────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(GRID_BG))
        # render grid into the small image, then scale it up
        bg = QColor(GRID_BG).rgb()
        fg = QColor(CELL).rgb()
        img = self._image
        for y, row in enumerate(self.grid):
            for x, v in enumerate(row):
                img.setPixel(x, y, fg if v else bg)
        p.drawImage(self.rect(), img.scaled(
            self.width(), self.height(),
            Qt.IgnoreAspectRatio, Qt.FastTransformation))
        p.end()

    # ── engine control ──────────────────────────────────────────────
    def step_once(self):
        self.grid = life.step(self.grid)
        self.update()

    def clear(self):
        self.grid = life.make_grid(self.cols, self.rows)
        self.update()

    def randomize(self):
        life.randomize(self.grid, density=0.35)
        self.update()


class LifeTab(QWidget):
    """Toolbar + canvas. Ticks on a QTimer driven by the speed slider."""

    def __init__(self):
        super().__init__()
        self.canvas = LifeCanvas()
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(34)
        self.btn_step = QPushButton("step")
        self.btn_clear = QPushButton("clear")
        self.btn_random = QPushButton("random")

        self.speed = QSlider(Qt.Horizontal)
        self.speed.setRange(1, 30)   # ticks per second
        self.speed.setValue(12)
        self.gen_label = QLabel("gen 0")
        self.gen_label.setStyleSheet("color: #8a8a90;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._generations = 0
        self._sync_speed()

        for w in (self.btn_play, self.btn_step, self.btn_clear,
                  self.btn_random):
            bar.addWidget(w)
        bar.addWidget(QLabel("speed"))
        bar.addWidget(self.speed, stretch=1)
        bar.addWidget(self.gen_label)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(bar)
        lay.addWidget(self.canvas, stretch=1)

        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_step.clicked.connect(self._step_paused)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_random.clicked.connect(self._randomize)
        self.speed.valueChanged.connect(self._sync_speed)

        # never greet the user with a dead universe
        self._randomize()

    # ── actions ─────────────────────────────────────────────────────
    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("▶")
        else:
            self.timer.start()
            self.btn_play.setText("⏸")

    def _step_paused(self):
        if not self.timer.isActive():
            self.canvas.step_once()
            self._generations += 1
            self.gen_label.setText(f"gen {self._generations}")

    def _clear(self):
        was_running = self.timer.isActive()
        self.timer.stop()
        self.canvas.clear()
        self._generations = 0
        self.gen_label.setText("gen 0")
        if was_running:
            self.timer.start()

    def _randomize(self):
        self.canvas.randomize()

    def _sync_speed(self):
        self.timer.setInterval(max(1, 1000 // self.speed.value()))

    def _tick(self):
        self.canvas.step_once()
        self._generations += 1
        self.gen_label.setText(f"gen {self._generations}")
