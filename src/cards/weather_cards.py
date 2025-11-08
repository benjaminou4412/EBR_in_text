"""
Location set card implementations
"""
from typing import Callable

from src.models import EventListener

from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class APerfectDay(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("A Perfect Day", "Weather")) #type:ignore
        self.art_description = "A gentle pair of streams runs amongst a small gathering " \
        "of stylized trees, joining together in the distance. The sun just peeks out over " \
        "the treetops amidst a clear blue sky, flanked by a smattering of thinning clouds."

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: If this test added progress, add 1 additional progress."""
        if engine.last_test_added_progress and engine.last_test_target:
            engine.add_message(f"Challenge (Mountain) on {self.title}: The test added progress, so add 1 additional progress.")
            msg = engine.last_test_target.add_progress(1)
            engine.add_message(msg)
            return True
        else:
            engine.add_message(f"Challenge (Mountain) on {self.title}: The test did not add progress.")
            return False
    
    def flip(self, engine:GameEngine):
        self.discard_from_play(engine) #return value ignored for custom messaging
        new_weather = MiddaySun()
        engine.state.areas[Area.SURROUNDINGS].insert(0, new_weather)
        engine.state.weather = new_weather
        engine.add_message(f"A Perfect Day flips into Midday Sun.")
        new_weather.enters_play(engine, Area.SURROUNDINGS)

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              self._tick_down_clouds,
                              self.id,
                              TimingType.WHEN
                              )]
    
    def _tick_down_clouds(self, engine: GameEngine, effort: int) -> None:
        self.remove_unique_tokens("Cloud", 1)
        if self.get_unique_token_count("Cloud") == 0:
            self.flip(engine)

    
class MiddaySun(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Midday Sun", "Weather")) #type:ignore
        self.art_description = "The sun blazes high above mountain peaks, sending tendrils of heat " \
        "snaking through a sky coated with heat-haze."
    
    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Suffer 1 fatigue."""
        engine.add_message(f"Challenge (Sun) on {self.title}: Suffer 1 fatigue.")
        engine.fatigue_ranger(engine.state.ranger, 1)
        return True #TODO: return false if fatigue is cancelled
    
    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (FOC + Reason) [2]",
                aspect=Aspect.FOC,
                approach=Approach.REASON,
                verb="Locate",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_locate_success,
                on_fail=None,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_locate_success(self, engine: GameEngine, _effort: int, _target: Card | None) -> None:
        self.add_unique_tokens("Cloud", 1)
        engine.soothe_ranger(engine.state.ranger, 1)
        return None
    
    def flip(self, engine:GameEngine):
        self.discard_from_play(engine) #return value ignored for custom messaging
        new_weather = APerfectDay()
        engine.state.areas[Area.SURROUNDINGS].insert(0, new_weather)
        engine.state.weather = new_weather
        new_weather.enters_play(engine, Area.SURROUNDINGS)
        engine.add_message(f"Midday Sun flips into A Perfect Day.")

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              self._tick_up_clouds,
                              self.id,
                              TimingType.WHEN
                              )]
    
    def _tick_up_clouds(self, engine: GameEngine, effort: int) -> None:
        self.add_unique_tokens("Cloud", 1)
        if self.get_unique_token_count("Cloud") >= 3:
            self.flip(engine)