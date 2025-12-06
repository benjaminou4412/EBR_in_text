"""
Valley set card implementations
"""
from typing import Callable

from src.models import EventListener


from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class HyPimpotChef(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Hy Pimpot, Chef", "Lone Tree Station")) #type:ignore
        self.keywords = {Keyword.FRIENDLY}
        self.art_description = "A heavy-set man with a friendly smile and droopy eyes. His face almost resembles " \
        "a walrus's, the edges of his lips curled upward towards rounded cheeks in an affable manner. He wears a simple " \
        "detached hood with a brim over his head and ears, a thick padded jacket, and a belt pouch slung over his torso " \
        "filled with plucked herbs and vials of ingredients."

    

