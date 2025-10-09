from __future__ import annotations
from typing import List
from .models import PathCard
from .cards import SitkaBuck, OvergrownThicket



def build_woods_path_deck() -> List[PathCard]:
    deck: List[PathCard] = []
    sb = SitkaBuck()
    ot = OvergrownThicket()
    deck.append(sb)
    deck.append(ot)
    return deck

