"""Matter tab — powder-game canvas with a palette and brush."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget,
)

from . import matter

BG = "#111113"


class MatterCanvas(QWidget):
    """Paints the flat bytearray grid, scaled up. Click/drag paints
    the selected matter; right-drag erases."""

    def __init__(self, cols: int = 280, rows: int = 180, cell: int = 2):
        super().__init__()
        self.cols, self.rows, self.cell = cols, rows, cell
        self.grid = bytearray(cols * rows)
        self.brush = matter.SAND
        self.radius = 3
        self._erase = False
        self.setMinimumSize(cols * cell // 2, rows * cell // 2)

    def _cell_at(self, pos) -> tuple[int, int]:
        cw = self.width() / self.cols
        ch = self.height() / self.rows
        return int(pos.y() // ch), int(pos.x() // cw)

    def _stamp(self, y, x):
        r = self.radius
        for dy in range(-r, r + 1):
            yy = y + dy
            if 0 <= yy < self.rows:
                for dx in range(-r, r + 1):
                    xx = x + dx
                    if (0 <= xx < self.cols
                            and dx * dx + dy * dy <= r * r):
                        i = yy * self.cols + xx
                        m = self.grid[i]
                        # solids replace anything; fluids/powders fill
                        # empty space or swap liquids
                        if self._erase:
                            self.grid[i] = matter.EMPTY
                        elif self.brush == matter.WALL:
                            self.grid[i] = matter.WALL
                        elif m == matter.EMPTY:
                            self.grid[i] = self.brush

    def mousePressEvent(self, e):
        self._erase = e.button() == Qt.RightButton
        self._stamp(*self._cell_at(e.position()))

    def mouseMoveEvent(self, e):
        if e.buttons() & (Qt.LeftButton | Qt.RightButton):
            self._stamp(*self._cell_at(e.position()))

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))
        img = QImage(self.cols, self.rows, QImage.Format_RGB32)
        for i, m in enumerate(self.grid):
            img.setPixel(i % self.cols, i // self.cols,
                         QColor(*matter.COLORS[m]).rgb())
        p.drawImage(self.rect(), img.scaled(
            self.width(), self.height(),
            Qt.IgnoreAspectRatio, Qt.FastTransformation))
        p.end()


class MatterTab(QWidget):
    PALETTE = [matter.SAND, matter.WATER, matter.STONE, matter.OIL,
               matter.PLANT, matter.FIRE, matter.LAVA, matter.ICE,
               matter.ACID, matter.TNT, matter.SMOKE, matter.WALL]

    def __init__(self):
        super().__init__()
        self.canvas = MatterCanvas()
        # reusable frame buffer: 0xffRRGGBB ints, rows*cols
        self._buf = [0] * (self.canvas.rows * self.canvas.cols)
        self._rgb = [((c[0] << 16) | (c[1] << 8) | c[2])
                     for c in matter.COLORS]

        top = QHBoxLayout()
        top.setSpacing(6)
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(34)
        self.btn_clear = QPushButton("clear")
        self.btn_wall_floor = QPushButton("border walls")
        self.btn_wall_floor.setToolTip(
            "Toggle solid walls around the canvas edges")
        top.addWidget(self.btn_play)
        top.addWidget(self.btn_clear)
        top.addWidget(self.btn_wall_floor)
        top.addWidget(QLabel("brush"))
        self.brush_size = QSlider(Qt.Horizontal)
        self.brush_size.setRange(1, 14)
        self.brush_size.setValue(4)
        top.addWidget(self.brush_size, stretch=1)

        pal = QGridLayout()
        pal.setSpacing(4)
        self._mat_buttons: dict[int, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for idx, m in enumerate(self.PALETTE):
            b = QPushButton(matter.NAMES[m])
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if m == matter.SAND:
                b.setChecked(True)
            rgb = matter.COLORS[m]
            bright = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            textc = "#111113" if bright > 128 else "#d8d8dc"
            b.setStyleSheet(f"""
                QPushButton {{ background: rgba({rgb[0]},{rgb[1]},{rgb[2]}, 0.85);
                    color: {textc}; border: 1px solid #2a2a30;
                    border-radius: 5px; padding: 3px 10px; }}
                QPushButton:checked {{ border: 2px solid #6d4aff;
                    font-weight: 600; }}""")
            b.clicked.connect(lambda _=False, mat=m: self._pick(mat))
            pal.addWidget(b, idx // 6, idx % 6)
            self._mat_buttons[m] = b
            self._group.addButton(b)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)
        lay.addLayout(top)
        lay.addLayout(pal)
        lay.addWidget(self.canvas, stretch=1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)   # ~25fps physics, always-on toy

        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_wall_floor.clicked.connect(self._toggle_walls)
        self.brush_size.valueChanged.connect(
            lambda v: setattr(self.canvas, "radius", v))

    def _pick(self, m: int):
        self.canvas.brush = m

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("▶")
        else:
            self.timer.start()
            self.btn_play.setText("⏸")

    def _clear(self):
        self.canvas.grid = bytearray(self.canvas.cols * self.canvas.rows)
        self.canvas.update()

    def _toggle_walls(self):
        c = self.canvas
        w, h = c.cols, c.rows
        edged = all(c.grid[x] == matter.WALL for x in range(w)) \
            and all(c.grid[y * w] == matter.WALL for y in range(h))
        if edged:
            # remove the border walls we added
            for x in range(w):
                c.grid[x] = c.grid[(h - 1) * w + x] = matter.EMPTY
            for y in range(h):
                c.grid[y * w] = c.grid[y * w + w - 1] = matter.EMPTY
        else:
            for x in range(w):
                c.grid[x] = c.grid[(h - 1) * w + x] = matter.WALL
            for y in range(h):
                c.grid[y * w] = c.grid[y * w + w - 1] = matter.WALL
        c.update()

    def _tick(self):
        import random as _r
        matter.step(self.canvas.grid, self.canvas.cols, self.canvas.rows)
        self.canvas.update()
