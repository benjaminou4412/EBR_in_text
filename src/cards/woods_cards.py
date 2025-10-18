"""
Woods terrain set card implementations
"""
from typing import Optional, Callable
from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..utils import get_display_id
from ..engine import GameEngine

class ProwlingWolhund(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Prowling Wolhund", "woods")) #type:ignore

class SitkaBuck(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Buck", "woods")) #type:ignore


class SunberryBramble(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sunberry Bramble", "woods")) #type:ignore

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (AWA + Reason) [2]",
                aspect=Aspect.AWA,
                approach=Approach.REASON,
                verb="Pluck",
                target_provider=None,
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_pluck_success,
                on_fail=lambda _s, _t: None,  # Fatigue not modeled
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_pluck_success(self, state: GameState, effort: int, target_id: Optional[str]) -> None:
        """Pluck test success: add 1 harm"""
        self.add_harm(1)


class SitkaDoe(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Doe", "woods")) #type:ignore

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (SPI + Conflict) [X=presence]",
                aspect=Aspect.SPI,
                approach=Approach.CONFLICT,
                verb="Spook",
                target_provider=None,
                difficulty_fn=lambda _s, _t: 1,
                on_success=self._on_spook_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_spook_success(self, state: GameState, effort: int, target_id: Optional[str]) -> None:
        """Spook test success: move to Along the Way"""
        state.move_card(self.id, Zone.ALONG_THE_WAY)

    def get_symbol_handlers(self) -> dict[Symbol, Callable[[GameEngine], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            Symbol.SUN: self._sun_effect,
            Symbol.MOUNTAIN: self._mountain_effect
        }

    def _sun_effect(self, engine: GameEngine) -> None:
        """Sun effect: If there are 1 or more Sitka Bucks in play >> Move each Sitka Buck within reach"""
        bucks = engine.state.get_cards_by_title("Sitka Buck")
        if bucks is None:
            engine.state.add_message(f"Challenge (Sun) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no Sitka Buck in play)")
        else:
            engine.state.add_message(f"Challenge (Sun) on {get_display_id(engine.state.all_cards_in_play(), self)}: The Sitka Buck are drawn to the doe. They move within reach.")
            for buck in bucks:
                engine.state.move_card(buck.id, Zone.WITHIN_REACH)
            

    def _mountain_effect(self, engine: GameEngine) -> None:
        """Mountain effect: If there is an active predator, exhaust it >> Add harm to this being equal to that predator's presence"""
        predators = engine.state.get_cards_by_trait("Predator")
        if predators is not None:
            active_predators = [predator for predator in predators if predator.exhausted == False]
            if not active_predators:
                engine.state.add_message(f"Challenge (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no active predators in play)")
            else:
                engine.state.add_message(f"Challenge (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: Choose a predator that will exhaust itself and harm Sitka Doe:")
                target_predator = engine.card_chooser(engine.state, active_predators)
                target_predator.exhausted = True
                target_presence = target_predator.get_current_presence()
                if target_presence is not None:
                    #this should always happen
                    self.add_harm(target_presence)
                    engine.state.add_message(f"{get_display_id(active_predators, target_predator)} is now exhausted.")
                    engine.state.add_message(f"{get_display_id(engine.state.all_cards_in_play(), self)} suffered harm equal to {get_display_id(active_predators, target_predator)}'s presence ({target_presence}).")

        else:
            engine.state.add_message(f"Challenge (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no predators in play)")
            


class OvergrownThicket(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Overgrown Thicket", "woods")) #type:ignore

    def get_tests(self) -> list[Action] | None:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (AWA + Exploration)",
                aspect=Aspect.AWA,
                approach=Approach.EXPLORATION,
                verb="Hunt",
                target_provider=None,
                difficulty_fn=lambda _s, _t: 1,
                on_success=self._on_hunt_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_hunt_success(self, state: GameState, effort: int, target_id: Optional[str]) -> None:
        """Hunt test success: add progress equal to effort"""
        self.add_progress(effort)

    def get_symbol_handlers(self) -> dict[Symbol, Callable[[GameEngine], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            Symbol.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, engine: GameEngine) -> None:
        """Mountain effect: discard 1 progress"""
        if self.progress > 0:
            self.progress -= 1
            engine.state.add_message(f"Challenge (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: discards 1 progress (now {self.progress}).")
            curr_presence = self.get_current_presence()
            if curr_presence is not None:
                engine.state.fatigue_ranger(curr_presence)
        else:
            engine.state.add_message(f"Challenge: (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no progress to discard).")
