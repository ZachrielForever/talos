"""Blackjack engine — pure logic, no Qt, no disk.

Rules (house-style, kept easy):
  - single deck reshuffled when fewer than 20 cards remain
  - dealer hits until 17 (stands on soft 17)
  - blackjack pays 3:2; dealer blackjack pushes a player blackjack
  - actions: hit, stand, double (first two cards only),
    split (two equal-rank cards, once per hand — no resplits)

Phases: BETTING -> PLAYER -> DEALER -> SETTLED -> BETTING ...
Chips are the caller's business; the engine only prices outcomes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

BETTING, PLAYER, DEALER, SETTLED = "betting", "player", "dealer", "settled"

RESHUFFLE_AT = 20


@dataclass(frozen=True)
class Card:
    rank: int          # 1..13 (1 = ace)
    suit: int          # 0..3

    @property
    def label(self) -> str:
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return names.get(self.rank, str(self.rank))


def hand_value(cards: list[Card]) -> tuple[int, bool]:
    """Returns (total, is_soft). Aces: 11 then demoted as needed."""
    total = 0
    aces = 0
    for c in cards:
        if c.rank == 1:
            aces += 1
            total += 11
        elif c.rank >= 10:
            total += 10
        else:
            total += c.rank
    soft = aces > 0
    while total > 21 and aces:
        total -= 10
        aces -= 1
        soft = aces > 0
    return total, soft


def is_blackjack(cards: list[Card]) -> bool:
    return len(cards) == 2 and hand_value(cards)[0] == 21


@dataclass
class HandState:
    cards: list[Card] = field(default_factory=list)
    bet: int = 0
    done: bool = False
    doubled: bool = False
    outcome: str = ""   # "win"/"lose"/"push"/"bj" once settled


@dataclass
class Table:
    """One player's round state."""
    phase: str = BETTING
    shoe: list[Card] = field(default_factory=list)
    hands: list[HandState] = field(default_factory=list)
    active: int = 0              # index into hands during PLAYER
    dealer: list[Card] = field(default_factory=list)
    message: str = "place your bet"

    def __post_init__(self):
        if not self.shoe:
            self.reset_shoe(random.Random())

    def reset_shoe(self, rng):
        self.shoe = [Card(r, s) for r in range(1, 14) for s in range(4)]
        rng.shuffle(self.shoe)

    def _draw(self, rng) -> Card:
        if len(self.shoe) < RESHUFFLE_AT:
            self.reset_shoe(rng)
        return self.shoe.pop()

    # -- lifecycle --------------------------------------------------

    def deal(self, bet: int, chips: int, rng):
        assert self.phase == BETTING
        assert 0 < bet <= chips, "bet within chips only"
        self.hands = [HandState(bet=bet)]
        self.dealer = []
        self.active = 0
        h = self.hands[0]
        for _ in range(2):
            h.cards.append(self._draw(rng))
        self.dealer.append(self._draw(rng))
        self.dealer.append(self._draw(rng))
        if is_blackjack(h.cards) or is_blackjack(self.dealer):
            self.phase = SETTLED
            self.message = self._settle_all()
        else:
            self.phase = PLAYER
            self.message = "hit or stand?"

    def current_hand(self) -> HandState:
        return self.hands[self.active]

    # -- player actions ---------------------------------------------

    def hit(self, rng):
        assert self.phase == PLAYER
        h = self.current_hand()
        h.cards.append(self._draw(rng))
        v = hand_value(h.cards)[0]
        if v > 21:
            h.done = True
            h.outcome = "bust"
            self._advance()
        elif v == 21:
            h.done = True
            self._advance()

    def stand(self):
        assert self.phase == PLAYER
        self.current_hand().done = True
        self._advance()

    def double(self, chips: int, rng):
        assert self.phase == PLAYER
        h = self.current_hand()
        assert len(h.cards) == 2, "double on first two cards only"
        assert h.bet * 2 <= chips, "not enough chips to double"
        h.bet *= 2
        h.doubled = True
        h.cards.append(self._draw(rng))
        h.done = True
        self._advance()

    def split(self, chips: int, rng):
        assert self.phase == PLAYER
        h = self.current_hand()
        assert len(self.hands) == 1 and len(h.cards) == 2, \
            "split once, on the first two cards"
        assert h.cards[0].rank == h.cards[1].rank, "pairs only"
        assert h.bet * 2 <= chips, "not enough chips to split"
        second = HandState(bet=h.bet)
        second.cards.append(h.cards.pop())
        h.cards.append(self._draw(rng))
        second.cards.append(self._draw(rng))
        self.hands.append(second)

    def _advance(self):
        # skip finished hands; dealer plays when all are done
        while self.active < len(self.hands) \
                and self.hands[self.active].done:
            self.active += 1
        if self.active >= len(self.hands):
            self.phase = DEALER
            dv = hand_value(self.dealer)[0]
            # dealer only draws if at least one live player hand
            live = any(h.outcome != "bust" for h in self.hands)
            while live and dv < 17:
                self.dealer.append(self._draw(_rng_holder[0]))
                dv = hand_value(self.dealer)[0]
            self.phase = SETTLED
            self.message = self._settle_all()
        else:
            self.message = "next hand: hit or stand?"

    # -- settlement ---------------------------------------------------

    def _settle_all(self) -> str:
        d_bj = is_blackjack(self.dealer)
        dv = hand_value(self.dealer)[0]
        parts = []
        for i, h in enumerate(self.hands):
            pv = hand_value(h.cards)[0]
            if h.outcome == "bust":
                h.outcome = "lose"
                parts.append(f"h{i+1}: bust")
            elif is_blackjack(h.cards) and not d_bj:
                h.outcome = "bj"
                parts.append(f"h{i+1}: blackjack!")
            elif d_bj and not is_blackjack(h.cards):
                h.outcome = "lose"
                parts.append(f"h{i+1}: dealer blackjack")
            elif d_bj and is_blackjack(h.cards):
                h.outcome = "push"
                parts.append(f"h{i+1}: push")
            elif dv > 21 or pv > dv:
                h.outcome = "win"
                parts.append(f"h{i+1}: win")
            elif pv == dv:
                h.outcome = "push"
                parts.append(f"h{i+1}: push")
            else:
                h.outcome = "lose"
                parts.append(f"h{i+1}: lose")
        return " · ".join(parts)


def payout(outcome: str, bet: int) -> int:
    """Net chips awarded (positive win, 0 push, negative loss)."""
    if outcome == "bj":
        return bet * 3 // 2
    if outcome == "win":
        return bet
    if outcome == "push":
        return 0
    return -bet


_rng_holder: list = []


def bind_rng(rng):
    """The _advance dealer loop needs an rng; the tab binds one."""
    _rng_holder.clear()
    _rng_holder.append(rng)
