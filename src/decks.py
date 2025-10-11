from __future__ import annotations
from .cards import SitkaBuck, OvergrownThicket
from .models import Card



def build_woods_path_deck() -> list[Card]:
    deck: list[Card] = []
    sb = SitkaBuck()
    ot = OvergrownThicket()
    deck.append(sb)
    deck.append(ot)
    return deck

