"""Life engine — pure logic, no Qt. Toroidal grid of 0/1.

B3/S23 on a torus. Grids are lists of bytearray rows: fast enough to
step 300x200 at interactive rates in pure Python, and trivially
testable headless.
"""

from __future__ import annotations


def make_grid(w: int, h: int) -> list[bytearray]:
    return [bytearray(w) for _ in range(h)]


def randomize(grid: list[bytearray], density: float = 0.3, rng=None) -> None:
    import random
    rng = rng or random
    for row in grid:
        for x in range(len(row)):
            row[x] = 1 if rng.random() < density else 0


def step(grid: list[bytearray]) -> list[bytearray]:
    """One generation. Returns a NEW grid; input is not mutated."""
    h, w = len(grid), len(grid[0])
    out = make_grid(w, h)
    for y in range(h):
        ru, rd, rm = grid[(y - 1) % h], grid[(y + 1) % h], grid[y]
        for x in range(w):
            left, right = (x - 1) % w, (x + 1) % w
            n = (ru[left] + ru[x] + ru[right]
                 + rm[left] + rm[right]
                 + rd[left] + rd[x] + rd[right])
            out[y][x] = 1 if (n == 3 or (n == 2 and rm[x])) else 0
    return out


def population(grid: list[bytearray]) -> int:
    return sum(sum(row) for row in grid)


# ── pattern stamps: sets of (x, y) offsets ─────────────────────────
GLIDER = {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)}

GOSPER_GUN = {
    (24, 0), (22, 1), (24, 1), (12, 2), (13, 2), (20, 2), (21, 2),
    (34, 2), (35, 2), (11, 3), (15, 3), (20, 3), (21, 3), (34, 3),
    (35, 3), (0, 4), (1, 4), (10, 4), (16, 4), (20, 4), (21, 4),
    (34, 4), (35, 4), (0, 5), (1, 5), (10, 5), (14, 5), (16, 5),
    (17, 5), (22, 5), (24, 5), (10, 6), (16, 6), (24, 6), (11, 7),
    (15, 7), (12, 8), (13, 8), (2, 10), (3, 10), (2, 11), (3, 11),
    (12, 11), (13, 11), (16, 11), (17, 11), (11, 12), (13, 12),
    (16, 12), (17, 12), (16, 13), (17, 13), (35, 13), (24, 14),
    (35, 14), (34, 15), (35, 15), (34, 16), (35, 16),
}

PATTERNS: dict[str, set[tuple[int, int]]] = {
    "glider": GLIDER,
    "gosper gun": GOSPER_GUN,
}


def stamp(grid: list[bytearray], pattern: set[tuple[int, int]],
          ox: int, oy: int) -> None:
    """Stamp a pattern with its origin at (ox, oy); torus-wrapped."""
    h, w = len(grid), len(grid[0])
    for px, py in pattern:
        grid[(oy + py) % h][(ox + px) % w] = 1
