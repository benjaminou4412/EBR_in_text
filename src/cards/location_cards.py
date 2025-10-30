"""
Location set card implementations
"""
from typing import Callable

from src.models import ConstantAbility


from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class AncestorsGrove(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Ancestor's Grove", "Locations")) #type:ignore
        self.art_description = "A small clearing within the dense wood, showered by sunbeams " \
        "that pour in through the thick canopy above. Several structures dot the clearing, " \
        "each consisting of two parts: the lower part a dome the size and shape of an igloo, " \
        "but built with stone, earth, and wood; and the upper part a copse of trees growing " \
        "atop the dome, their roots snaking down over the grassy roof of the dome. Several people " \
        "gather around the entrance to the closest dome, each wearing hooded robes of a different color."

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Choose a card from your ranger discard. Place it on top of your fatigue stack."""
        if engine.state.ranger.discard:
            engine.add_message(f"Challenge (Sun) on {self.title}: Choose a card from your discard pile to move to your fatigue stack.")
            target = engine.card_chooser(engine, engine.state.ranger.discard)
            engine.state.ranger.fatigue_stack.insert(0, target)
            engine.state.ranger.discard.remove(target)
            return True
        else:
            engine.add_message(f"Challenge (Sun) on {self.title}: (ranger discard is empty)")
            return False
    
class BoulderField(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Boulder Field", "Locations")) #type:ignore
        self.art_description = "A wide-open field filled with boulders of all shapes and sizes. " \
        "The skull of a horned being - perhaps a Sitka Buck? - lies in the center of the scene."


    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        return [ConstantAbility(ConstantAbilityType.MODIFY_PRESENCE,
                                source_card_id=self.id,
                                condition_fn=lambda _s, c: CardType.BEING in c.card_types,
                                modifier=ValueModifier(target="presence",
                                                       amount = -1,
                                                       source_id=self.id))]