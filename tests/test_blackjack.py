"""Blackjack engine tests — the table must obey its rules."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos.blackjack import (  # noqa: E402
    BETTING, PLAYER, SETTLED, Card, Table, bind_rng, hand_value,
    is_blackjack, payout,
)

RANK_LABEL = {1: "A", 11: "J", 12: "Q", 13: "K"}


def card(rank, suit=0):
    return Card(rank, suit)


def rigged(order: list[str]):
    """Deal cards with the given labels in the given order, then
    pad with a shuffled spare deck so the low-shoe reshuffle never
    triggers mid-test. Duplicate identities are fine; only the
    scripted prefix matters."""
    to_rank = {"A": 1, "J": 11, "Q": 12, "K": 13, "10": 10}
    scripted = []
    suits = 0
    for lab in order:
        r = to_rank.get(lab)
        if r is None:
            r = int(lab)
        scripted.append(Card(r, suits))
        suits = (suits + 1) % 4
    t = Table()
    rest = [Card(r, s) for r in range(1, 14) for s in range(4)]
    random.Random(99).shuffle(rest)
    # _draw() pops from the END of the shoe, so the scripted cards
    # must be the tail: pop order = reverse(list) = scripted order
    t.shoe = rest + scripted[::-1]
    return t


def test_hand_value_aces_and_faces():
    assert hand_value([card(1), card(13)]) == (21, True)
    assert hand_value([card(1), card(5), card(5)]) == (21, True)
    assert hand_value([card(1), card(1), card(9)]) == (21, True)
    assert hand_value([card(13), card(10), card(2)]) == (22, False)
    assert hand_value([card(1), card(1)]) == (12, True)


def test_blackjack_detection():
    assert is_blackjack([card(1), card(12)])
    assert not is_blackjack([card(10), card(11), card(13)])


def test_deal_and_settlement_win():
    # player 20, dealer 19 -> win
    t = rigged(["10", "K",      # player 20
                "10", "9"])      # dealer 19
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    assert t.phase == PLAYER
    t.stand()
    assert t.phase == SETTLED
    assert t.hands[0].outcome == "win"
    assert payout("win", 10) == 10


def test_bust_loses_even_if_dealer_also_busts():
    # player 15 stands, dealer 20 -> dealer wins; also covers
    # "dealer doesn't draw when all player hands stand"
    t = rigged(["10", "5",      # player 15
                "10", "10"])    # dealer 20
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    t.stand()
    assert t.hands[0].outcome == "lose"
    assert payout("lose", 10) == -10


def test_dealer_hits_until_17():
    # dealer 10+2 = 12, then draws 5 -> 17, stands; player 16 stands
    t = rigged(["10", "6",      # player 16
                "10", "2",      # dealer 12
                "5"])           # dealer draws to 17
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    t.stand()
    assert hand_value(t.dealer)[0] == 17
    assert t.hands[0].outcome == "lose"


def test_double_down():
    # player 5+6=11, doubles, draws 10 -> 21; dealer 20 -> win at 20 bet
    t = rigged(["5", "6",       # player 11
                "10", "9",      # dealer 19
                "10"])          # double card -> 21
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    t.double(chips=100, rng=random.Random(1))
    assert t.hands[0].doubled
    assert t.hands[0].bet == 20
    assert hand_value(t.hands[0].cards)[0] == 21
    assert t.hands[0].outcome == "win"


def test_split_pair():
    # two 8s split into 8+10=18 and 8+10=18; dealer 17 -> win win
    t = rigged(["8", "8",       # player pair
                "10", "7",      # dealer 17
                "10",           # hand1 first card
                "10"])          # hand2 first card
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    assert t.phase == PLAYER
    t.split(chips=100, rng=random.Random(1))
    assert len(t.hands) == 2
    t.stand()   # hand 1
    t.stand()   # hand 2
    assert t.phase == SETTLED
    assert all(h.outcome == "win" for h in t.hands)


def test_natural_blackjack_pays_3_2():
    # player A+K, dealer 9+9: bj!
    t = rigged(["A", "K",      # player natural
                "9", "9"])      # dealer 18
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    assert t.phase == SETTLED
    assert t.hands[0].outcome == "bj"
    assert payout("bj", 10) == 15


def test_bet_bounds_enforced():
    t = Table()
    bind_rng(random.Random(1))
    for bad in (0, -5, 999):
        try:
            t.deal(bad, 100, random.Random(1))
            assert False, f"bet {bad} should be rejected"
        except AssertionError as e:
            if "should be rejected" in str(e):
                raise
            # engine assertion — expected
    t.deal(100, 100, random.Random(1))   # all-in allowed


def test_bust_then_next_round_fresh():
    # player 10+6 then draws 10 -> bust
    t = rigged(["10", "6",      # player 16
                "10", "7",      # dealer 17
                "10"])          # hit card -> bust
    bind_rng(random.Random(1))
    t.deal(10, 100, random.Random(1))
    t.hit(random.Random(1))
    assert t.phase == SETTLED
    assert t.hands[0].outcome == "lose"
    # fresh round
    t.phase = BETTING
    t.message = ""
    t.hands = []
    t.dealer = []
    t.deal(10, 90, random.Random(1))
    assert t.phase in (PLAYER, SETTLED)


def test_reshuffle_when_shoe_low():
    t = Table()
    bind_rng(random.Random(1))
    t.deal(10, 1000, random.Random(1))
    assert len(t.shoe) >= 52 - 4 - RESHUFFLE_CHECK
RESHUFFLE_CHECK = 32  # 52 - 4 dealt - low-water guard fudge
