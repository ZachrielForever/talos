"""Matter engine — powder-game physics, pure logic, no Qt.

Falling-sand style cellular automaton on a flat bytearray grid
(row-major, matter ids). Edges are solid boundaries. step() mutates
the grid in place; pass a seeded random.Random for determinism.

Matter set (chef's choice, 13 states):
  empty, wall, sand, water, stone, oil, fire, smoke, plant,
  acid, lava, ice, tnt

Signature interactions:
  sand sinks through liquids · oil floats on water and burns ·
  fire spreads to flammables, dies to smoke near water ·
  lava + water -> stone + smoke · acid dissolves almost everything ·
  plants drink water to grow · ice melts by fire, freezes water ·
  tnt chain-detonates, water dampens the blast
"""

from __future__ import annotations

import random

EMPTY, WALL, SAND, WATER, STONE, OIL, FIRE, SMOKE, PLANT, \
    ACID, LAVA, ICE, TNT = range(13)

COUNT = 13

NAMES = ["empty", "wall", "sand", "water", "stone", "oil", "fire",
         "smoke", "plant", "acid", "lava", "ice", "tnt"]

COLORS = [
    (17, 17, 19),    # empty (canvas bg)
    (105, 105, 112),  # wall
    (199, 183, 129),  # sand
    (52, 122, 196),   # water
    (128, 132, 140),  # stone
    (86, 66, 46),     # oil
    (255, 168, 54),   # fire
    (128, 128, 136),  # smoke
    (74, 160, 70),    # plant
    (150, 225, 60),   # acid
    (235, 80, 28),    # lava
    (168, 212, 235),  # ice
    (200, 62, 62),    # tnt
]

_IS_POWDER = [m in (SAND, STONE, TNT) for m in range(COUNT)]
_IS_LIQUID = [m in (WATER, OIL, ACID, LAVA) for m in range(COUNT)]
_DENSITY = [0] * COUNT          # liquids: higher sinks
_DENSITY[OIL], _DENSITY[WATER] = 1, 2
_DENSITY[ACID], _DENSITY[LAVA] = 2, 3
_DIAGONAL = [m in (SAND, TNT) for m in range(COUNT)]
_FLAMMABLE = [0.0] * COUNT      # ignition chance per neighbor tick
_FLAMMABLE[OIL], _FLAMMABLE[PLANT] = 0.5, 0.05
_FLAMMABLE[TNT] = 1.0
_ACID_PROOF = [m in (EMPTY, WALL, ACID, WATER, SMOKE, FIRE)
               for m in range(COUNT)]

_N4 = ((0, 1), (0, -1), (1, 0), (-1, 0))
_N8 = _N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))

BOOM_RADIUS = 6


def _explode(g, w, h, x, y, rng, moved):
    """Detonate at (x, y): fire core, debris fringe, chained tnt.
    Walls and water dampen the blast (survive untouched)."""
    stack = [(x, y)]
    r2 = BOOM_RADIUS * BOOM_RADIUS
    while stack:
        cx, cy = stack.pop()
        x0, x1 = max(0, cx - BOOM_RADIUS), min(w - 1, cx + BOOM_RADIUS)
        y0, y1 = max(0, cy - BOOM_RADIUS), min(h - 1, cy + BOOM_RADIUS)
        for yy in range(y0, y1 + 1):
            row = yy * w
            for xx in range(x0, x1 + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if d2 > r2:
                    continue
                i = row + xx
                t = g[i]
                if t in (WALL, WATER):
                    continue
                if t == TNT:
                    g[i] = EMPTY
                    stack.append((xx, yy))
                    continue
                r = rng.random()
                if d2 < r2 * 0.4 and r < 0.75:
                    g[i] = FIRE
                elif r < 0.35:
                    g[i] = SMOKE
                else:
                    g[i] = EMPTY
                moved[i] = 1


def _try_powder(g, w, h, x, y, i, m, rng, moved):
    if y + 1 >= h:
        return
    b = i + w
    tb = g[b]
    if tb == EMPTY or _IS_LIQUID[tb]:
        g[i], g[b] = tb, m
        moved[b] = 1
        return
    if _DIAGONAL[m]:
        d = -1 if rng.random() < 0.5 else 1
        for dx in (d, -d):
            nx = x + dx
            if 0 <= nx < w:
                j = b + dx
                tj = g[j]
                if tj == EMPTY or _IS_LIQUID[tj]:
                    g[i], g[j] = tj, m
                    moved[j] = 1
                    return


def _try_liquid(g, w, h, x, y, i, m, rng, moved):
    if y + 1 < h:
        b = i + w
        tb = g[b]
        if tb == EMPTY:
            g[b], g[i] = m, EMPTY
            moved[b] = 1
            return True
        if _IS_LIQUID[tb] and _DENSITY[tb] < _DENSITY[m]:
            g[i], g[b] = tb, m          # denser liquid sinks
            moved[b] = 1
            return True
        d = -1 if rng.random() < 0.5 else 1
        for dx in (d, -d):
            nx = x + dx
            if 0 <= nx < w and g[b + dx] == EMPTY:
                g[b + dx], g[i] = m, EMPTY
                moved[b + dx] = 1
                return True
    # lateral dispersion: water spreads widest, oil least
    d = -1 if rng.random() < 0.5 else 1
    disp = 4 if m == WATER else (2 if m == ACID else 1)
    for dd in (d, -d):
        best = 0
        for k in range(1, disp + 1):
            nx = x + dd * k
            if nx < 0 or nx >= w or g[y * w + nx] != EMPTY:
                break
            best = k
        if best:
            j = y * w + x + dd * best
            g[j], g[i] = m, EMPTY
            moved[j] = 1
            return True
    return False


def step(g, w, h, rng=None, parity=False):
    """Advance one frame. Mutates g in place."""
    rng = rng or random
    moved = bytearray(w * h)
    xs = range(w) if parity else range(w - 1, -1, -1)
    for y in range(h - 1, -1, -1):
        row = y * w
        for x in xs:
            i = row + x
            m = g[i]
            if m == EMPTY or moved[i]:
                continue

            if _IS_POWDER[m]:
                # tnt resting on heat cooks off
                if m == TNT:
                    hot = False
                    for dx, dy in _N4:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h \
                                and g[ny * w + nx] in (FIRE, LAVA):
                            hot = True
                            break
                    if hot and rng.random() < 0.4:
                        g[i] = EMPTY
                        _explode(g, w, h, x, y, rng, moved)
                        continue
                _try_powder(g, w, h, x, y, i, m, rng, moved)
                continue

            if _IS_LIQUID[m]:
                if m == ACID:
                    for dx, dy in _N4:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            j = ny * w + nx
                            if not _ACID_PROOF[g[j]] and rng.random() < 0.2:
                                g[j] = EMPTY
                                moved[j] = 1
                                if rng.random() < 0.6:
                                    g[i] = EMPTY       # consumed
                                    break
                    if g[i] != ACID:
                        continue
                elif m == LAVA:
                    for dx, dy in _N4:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            j = ny * w + nx
                            t = g[j]
                            if t == WATER:
                                g[i], g[j] = STONE, SMOKE
                                moved[i] = moved[j] = 1
                                break
                            if _FLAMMABLE[t] and rng.random() \
                                    < _FLAMMABLE[t] * 0.5:
                                g[j] = FIRE
                                moved[j] = 1
                    if g[i] != LAVA or rng.random() < 0.5:
                        continue          # lava creeps
                _try_liquid(g, w, h, x, y, i, m, rng, moved)
                continue

            if m == SMOKE:
                if rng.random() < 0.02:
                    g[i] = EMPTY
                    continue
                u = i - w
                if y == 0 and rng.random() < 0.05:
                    g[i] = EMPTY
                    continue
                d = -1 if rng.random() < 0.5 else 1
                # rise: straight up, then diagonal up, then drift
                if y > 0:
                    if g[u] == EMPTY:
                        g[u], g[i] = SMOKE, EMPTY
                        moved[u] = 1
                        continue
                    dd = -1 if rng.random() < 0.5 else 1
                    nx = x + dd
                    if 0 <= nx < w and g[u + dd] == EMPTY:
                        g[u + dd], g[i] = SMOKE, EMPTY
                        moved[u + dd] = 1
                        continue
                nx = x + d
                if 0 <= nx < w and g[row + nx] == EMPTY:
                    g[row + nx], g[i] = SMOKE, EMPTY
                    moved[row + nx] = 1
                continue

            if m == FIRE:
                # extinguished by adjacent water
                for dx, dy in _N4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h \
                            and g[ny * w + nx] == WATER:
                        g[i] = SMOKE
                        break
                if g[i] != FIRE:
                    continue
                # ignite flammables (explosives detonate)
                for dx, dy in _N8:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        t = g[j]
                        if _FLAMMABLE[t] and rng.random() < _FLAMMABLE[t]:
                            if t == TNT:
                                g[j] = EMPTY
                                _explode(g, w, h, nx, ny, rng, moved)
                            else:
                                g[j] = FIRE
                                moved[j] = 1
                # emit smoke above
                if y > 0 and g[i - w] == EMPTY and rng.random() < 0.06:
                    g[i - w] = SMOKE
                    moved[i - w] = 1
                # burn out (slowly — flames should outlast a puddle)
                r = rng.random()
                if r < 0.02:
                    g[i] = SMOKE
                elif r < 0.03:
                    g[i] = EMPTY
                continue

            if m == PLANT:
                for dx, dy in _N4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if g[j] == WATER and rng.random() < 0.3:
                            g[j] = PLANT           # drinks water, grows
                            moved[j] = 1
                continue

            if m == ICE:
                melted = False
                for dx, dy in _N4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if g[j] in (FIRE, LAVA):
                            g[i] = WATER
                            melted = True
                            break
                        if g[j] == WATER and rng.random() < 0.002:
                            g[j] = ICE               # slowly freezes
                            moved[j] = 1
                continue
