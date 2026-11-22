"""Blackjack tab — felt-simple table, chips cached in memory only.

Chips survive tab switches within a session (the TabWidget keeps the
widget alive) but die with the app — that's the deal we made.
Start bankroll: 1000. Lose it all? It's a toy: click 'rebuy'."""

from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from .blackjack import (
    BETTING, PLAYER, SETTLED, Table, bind_rng, hand_value, payout,
)

FELT = "#173226"
BANKROLL_START = 1000

CARD_W, CARD_H = 64, 92


class CardLabel(QWidget):
    """One cute little card: white face, rank+suit corner."""

    GLYPHS = {0: "♣", 1: "♦", 2: "♥", 3: "♠"}

    def __init__(self, card, hidden=False):
        super().__init__()
        self.card = card
        self.hidden = hidden
        self.setFixedSize(CARD_W, CARD_H)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#00000000"), 0))
        p.setBrush(QColor("#f4f1e6"))
        p.drawRoundedRect(2, 2, CARD_W - 4, CARD_H - 4, 8, 8)
        if self.hidden:
            p.setBrush(QColor("#6d4aff"))
            p.drawRect(10, 10, CARD_W - 20, CARD_H - 20)
        else:
            red = self.card.suit in (1, 2)
            p.setPen(QColor("#b3342f") if red else QColor("#232326"))
            f = p.font()
            f.setPointSize(20)
            f.setBold(True)
            p.setFont(f)
            p.drawText(self.rect().adjusted(6, 4, -6, -4),
                       Qt.AlignTop | Qt.AlignLeft, self.card.label)
            f.setPointSize(13)
            p.setFont(f)
            p.drawText(self.rect().adjusted(6, 4, -6, -4),
                       Qt.AlignBottom | Qt.AlignRight,
                       self.GLYPHS[self.card.suit])
        p.end()


class HandRow(QWidget):
    """A horizontal strip of cards + total, for dealer or one hand."""

    def __init__(self, name: str):
        super().__init__()
        self.name_lbl = QLabel(name)
        self.total_lbl = QLabel("")
        self.cards_lay = QHBoxLayout()
        self.cards_lay.setSpacing(6)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        top = QHBoxLayout()
        top.addWidget(self.name_lbl)
        top.addStretch(1)
        top.addWidget(self.total_lbl)
        outer.addLayout(top)
        outer.addLayout(self.cards_lay)

    def show_cards(self, cards, hide_first=False, outcome=""):
        self.total_lbl.setText("")
        self.cards_lbls = []
        while self.cards_lay.count():
            item = self.cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not cards:
            return
        shown = cards
        if hide_first:
            self.cards_lay.addWidget(CardLabel(cards[0], hidden=True))
            shown = cards[1:]
        for c in shown:
            self.cards_lay.addWidget(CardLabel(c))
        vals = []
        for c in (cards[1:] if hide_first else cards):
            vals.append(c)
        if vals:
            v, soft = hand_value(vals)
            txt = f"{v}" + (" (soft)" if soft else "")
            if outcome:
                txt += f"  {outcome}"
            self.total_lbl.setText(txt)
        self.cards_lay.addStretch(1)


class BlackjackTab(QWidget):
    def __init__(self):
        super().__init__()
        self.rng = random.Random()
        bind_rng(self.rng)
        self.table = Table()
        self.chips = BANKROLL_START
        self.stats = {"hands": 0, "wins": 0, "pushes": 0}

        self.dealer_row = HandRow("dealer")
        self.hand_rows = []
        self.hands_host = QVBoxLayout()
        self.hands_host.setSpacing(10)

        self.msg = QLabel("place your bet")
        self.msg.setStyleSheet("font-size: 15px; font-weight: 600;"
                               " color: #d8d8dc;")
        self.chips_lbl = QLabel()
        self.stats_lbl = QLabel()

        self.bet_spin = QSpinBox()
        self.bet_spin.setRange(1, 9999)
        self.bet_spin.setValue(50)
        self.btn_deal = QPushButton("deal")
        self.btn_hit = QPushButton("hit")
        self.btn_stand = QPushButton("stand")
        self.btn_double = QPushButton("double")
        self.btn_split = QPushButton("split")
        self.btn_rebuy = QPushButton("rebuy")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        for b in (self.btn_deal, self.btn_hit, self.btn_stand,
                  self.btn_double, self.btn_split, self.btn_rebuy,
                  self.bet_spin):
            controls.addWidget(b)
        controls.addStretch(1)
        controls.addWidget(self.chips_lbl)
        controls.addWidget(self.stats_lbl)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        lay.addWidget(self.msg)
        lay.addSpacing(6)
        lay.addWidget(self.dealer_row)
        lay.addLayout(self.hands_host)
        lay.addStretch(1)
        lay.addLayout(controls)

        self.btn_deal.clicked.connect(self._deal)
        self.btn_hit.clicked.connect(lambda: self._act("hit"))
        self.btn_stand.clicked.connect(lambda: self._act("stand"))
        self.btn_double.clicked.connect(lambda: self._act("double"))
        self.btn_split.clicked.connect(lambda: self._act("split"))
        self.btn_rebuy.clicked.connect(self._rebuy)

        self.setStyleSheet(f"""
            QWidget {{ background: {FELT}; }}
            QLabel {{ color: #e6e2cf; }}
            QPushButton {{
                background: #0f2920; color: #e6e2cf;
                border: 1px solid #2c5a44; border-radius: 6px;
                padding: 6px 16px; font-weight: 600;
            }}
            QPushButton:hover {{ border-color: #6d4aff; }}
            QPushButton:disabled {{ color: #5b6f64; border-color: #1d3b30; }}
            QSpinBox {{ background: #0f2920; color: #e6e2cf;
                border: 1px solid #2c5a44; border-radius: 6px;
                padding: 4px 8px; }}
        """)
        self._refresh()

    # -- actions ------------------------------------------------------

    def _deal(self):
        t = self.table
        if t.phase == SETTLED:
            # clear the settled round back to a betting table
            t.phase = BETTING
            t.hands = []
            t.dealer = []
            t.active = 0
            if hasattr(t, "_paid"):
                del t._paid
        bet = self.bet_spin.value()
        if bet > self.chips:
            self.msg.setText("can't cover that bet — rebuy or lower it")
            return
        self.chips -= bet
        t.deal(bet, self.chips + bet, self.rng)
        self._refresh()

    def _act(self, act: str):
        t = self.table
        if t.phase != PLAYER:
            return
        h = t.current_hand()
        try:
            if act == "hit":
                t.hit(self.rng)
            elif act == "stand":
                t.stand()
            elif act == "double":
                if h.bet > self.chips:
                    self.msg.setText("not enough chips to double")
                    return
                self.chips -= h.bet
                t.double(self.chips + h.bet, self.rng)
            elif act == "split":
                if h.bet > self.chips:
                    self.msg.setText("not enough chips to split")
                    return
                self.chips -= h.bet
                t.split(self.chips + h.bet, self.rng)
        except AssertionError as e:
            self.msg.setText(str(e) or "not now")
        self._refresh()

    def _rebuy(self):
        self.chips = BANKROLL_START
        self.table = Table()
        self.msg.setText("fresh bankroll — place your bet")
        self._refresh()

    # -- rendering ----------------------------------------------------

    def _refresh(self):
        t = self.table
        if t.phase == SETTLED:
            self._settle()
        # dealer hole card hidden while the player is still acting
        hole_hidden = t.phase == PLAYER
        self.dealer_row.show_cards(
            t.dealer, hide_first=(len(t.dealer) == 2 and hole_hidden))

        # rebuild hand rows (max 2 — split once)
        while self.hands_host.count():
            item = self.hands_host.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, h in enumerate(t.hands):
            row = HandRow(f"hand {i + 1}"
                          + (" (active)" if t.phase == PLAYER
                             and i == t.active else ""))
            outcome = h.outcome if t.phase == SETTLED else ""
            if t.phase == SETTLED and outcome == "lose" \
                    and hand_value(h.cards)[0] > 21:
                outcome = "bust!"
            row.show_cards(h.cards, outcome=outcome)
            self.hands_host.addWidget(row)

        betting = t.phase == BETTING
        self.btn_deal.setVisible(betting)
        self.btn_rebuy.setVisible(self.chips <= 0 and betting)
        self.btn_hit.setVisible(not betting and t.phase == PLAYER)
        self.btn_stand.setVisible(t.phase == PLAYER)
        can_double = (t.phase == PLAYER and len(t.hands) == 1
                      and len(t.current_hand().cards) == 2
                      and t.current_hand().bet <= self.chips)
        self.btn_double.setVisible(can_double)
        can_split = (t.phase == PLAYER and len(t.hands) == 1
                     and len(t.current_hand().cards) == 2
                     and t.current_hand().cards[0].rank
                     == t.current_hand().cards[1].rank
                     and t.current_hand().bet <= self.chips)
        self.btn_split.setVisible(can_split)
        self.bet_spin.setVisible(betting)

        if t.phase == PLAYER:
            self.msg.setText("your move")
        self.chips_lbl.setText(f"chips: {self.chips}")
        s = self.stats
        self.stats_lbl.setText(
            f"hands {s['hands']} · won {s['wins']} · pushed {s['pushes']}")

    def _settle(self):
        """Apply payouts once per settle; guard the double-tap."""
        t = self.table
        if getattr(t, "_paid", False):
            return
        t._paid = True
        for h in t.hands:
            self.chips += h.bet + payout(h.outcome, h.bet)
            self.stats["hands"] += 1
            if h.outcome in ("win", "bj"):
                self.stats["wins"] += 1
            elif h.outcome == "push":
                self.stats["pushes"] += 1


