"""
Woods terrain set card implementations
"""
from typing import Optional, Callable
from ..models import *
from ..json_loader import load_card_fields #type:ignore


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

    def get_symbol_handlers(self) -> dict[Symbol, Callable[[GameState], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            Symbol.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, state: GameState) -> None:
        """Mountain symbol: discard 1 progress"""
        if self.progress > 0:
            self.progress -= 1
            state.add_message(f"Challenge: Mountain on {self.title} discards 1 progress (now {self.progress}).")
        else:
            state.add_message(f"Challenge: Mountain on {self.title} (no progress to discard).")
