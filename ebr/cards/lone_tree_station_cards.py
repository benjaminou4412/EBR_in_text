"""
Valley set card implementations
"""
from typing import Callable

from ebr.models import EventListener


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

    def get_tests(self) -> list[Action]:
        """AWA + [reason]: Harvest [2] local plants for the stew to attach a flora facedown to Hy.
        If there are 3 flora attached to Hy, he prepares his famous stew: [Campaign Log Entry] 47.4"""
        return [
            Action(
                id=f"test-harvest-{self.id}",
                name=f"{self.title} (AWA + Reason) [2]",
                aspect=Aspect.AWA,
                approach=Approach.REASON,
                verb="Harvest",
                target_provider=lambda s: [card for card in s.all_cards_in_play() if card.has_trait("Flora")],
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_harvest_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_harvest_success(self, engine: GameEngine, _effort: int, target: Card | None) -> None:
        """Attach the targeted flora facedown to Hy. If 3 flora attached, trigger entry 47.4."""
        if target is None:
            raise RuntimeError("Harvest test requires a flora target!")
        facedown_flora = target.flip(engine)
        engine.attach(facedown_flora, self)

        flora_count = sum(1 for aid in self.attached_card_ids
                         if isinstance(card := engine.state.get_card_by_id(aid), FacedownCard)
                         and card.backside is not None and card.backside.has_trait("Flora"))
        engine.add_message(f"{flora_count} flora now attached to {self.title}.")

        if flora_count >= 3:
            engine.add_message(f"{self.title} has 3 flora attached! He prepares his famous stew.")
            engine.campaign_guide.resolve_entry("47.4", self, engine, None)

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Crest: If there is an active predator, exhaust it. Add harm to this being equal to that predator's presence."""
        return {
            ChallengeIcon.CREST: self._crest_effect
        }

    def _crest_effect(self, engine: GameEngine) -> bool:
        return self.harm_from_predator(engine, ChallengeIcon.CREST, self)


