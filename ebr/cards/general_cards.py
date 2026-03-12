"""
General set card implementations
"""
from typing import Callable

from ..models import *
from ..json_loader import load_card_fields  # type:ignore
from ..engine import GameEngine


class CerberusianCyclone(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Cerberusian Cyclone", "general"))  # type:ignore
        self.art_description = (
            "A trio of violently spinning columns of air tears across the landscape, "
            "kicking up dust and debris and uprooting small trees. The funnels fuse into "
            "a massive vortex at their base."
        )

    def get_tests(self) -> list[Action]:
        """AWA + [conflict]: Evade [2] the violently swirling columns of air to discard 1 strength
        for every 2 effort. If there is no strength on this feature, discard it."""
        return [
            Action(
                id=f"test-evade-{self.id}",
                name=f"{self.title} (AWA + Conflict) [2]",
                aspect=Aspect.AWA,
                approach=Approach.CONFLICT,
                verb="Evade",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_evade_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_evade_success(self, engine: GameEngine, effort: int, _card: Card | None) -> None:
        """Discard 1 strength for every 2 effort. If no strength remains, discard this feature."""
        strength_to_remove = effort // 2
        if strength_to_remove > 0 and self.has_unique_token_type("strength"):
            current = self.unique_tokens.get("strength", 0)
            actual_removed = min(strength_to_remove, current)
            if actual_removed > 0:
                self.remove_unique_tokens(engine, "strength", actual_removed)
        # Check if no strength remains
        remaining = self.unique_tokens.get("strength", 0)
        if remaining <= 0:
            engine.add_message(f"No strength remaining on {self.title} - discarding it!")
            self.discard_from_play(engine)

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect,
        }

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Move this feature. If you move it to an area with no other cards, add 1 strength."""
        self_display = engine.get_display_id_cached(self)
        self.move_self(engine)
        target_area = engine.state.get_card_area_by_id(self.id)
        # Check if the target area has no other cards besides this one
        cards_in_area = [c for c in engine.state.areas[target_area] if c.id != self.id]
        if not cards_in_area:
            engine.add_message(f"No other cards in {target_area.value} - adding 1 strength to {self_display}.")
            self.add_unique_tokens(engine, "strength", 1)
        return True

    def _crest_effect(self, engine: GameEngine) -> bool:
        """Move a card in the same area as this feature.
        If you move it within reach of a Ranger, it fatigues that Ranger."""
        self_display = engine.get_display_id_cached(self)
        current_area = engine.state.get_card_area_by_id(self.id)
        if current_area is None:
            return False
        # Find other cards in the same area
        same_area_cards = [c for c in engine.state.areas[current_area] if c.id != self.id]
        if not same_area_cards:
            engine.add_message(f"Challenge (Crest) on {self_display}: No other cards in {current_area.value} to move.")
            return False
        engine.add_message(f"Challenge (Crest) on {self_display}: Choose a card in {current_area.value} to move:")
        target = engine.card_chooser(engine, same_area_cards)
        target_display = engine.get_display_id_cached(target)
        # Choose destination area
        areas = [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH, Area.PLAYER_AREA]
        other_areas = [a for a in areas if a != current_area]
        area_names = [a.value for a in other_areas]
        chosen_name = engine.option_chooser(engine, area_names, f"Move {target_display} to which area?")
        dest_area = next(a for a in other_areas if a.value == chosen_name)
        engine.move_card(target.id, dest_area)
        # If moved within reach of a Ranger, fatigue that Ranger
        if dest_area == Area.WITHIN_REACH:
            presence = target.get_current_presence(engine)
            fatigue_amount = presence if presence is not None and presence > 0 else 1
            engine.state.ranger.fatigue(engine, fatigue_amount)
        return True


class BallLightning(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Ball Lightning", "general"))  # type:ignore
        self.art_description = (
            "A crackling sphere of bright electrical energy flits through the trees, "
            "swirling with intense pale-blue volatility. It leaves a wispy blue trail behind it as it moves."
        )

    def on_harm_clear(self, engine: GameEngine):
        """Clear [harm]: If within reach of a Ranger, suffer 2 injuries.
        If along the way, remove all progress from the location."""
        current_area = engine.state.get_card_area_by_id(self.id)
        if current_area == Area.WITHIN_REACH:
            engine.add_message("Ball Lightning was cleared by harm while within reach! Ranger suffers 2 injuries!")
            engine.state.ranger.injure(engine)
            engine.state.ranger.injure(engine)
        elif current_area == Area.ALONG_THE_WAY:
            location = engine.state.location
            if location.progress > 0:
                engine.add_message(f"Ball Lightning was cleared by harm while along the way! Removing all progress from {location.title}.")
                location.remove_progress(location.progress)
            else:
                engine.add_message("Ball Lightning was cleared by harm while along the way! (Location has no progress to remove.)")

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.CREST: self._crest_effect,
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Move this feature."""
        self.move_self(engine)
        return True

    def _crest_effect(self, engine: GameEngine) -> bool:
        """Add 1 harm to this feature."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Crest) on {self_display}: Adding 1 harm.")
        engine.add_message(self.add_harm(1))
        return True
