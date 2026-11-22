# talos

One-window, tabbed playground of cellular automata and toys.

Named for the bronze automaton of Greek myth — an animated construct
that lives without its maker's hand. Spirit successor to
[ludus](https://github.com/ZachrielForever/ludus): same shape (locked
window, switchable tabs), rebuilt with the house rules:

- **Engines are pure.** Simulation logic carries zero Qt imports and
  is tested headless (`pytest tests/`).
- **Tabs are self-contained.** Each tab is a QWidget that owns its
  engine, toolbar, and canvas.
- **Dark, one accent.** Near-black canvas, white cells, purple.

## Running

```fish
python -m venv .venv
.venv/bin/pip install PySide6
.venv/bin/python -m talos
```

## Tabs

- **Life** — Conway's B3/S23 on a torus. Draw with the mouse while it
  runs; play/pause/step/clear/random; speed slider 1–30 gens/sec.
