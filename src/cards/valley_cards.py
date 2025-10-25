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
        self.art_description = "A mature woman with determined eyes, wearing a form-fitting " \
        "suit of what almost looks like padded armor, a hooded cloak, a backpack, and a " \
        "Ranger Badge. The suit is clearly thick enough to offer substantial protection, but her " \
        "body's musclature and strength is apparent beneath its surface, with muscled arms and a " \
        "broad chest. She carries a simple walking stick shaped like a shepherd's crook, " \
        "reinforced by a wrapping around the grip point and what might be bone ornamentation along its hook."

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return []

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
            

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: Add 1[progress] to a path card as Calypsa lends you a hand."""
        path_cards: list[Card] = engine.state.path_cards_in_play() #never empty because Calypsa herself is always a valid target
        engine.add_message(f"Challenge (Mountain) on {self.title}: Calypsa lends you a hand. Choose a path card to add 1 progress to:")
        target: Card = engine.card_chooser(engine,path_cards)
        msg = target.add_progress(1)
        engine.add_message(msg)
        return True

    def _crest_effect(self, engine: GameEngine) -> bool:
        """If there is an active predator, exhaust it. »» Add [harm] to this being equal to that predator's presence."""
        return self.harm_from_predator(engine, ChallengeIcon.CREST, self)