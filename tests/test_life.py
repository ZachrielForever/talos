"""Headless Life engine tests — the toy's rules must be exact."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos import life  # noqa: E402


def test_blinker_oscillates():
    """The period-2 oscillator: vertical bar -> horizontal bar -> back."""
    g = life.make_grid(5, 5)
    life.stamp(g, {(1, 0), (1, 1), (1, 2)}, 2, 1)  # vertical blinker at x=3
    g2 = life.step(g)
    # center survives, neighbors flip: horizontal bar at y=2, x=2..4
    assert life.population(g) == 3
    assert life.population(g2) == 3
    assert [(x, y) for y in range(5) for x in range(5) if g2[y][x]] == \
        [(2, 2), (3, 2), (4, 2)]
    g3 = life.step(g2)
    assert [(x, y) for y in range(5) for x in range(5) if g3[y][x]] == \
        [(3, 1), (3, 2), (3, 3)]


def test_block_is_still_life():
    """The 2x2 block: B3/S23 leaves it untouched forever."""
    g = life.make_grid(6, 6)
    life.stamp(g, {(0, 0), (1, 0), (0, 1), (1, 1)}, 2, 2)
    assert life.step(g) == g


def test_glider_moves_on_torus():
    """A glider displaces diagonally every 4 generations."""
    g = life.make_grid(20, 20)
    life.stamp(g, life.GLIDER, 5, 5)
    p0 = life.population(g)
    for _ in range(4):
        g = life.step(g)
    assert life.population(g) == p0  # gliders don't die
    # displaced by (1, 1): check a cell that must now be alive
    assert any(g[(5 + dy + 1) % 20][(5 + dx + 1) % 20]
               for dx, dy in life.GLIDER)


def test_lonely_cell_dies():
    """Underpopulation: a lone cell has zero neighbors and vanishes."""
    g = life.make_grid(5, 5)
    g[2][2] = 1
    assert life.population(life.step(g)) == 0


def test_overcrowding_kills():
    """Overpopulation: a 3x3 block center dies, ring births a square."""
    g = life.make_grid(7, 7)
    for y in range(3):
        for x in range(3):
            g[2 + y][2 + x] = 1
    g2 = life.step(g)
    assert g2[3][3] == 0  # center had 8 neighbors


def test_stamp_wraps_on_torus():
    """Stamping near the edge wraps instead of IndexError."""
    g = life.make_grid(5, 5)
    life.stamp(g, {(4, 4)}, 0, 0)  # stamps at (4, 4) via wrap
    assert g[4][4] == 1
    life.stamp(g, {(0, 0)}, 4, 4)  # wraps to (4, 4) too
    assert g[4][4] == 1  # unchanged, no crash


def test_step_does_not_mutate_input():
    g = life.make_grid(6, 6)
    life.stamp(g, life.GLIDER, 1, 1)
    before = [bytes(r) for r in g]
    life.step(g)
    assert [bytes(r) for r in g] == before


def test_randomize_is_deterministic_with_seed():
    g = life.make_grid(10, 10)
    import random
    life.randomize(g, rng=random.Random(42))
    snap = [bytes(r) for r in g]
    g2 = life.make_grid(10, 10)
    life.randomize(g2, rng=random.Random(42))
    assert [bytes(r) for r in g2] == snap
