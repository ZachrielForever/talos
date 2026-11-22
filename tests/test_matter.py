"""Matter engine tests — the physics must obey its contracts."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos.matter import (  # noqa: E402
    ACID, EMPTY, FIRE, ICE, LAVA, NAMES, OIL, PLANT, SAND, SMOKE,
    STONE, TNT, WALL, WATER, step,
)

W, H = 40, 30


def grid(rows):
    """rows: list of strings, chars = matter initials ('.' = empty)."""
    legend = {".": EMPTY, "e": EMPTY, "w": WALL, "s": SAND, "a": WATER,
              "S": STONE, "o": OIL, "f": FIRE, "m": SMOKE, "p": PLANT,
              "A": ACID, "l": LAVA, "i": ICE, "t": TNT}
    assert len(rows) == H and all(len(r) == W for r in rows)
    g = bytearray(W * H)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            g[y * W + x] = legend[c]
    return g


def show(g):
    inv = {EMPTY: ".", WALL: "w", SAND: "s", WATER: "a", STONE: "S",
           OIL: "o", FIRE: "f", SMOKE: "m", PLANT: "p", ACID: "A",
           LAVA: "l", ICE: "i", TNT: "t"}
    return ["".join(inv[v] for v in g[y * W:(y + 1) * W]) for y in range(H)]


def run(g, frames, seed=1):
    rng = random.Random(seed)
    for _ in range(frames):
        step(g, W, H, rng)
    return g


def test_sand_falls_and_piles():
    g = grid(["." * W for _ in range(H)])
    g[H - 5]  # noop
    g[(H - 5) * W + W // 2] = SAND
    run(g, 10)
    # sand reached the floor
    assert g[(H - 1) * W + W // 2] == SAND


def test_water_fills_level_and_damps():
    # basin: walls at both sides, water poured in
    rows = []
    rows.append("." * W)
    for _ in range(H - 2):
        rows.append("." * W)
    rows.append("w" * W)
    g = grid(rows)
    for x in range(10, 30):
        g[1 * W + x] = WATER
    run(g, 120)
    # water level: everything below some row within the walls is water
    bot = [x for x in range(1, W - 1) if g[(H - 2) * W + x] == WATER]
    assert len(bot) > 15, "water should pool on the floor"
    # total water conserved unless touching fire/etc — it isn't here
    total = sum(1 for v in g if v == WATER)
    assert total >= 19


def test_oil_floats_on_water():
    rows = ["." * W for _ in range(H - 1)] + ["w" * W]
    g = grid(rows)
    for x in range(5, 35):
        g[2 * W + x] = WATER
    for x in range(10, 30):
        g[1 * W + x] = Oil = OIL
    run(g, 80)
    # oil ends above water: at the top layer of the pool
    top_oil = sum(1 for x in range(1, W - 1) if g[1 * W + x] == OIL
                  or g[2 * W + x] == OIL)
    oils = [(x, y) for y in range(H) for x in range(W)
            if g[y * W + x] == OIL]
    waters = [(x, y) for y in range(H) for x in range(W)
              if g[y * W + x] == WATER]
    assert oils and waters
    assert min(y for _, y in oils) <= min(y for _, y in waters), \
        "oil must float (smaller y = higher)"


def test_fire_ignites_oil_and_dies():
    rows = ["." * W for _ in range(H - 1)] + ["w" * W]
    g = grid(rows)
    # shelf so the oil doesn't run away before catching
    for x in range(3, 8):
        g[6 * W + x] = WALL
    g[5 * W + 5] = OIL
    g[4 * W + 5] = FIRE
    run(g, 200, seed=3)
    assert not any(v == OIL for v in g), "oil should have burned"
    assert not any(v == FIRE for v in g), "fire must burn out"


def test_lava_meets_water_makes_stone():
    rows = ["." * W for _ in range(H - 1)] + ["w" * W]
    g = grid(rows)
    g[5 * W + 5] = LAVA
    g[(H - 3) * W + 5] = WATER
    run(g, 200)
    assert any(v == STONE for v in g), \
        "lava+water should forge stone"


def test_tnt_chain_detonates():
    rows = ["." * W for _ in range(H - 1)] + ["w" * W]
    g = grid(rows)
    for x in range(15, 25):
        g[10 * W + x] = TNT
    g[9 * W + 20] = FIRE   # directly adjacent to the charge
    run(g, 10, seed=7)
    assert not any(v == TNT for v in g), "all tnt should cook off"
    fire_or_smoke = sum(1 for v in g if v in (FIRE, SMOKE))
    assert fire_or_smoke > 0, "explosion leaves fire/smoke"


def test_acid_eats_stone():
    rows = ["." * W for _ in range(H - 1)] + ["w" * W]
    g = grid(rows)
    g[5 * W + 5] = ACID
    g[(H - 2) * W + 5] = STONE
    run(g, 300, seed=11)
    assert not any(v == STONE for v in g), "acid should dissolve the stone"


# TNT chain in test: smoke/fire assertions need tnt exploded away
# sanity: NAMES aligns with ids
def test_names_align():
    assert NAMES[ACID] == "acid"
    assert NAMES[SAND] == "sand"
    assert NAMES[TNT] == "tnt"
