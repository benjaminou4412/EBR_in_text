"""
Weather card implementations
"""
from typing import Callable

from ebr.models import EventListener

from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class APerfectDay(Card):
    def __init__(self, fresh: bool = True): #"fresh" flag to prevent infinite recursion
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("A Perfect Day", "Weather")) #type:ignore
        self.art_description = "A gentle pair of streams runs amongst a small gathering " \
        "of stylized trees, joining together in the distance. The sun just peeks out over " \
        "the treetops amidst a clear blue sky, flanked by a smattering of thinning clouds."
        if fresh:
            self.backside = MiddaySun(fresh=False)
            self.backside.backside = self



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


    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._tick_down_clouds,
                              self.id,
                              TimingType.WHEN
                              )]

    def _tick_down_clouds(self, engine: GameEngine, effort: int) -> int:
        self.remove_unique_tokens(engine, "Cloud", 1)
        if self.get_unique_token_count("Cloud") == 0:
            self.flip(engine)
        return 0 #doesn't involve effort

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside


class MiddaySun(Card):
    def __init__(self, fresh: bool = True): #"fresh" flag to prevent infinite recursion
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Midday Sun", "Weather")) #type:ignore
        self.art_description = "The sun blazes high above mountain peaks, sending tendrils of heat " \
        "snaking through a sky coated with heat-haze."
        if fresh:
            self.backside = APerfectDay(fresh=False)
            self.backside.backside = self

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Suffer 1 fatigue."""
        engine.add_message(f"Challenge (Sun) on {self.title}: Suffer 1 fatigue.")
        engine.state.ranger.fatigue(engine, 1)
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
        self.add_unique_tokens(engine, "Cloud", 1)
        engine.state.ranger.soothe(engine, 1)
        return None


    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._tick_up_clouds,
                              self.id,
                              TimingType.WHEN
                              )]

    def _tick_up_clouds(self, engine: GameEngine, effort: int) -> int:
        self.add_unique_tokens(engine, "Cloud", 1)
        if self.get_unique_token_count("Cloud") >= 3:
            self.flip(engine)
        return 0 #doesn't involve effort

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside


class Downpour(Card):
    """Downpour weather card - has Inclement trait, uses rain tokens.

    Sun challenge: Discard 1 rain. Each ranger suffers 1 fatigue.
    If no rain remaining, flip into Gathering Storm."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Downpour", "Weather")) #type:ignore
        self.art_description = "A thick gathering of clouds hangs over a lone tree. Sheets of rain cover the sky and earth."
        if fresh:
            self.backside = GatheringStorm(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Discard 1 rain. Each ranger suffers 1 fatigue. If no rain remaining, flip."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Sun) on {self_display}: Discard 1 rain. Each ranger suffers 1 fatigue.")
        self.remove_unique_tokens(engine, "rain", 1)
        engine.state.ranger.fatigue(engine, 1)
        if self.get_unique_token_count("rain") <= 0:
            engine.add_message(f"No rain remaining on {self_display} - flipping into Gathering Storm.")
            self.flip(engine)
        return True


class GatheringStorm(Card):
    """Gathering Storm - backside of Downpour, uses rain tokens.

    Test: FOC + Reason: Shelter [2] to discard 1 rain for every 2 effort.
    Refresh: Add 2 rain. At 4+, move all prey to along the way, exhaust role, flip into Downpour."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Gathering Storm", "Weather")) #type:ignore
        self.art_description = "Wispy clouds over a mountain peak are forming into a dense and ominous shape." 
        if fresh:
            self.backside = Downpour(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_tests(self) -> list[Action]:
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (FOC + Reason) [2]",
                aspect=Aspect.FOC,
                approach=Approach.REASON,
                verb="Shelter",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_shelter_success,
                on_fail=None,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_shelter_success(self, engine: GameEngine, effort: int, _target: Card | None) -> None:
        """Discard 1 rain for every 2 effort."""
        rain_to_remove = effort // 2
        if rain_to_remove > 0 and self.has_unique_token_type("rain"):
            current = self.unique_tokens.get("rain", 0)
            actual = min(rain_to_remove, current)
            if actual > 0:
                self.remove_unique_tokens(engine, "rain", actual)

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._refresh_effect,
                              self.id,
                              TimingType.WHEN
                              )]

    def _refresh_effect(self, engine: GameEngine, effort: int) -> int:
        """Add 2 rain. If 4+, move all prey to along the way, exhaust role, flip into Downpour."""
        self_display = engine.get_display_id_cached(self)
        self.add_unique_tokens(engine, "rain", 2)
        if self.get_unique_token_count("rain") >= 4:
            engine.add_message(f"4+ rain on {self_display}! A peal of thunder fills the air, and a heavy rain begins.")
            # Move all prey to along the way (from within reach)
            prey_within_reach = [c for c in engine.state.areas[Area.WITHIN_REACH]
                                 if c.has_trait("Prey")]
            for prey in prey_within_reach:
                engine.move_card(prey.id, Area.ALONG_THE_WAY)
            # Exhaust role
            engine.add_message(engine.state.role_card.exhaust())
            # Flip into Downpour
            self.flip(engine)
        return 0


class HowlingWinds(Card):
    """Howling Winds weather card - has Inclement trait, uses wind tokens.

    Arrival Setup: Shuffle a Cerberusian Cyclone into the path deck.
    Refresh: If 3+ wind, remove them, draw 1 extra path next round, flip into Thunderhead.
    Sun challenge: Add 2 wind. May suffer up to 2 fatigue to add 1 fewer wind per fatigue."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Howling Winds", "Weather")) #type:ignore
        self.art_description = "The sun and distance peaks are only barely visible now as violent gusts tear down from cloudy skies." 
        self._extra_path_draw_pending = False
        if fresh:
            self.backside = Thunderhead(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_arrival_setup_cards(self, engine: GameEngine) -> list[Card]:
        """Arrival Setup: Search the General set for a Cerberusian Cyclone and shuffle it into the path deck."""
        cyclone = engine.state.collection.checkout_by_title("General", "Cerberusian Cyclone")
        if cyclone is not None:
            engine.add_message(f"Howling Winds: Shuffling a Cerberusian Cyclone into the path deck.")
            return [cyclone]
        engine.add_message(f"Howling Winds: No Cerberusian Cyclone available in the collection.")
        return []

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Add 2 wind. May suffer up to 2 fatigue to add 1 fewer wind per fatigue."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Sun) on {self_display}: Add 2 wind. "
                           f"You may suffer up to 2 fatigue to reduce the wind added.")
        fatigue_choice = engine.amount_chooser(engine, 0, 2,
            "How much fatigue to suffer to reduce wind? (0-2):")
        wind_to_add = max(0, 2 - fatigue_choice)
        if fatigue_choice > 0:
            engine.state.ranger.fatigue(engine, fatigue_choice)
        if wind_to_add > 0:
            self.add_unique_tokens(engine, "wind", wind_to_add)
        else:
            engine.add_message("No wind added.")
        return True

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._refresh_effect,
                              self.id,
                              TimingType.WHEN
                              )]

    def _refresh_effect(self, engine: GameEngine, effort: int) -> int:
        """If 3+ wind, remove them, the lead ranger draws 1 additional path card next round,
        and flip into Thunderhead."""
        self_display = engine.get_display_id_cached(self)
        if self.get_unique_token_count("wind") >= 3:
            engine.add_message(f"3+ wind on {self_display}! Removing wind, drawing 1 extra path next round, "
                               f"and flipping into Thunderhead.")
            self.remove_unique_tokens(engine, "wind", self.unique_tokens.get("wind", 0))
            self._extra_path_draw_pending = True
            self.flip(engine)
        return 0

    def phase1_extra_draw(self, engine: GameEngine) -> None:
        """Called at the start of Phase 1 to draw the extra path card if pending."""
        if self._extra_path_draw_pending:
            engine.add_message("Howling Winds effect: Drawing 1 additional path card.")
            engine.draw_path_card(None, None)
            self._extra_path_draw_pending = False


class Thunderhead(Card):
    """Thunderhead - backside of Howling Winds, has Inclement trait.

    Refresh: Flip into Howling Winds.
    Sun challenge: Remove 1 progress from each path card and the location.
    Crest challenge: Ready 1 predator or prey."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Thunderhead", "Weather")) #type:ignore
        self.art_description = "From dark clouds towering impossibly high, a peal of thunder strikes."
        if fresh:
            self.backside = HowlingWinds(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.CREST: self._crest_effect,
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Remove 1 progress from each path card and the location."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Sun) on {self_display}: Remove 1 progress from each path card and the location.")
        for card in engine.state.all_cards_in_play():
            if card.has_type(CardType.PATH) and card.progress > 0:
                _, msg = card.remove_progress(1)
                engine.add_message(msg)
        if engine.state.location.progress > 0:
            _, msg = engine.state.location.remove_progress(1)
            engine.add_message(msg)
        return True

    def _crest_effect(self, engine: GameEngine) -> bool:
        """Ready 1 predator or prey."""
        self_display = engine.get_display_id_cached(self)
        pred_or_prey = [c for c in engine.state.all_cards_in_play()
                        if (c.has_trait("Predator") or c.has_trait("Prey")) and c.is_exhausted()]
        if not pred_or_prey:
            engine.add_message(f"Challenge (Crest) on {self_display}: No exhausted predators or prey to ready.")
            return False
        engine.add_message(f"Challenge (Crest) on {self_display}: Ready 1 predator or prey.")
        target = engine.card_chooser(engine, pred_or_prey)
        engine.add_message(target.ready(engine))
        return True

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._refresh_effect,
                              self.id,
                              TimingType.WHEN
                              )]

    def _refresh_effect(self, engine: GameEngine, effort: int) -> int:
        """Flip into Howling Winds."""
        engine.add_message(f"Thunderhead refresh: Flipping into Howling Winds.")
        self.flip(engine)
        return 0


class ElectricFog(Card):
    """Electric Fog weather card - has Inclement trait, uses fog tokens.

    Arrival Setup: Shuffle a Ball Lightning into the path deck.
    Response: When you perform an Avoid test, you may discard 1 fog to commit 1 effort.
              If you fail, suffer 1 injury.
    Sun challenge: Discard 1 fog. Each ranger suffers 1 fatigue. If no fog remaining,
                   flip into Clinging Mist."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Electric Fog", "Weather")) #type:ignore
        self.art_description = "Nothing is visible except fog all around you and increasingly frequent sparks of electricity." 
        self._fog_used_this_test = False
        if fresh:
            self.backside = ClingingMist(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_arrival_setup_cards(self, engine: GameEngine) -> list[Card]:
        """Arrival Setup: Search the General set for a Ball Lightning and shuffle it into the path deck."""
        ball = engine.state.collection.checkout_by_title("General", "Ball Lightning")
        if ball is not None:
            engine.add_message(f"Electric Fog: Shuffling a Ball Lightning into the path deck.")
            return [ball]
        engine.add_message(f"Electric Fog: No Ball Lightning available in the collection.")
        return []

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Discard 1 fog. Each ranger suffers 1 fatigue. If no fog, flip."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Sun) on {self_display}: Discard 1 fog. Each ranger suffers 1 fatigue.")
        self.remove_unique_tokens(engine, "fog", 1)
        engine.state.ranger.fatigue(engine, 1)
        if self.get_unique_token_count("fog") <= 0:
            engine.add_message(f"No fog remaining on {self_display} - flipping into Clinging Mist.")
            self.flip(engine)
        return True

    def get_listeners(self) -> list[EventListener] | None:
        return [
            # Response: When you perform an Avoid test, may discard 1 fog to commit 1 effort
            EventListener(EventType.PERFORM_TEST,
                          lambda _e, _c: self.get_unique_token_count("fog") > 0,
                          self._fog_response,
                          self.id,
                          TimingType.WHEN,
                          test_type="Avoid"),
            # If the test fails and fog was used, suffer 1 injury
            EventListener(EventType.TEST_FAIL,
                          lambda _e, _c: self._fog_used_this_test,
                          self._fog_fail_penalty,
                          self.id,
                          TimingType.AFTER,
                          test_type="Avoid"),
            # Reset the flag on test success too (cleanup)
            EventListener(EventType.TEST_SUCCEED,
                          lambda _e, _c: self._fog_used_this_test,
                          self._fog_reset,
                          self.id,
                          TimingType.AFTER,
                          test_type="Avoid"),
        ]

    def _fog_response(self, engine: GameEngine, effort: int) -> int:
        """May discard 1 fog to commit 1 effort to this Avoid test."""
        self._fog_used_this_test = False
        decision = engine.response_decider(engine,
            "Electric Fog: Discard 1 fog to commit 1 effort to this Avoid? (If you fail, suffer 1 injury)")
        if decision:
            self.remove_unique_tokens(engine, "fog", 1)
            self._fog_used_this_test = True
            return 1
        return 0

    def _fog_fail_penalty(self, engine: GameEngine, effort: int) -> int:
        """Suffer 1 injury because fog effort was used and the test failed."""
        engine.add_message("Electric Fog: The Avoid test failed after passing through the fog. Suffer 1 injury.")
        engine.state.ranger.injure(engine)
        self._fog_used_this_test = False
        return 0

    def _fog_reset(self, engine: GameEngine, effort: int) -> int:
        """Reset the fog flag after a successful test."""
        self._fog_used_this_test = False
        return 0


class ClingingMist(Card):
    """Clinging Mist - backside of Electric Fog, has Inclement trait.

    Constant: Increase the difficulty of all tests by 1.
    Refresh: Add 2 fog. If 4+ fog, flip into Electric Fog.
    Sun challenge: Discard 1 energy."""
    def __init__(self, fresh: bool = True):
        super().__init__(**load_card_fields("Clinging Mist", "Weather")) #type:ignore
        self.art_description = "Tendrils of mist blanket the floor of the valley, with only the very peaks of tall trees poking out over the sea of fog."
        if fresh:
            self.backside = ElectricFog(fresh=False)
            self.backside.backside = self

    def flip(self, engine: GameEngine) -> None:
        super().flip(engine)
        if self.backside is None:
            raise RuntimeError(f"Weather should always have a backside!")
        engine.state.weather = self.backside

    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        """Increase the difficulty of all tests by 1."""
        return [ConstantAbility(
            ConstantAbilityType.MODIFY_DIFFICULTY,
            source_card_id=self.id,
            condition_fn=lambda _s, _c: True,
            modifier=ValueModifier(target="difficulty", amount=1, source_id=self.id)
        )]

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Discard 1 energy."""
        self_display = engine.get_display_id_cached(self)
        engine.add_message(f"Challenge (Sun) on {self_display}: The wet ground is difficult to navigate. Discard 1 energy.")
        # Let the player choose which aspect to discard from
        available = [a for a in Aspect if engine.state.ranger.energy.get(a, 0) > 0]
        if available:
            aspect_names = [a.value for a in available]
            chosen_name = engine.option_chooser(engine, aspect_names,
                "Choose which energy to discard:")
            chosen_aspect = next(a for a in available if a.value == chosen_name)
            engine.state.ranger.energy[chosen_aspect] -= 1
            engine.add_message(f"Discarded 1 {chosen_aspect.value} energy.")
        else:
            engine.add_message("No energy to discard.")
        return True

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.REFRESH,
                              lambda eng, _c: True,
                              self._refresh_effect,
                              self.id,
                              TimingType.WHEN
                              )]

    def _refresh_effect(self, engine: GameEngine, effort: int) -> int:
        """Add 2 fog. If 4+ fog, flip into Electric Fog."""
        self_display = engine.get_display_id_cached(self)
        self.add_unique_tokens(engine, "fog", 2)
        if self.get_unique_token_count("fog") >= 4:
            engine.add_message(f"4+ fog on {self_display}! Flipping into Electric Fog.")
            self.flip(engine)
        return 0
