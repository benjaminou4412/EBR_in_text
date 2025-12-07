"""
Location set card implementations
"""
from typing import Callable

from src.models import ConstantAbility


from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class BiscuitDelivery(Card):
    def __init__(self, fresh: bool = True): #"fresh" flag to prevent infinite recursion
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Biscuit Delivery", "Mission")) #type:ignore
        if fresh:
            self.backside = BiscuitBasket(fresh=False)
            self.backside.backside = self

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(event_type=EventType.TRAVEL,
                              active=lambda e, _c: (
                                  e.state.get_cards_by_title("Hy Pimpot, Chef") is not None and
                                  e.state.location.title == "Lone Tree Station"
                              ),
                              effect_fn=self.resolve_objective_entry,
                              source_card_id=self.id,
                              timing_type=TimingType.BEFORE,
                              test_type=None)]
    
    def resolve_objective_entry(self, eng: GameEngine, effort: int) -> int:
        eng.campaign_guide.resolve_entry(
            entry_number=self.mission_clear_log,
            source_card=self,
            engine=eng,
            clear_type=None
        )
        return 0

    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        """During this mission, use [Campaign Log Entry] 91 instead of the normal entries for Hy Pimpot, Kordo, Nal, and Quisi Vos."""
        return [ConstantAbility(ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY,
                                source_card_id=self.id,
                                condition_fn=lambda _s, c: (
                                    c.title == "Hy Pimpot, Chef" or
                                    c.title == "Kordo, Ranger Veteran" or
                                    c.title == "Spirit Speaker Nal" or
                                    c.title == "Quisi Vos, Rascal"
                                    ),
                                override_entry = "91",
                                modifier=None)]

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: If Quisi Vos is not in the path discard, she is drawn by baked goods. »» Search the Valley set for Quisi and put her into play."""
        return False
    
class BiscuitBasket(Card):
    def __init__(self, fresh: bool = True): #"fresh" flag to prevent infinite recursion
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Biscuit Basket", "Mission")) #type:ignore
        if fresh:
            self.backside = BiscuitDelivery(fresh=False)
            self.backside.backside = self