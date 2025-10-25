"""
Valley set card implementations
"""
from typing import Callable
from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class CalypsaRangerMentor(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Calypsa, Ranger Mentor", "Valley")) #type:ignore
        self.keywords = {Keyword.FRIENDLY}

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return []

    def get_symbol_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
            

    def _mountain_effect(self, engine: GameEngine) -> None:
        """Mountain effect: Add 1[progress] to a path card as Calypsa lends you a hand."""
        path_cards: list[Card] = engine.state.path_cards_in_play() #never empty because Calypsa herself is always a valid target
        engine.add_message(f"Challenge (Mountain) on {self.title}: Calypsa lends you a hand. Choose a path card to add 1 progress to:")
        target: Card = engine.card_chooser(engine,path_cards) 
        target.add_progress(1)

    def _crest_effect(self, engine: GameEngine) -> None:
        """If there is an active predator, exhaust it. »» Add [harm] to this being equal to that predator's presence."""
        self.harm_from_predator(engine, ChallengeIcon.CREST)