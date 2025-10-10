"""
Woods terrain set card implementations
"""
from ..models import *
from ..json_loader import load_card_fields #type:ignore


class SitkaBuck(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Buck", "woods")) #type:ignore


class OvergrownThicket(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Overgrown Thicket", "woods")) #type:ignore
