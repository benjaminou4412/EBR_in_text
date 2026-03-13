#type: ignore
"""Tests for all 8 weather cards and the weather forecast / day-start system."""
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import (APerfectDay, MiddaySun, Downpour, GatheringStorm,
                       HowlingWinds, Thunderhead, ElectricFog, ClingingMist,
                       LoneTreeStation, CerberusianCyclone, BallLightning)
from ebr.cards.explorer_cards import PeerlessPathfinder
from ebr.decks import get_current_weather
from tests.test_utils import MockChallengeDeck, make_challenge_card


# ─── Helpers ──────────────────────────────────────────────────────────


def make_test_ranger() -> RangerState:
    return RangerState(
        name="Test Ranger",
        hand=[],
        aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(20)],
        discard=[],
        fatigue_stack=[]
    )


def make_engine(weather: Card, **engine_kwargs) -> GameEngine:
    """Build an engine with the given weather card."""
    location = LoneTreeStation()
    role = PeerlessPathfinder()
    ranger = make_test_ranger()
    state = GameState(
        ranger=ranger, role_card=role, location=location, weather=weather,
        campaign_tracker=CampaignTracker(day_number=1),
        areas={
            Area.SURROUNDINGS: [weather, location],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        }
    )
    defaults = dict(
        card_chooser=lambda _e, cards: cards[0],
        response_decider=lambda _e, _p: True,
        order_decider=lambda _e, items, _p: items,
        option_chooser=lambda _e, opts, _p: opts[0],
        amount_chooser=lambda _e, lo, hi, _p: lo,
    )
    defaults.update(engine_kwargs)
    return GameEngine(state, **defaults)


def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    state.challenge_deck = MockChallengeDeck([make_challenge_card(
        icon=symbol,
        awa=mod if aspect == Aspect.AWA else 0,
        fit=mod if aspect == Aspect.FIT else 0,
        spi=mod if aspect == Aspect.SPI else 0,
        foc=mod if aspect == Aspect.FOC else 0
    )])


def make_day_engine(day_number: int) -> GameEngine:
    """Build an engine using the full new-day-start procedure for a given day."""
    role_card = PeerlessPathfinder()
    campaign_tracker = CampaignTracker(
        day_number=day_number,
        ranger_name="Test Ranger",
        ranger_aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
        current_location_id="Lone Tree Station",
        current_terrain_type="Woods"
    )
    state = GameEngine.setup_new_day(campaign_tracker, role_card)
    state.ranger.deck = [Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(20)]
    engine = GameEngine(state)
    for _ in range(5):
        state.ranger.draw_card(engine)
    engine.arrival_setup(start_of_day=True)
    return engine


# ═══════════════════════════════════════════════════════════════════════
# A Perfect Day
# ═══════════════════════════════════════════════════════════════════════


class TestAPerfectDayFields(unittest.TestCase):

    def test_title(self):
        w = APerfectDay()
        self.assertEqual(w.title, "A Perfect Day")

    def test_weather_type(self):
        w = APerfectDay()
        self.assertTrue(w.has_type(CardType.WEATHER))

    def test_no_traits(self):
        w = APerfectDay()
        self.assertEqual(len(w.traits), 0)

    def test_starts_with_3_clouds(self):
        w = APerfectDay()
        self.assertEqual(w.get_unique_token_count("cloud"), 3)

    def test_backside_is_midday_sun(self):
        w = APerfectDay()
        self.assertIsInstance(w.backside, MiddaySun)

    def test_backside_backside_is_self(self):
        w = APerfectDay()
        self.assertIs(w.backside.backside, w)

    def test_has_mountain_challenge_handler(self):
        w = APerfectDay()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.MOUNTAIN, handlers)

    def test_no_sun_challenge_handler(self):
        w = APerfectDay()
        handlers = w.get_challenge_handlers()
        self.assertNotIn(ChallengeIcon.SUN, handlers)


class TestAPerfectDayMountainEffect(unittest.TestCase):

    def test_mountain_effect_adds_progress_when_test_added_progress(self):
        weather = APerfectDay()
        target = Card(
            id="test-target", title="Test Feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=2, progress_threshold=5,
            starting_area=Area.WITHIN_REACH
        )
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [target],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather
        stack_deck(state, Aspect.FIT, +1, ChallengeIcon.MOUNTAIN)
        eng = GameEngine(state)
        from ebr.registry import provide_common_tests
        tests = provide_common_tests(state)
        traverse_action = next(t for t in tests if "Traverse" in t.name)
        decision = CommitDecision(energy=2, hand_indices=[])
        eng.perform_test(traverse_action, decision, target.id)
        # 2 energy + 1 mod = 3 effort as progress, +1 from Mountain
        self.assertEqual(target.progress, 4)

    def test_mountain_effect_does_nothing_when_no_progress_added(self):
        weather = APerfectDay()
        being = Card(
            id="test-being", title="Test Being",
            card_types={CardType.PATH, CardType.BEING},
            presence=2, progress_threshold=5,
            starting_area=Area.WITHIN_REACH
        )
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [being],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)
        eng = GameEngine(state)
        from ebr.registry import provide_common_tests
        tests = provide_common_tests(state)
        search_action = next(t for t in tests if "Remember" in t.name)
        decision = CommitDecision(energy=1, hand_indices=[])
        eng.perform_test(search_action, decision, being.id)
        self.assertEqual(being.progress, 0)


class TestAPerfectDayRefresh(unittest.TestCase):

    def test_refresh_removes_1_cloud(self):
        w = APerfectDay()
        w.unique_tokens = {"cloud": 3}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertEqual(w.get_unique_token_count("Cloud"), 2)

    def test_flips_to_midday_sun_at_zero_clouds(self):
        w = APerfectDay()
        w.unique_tokens = {"cloud": 1}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, MiddaySun)
        self.assertIn(eng.state.weather, eng.state.areas[Area.SURROUNDINGS])
        self.assertNotIn(w, eng.state.areas[Area.SURROUNDINGS])


# ═══════════════════════════════════════════════════════════════════════
# Midday Sun
# ═══════════════════════════════════════════════════════════════════════


class TestMiddaySunFields(unittest.TestCase):

    def test_title(self):
        w = MiddaySun()
        self.assertEqual(w.title, "Midday Sun")

    def test_hot_trait(self):
        w = MiddaySun()
        self.assertTrue(w.has_trait("Hot"))

    def test_starts_with_0_clouds(self):
        w = MiddaySun()
        self.assertEqual(w.get_unique_token_count("cloud"), 0)

    def test_backside_is_a_perfect_day(self):
        w = MiddaySun()
        self.assertIsInstance(w.backside, APerfectDay)

    def test_has_sun_challenge_handler(self):
        w = MiddaySun()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.SUN, handlers)

    def test_has_locate_test(self):
        w = MiddaySun()
        tests = w.get_tests()
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].aspect, Aspect.FOC)
        self.assertEqual(tests[0].approach, Approach.REASON)
        self.assertEqual(tests[0].verb, "Locate")


class TestMiddaySunSunEffect(unittest.TestCase):

    def test_sun_fatigues_ranger(self):
        w = MiddaySun()
        eng = make_engine(w)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        handlers = w.get_challenge_handlers()
        handlers[ChallengeIcon.SUN](eng)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)


class TestMiddaySunLocateTest(unittest.TestCase):

    def test_locate_success_adds_cloud_and_soothes(self):
        w = MiddaySun()
        hand_card = Card(id="hand0", title="Hand Card",
                         approach_icons={Approach.REASON: 1})
        eng = make_engine(w)
        eng.state.ranger.hand = [hand_card]
        # Give ranger some fatigue to soothe
        eng.state.ranger.fatigue_stack.append(Card(id="fat", title="Fatigue"))
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        # Use MOUNTAIN icon to avoid triggering Sun challenge effect (which would add fatigue)
        stack_deck(eng.state, Aspect.FOC, 0, ChallengeIcon.MOUNTAIN)
        tests = w.get_tests()
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(tests[0], decision, w.id)
        self.assertEqual(w.get_unique_token_count("Cloud"), 1)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue - 1)


class TestMiddaySunRefresh(unittest.TestCase):

    def test_refresh_adds_1_cloud(self):
        w = MiddaySun()
        w.unique_tokens = {"cloud": 1}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertEqual(w.get_unique_token_count("Cloud"), 2)

    def test_flips_to_perfect_day_at_3_clouds(self):
        w = MiddaySun()
        w.unique_tokens = {"cloud": 2}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, APerfectDay)
        self.assertIn(eng.state.weather, eng.state.areas[Area.SURROUNDINGS])


# ═══════════════════════════════════════════════════════════════════════
# Downpour
# ═══════════════════════════════════════════════════════════════════════


class TestDownpourFields(unittest.TestCase):

    def test_title(self):
        w = Downpour()
        self.assertEqual(w.title, "Downpour")

    def test_inclement_trait(self):
        w = Downpour()
        self.assertTrue(w.has_trait("Inclement"))

    def test_starts_with_4_rain(self):
        w = Downpour()
        self.assertEqual(w.get_unique_token_count("rain"), 4)

    def test_backside_is_gathering_storm(self):
        w = Downpour()
        self.assertIsInstance(w.backside, GatheringStorm)

    def test_backside_backside_is_self(self):
        w = Downpour()
        self.assertIs(w.backside.backside, w)

    def test_has_sun_challenge_handler(self):
        w = Downpour()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.SUN, handlers)


class TestDownpourSunEffect(unittest.TestCase):

    def test_removes_1_rain_and_fatigues(self):
        w = Downpour()
        eng = make_engine(w)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        w._sun_effect(eng)
        self.assertEqual(w.get_unique_token_count("rain"), 3)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)

    def test_flips_when_rain_reaches_zero(self):
        w = Downpour()
        w.unique_tokens = {"rain": 1}
        eng = make_engine(w)
        w._sun_effect(eng)
        self.assertIsInstance(eng.state.weather, GatheringStorm)

    def test_does_not_flip_with_rain_remaining(self):
        w = Downpour()
        w.unique_tokens = {"rain": 2}
        eng = make_engine(w)
        w._sun_effect(eng)
        self.assertIsInstance(eng.state.weather, Downpour)
        self.assertEqual(w.get_unique_token_count("rain"), 1)


# ═══════════════════════════════════════════════════════════════════════
# Gathering Storm
# ═══════════════════════════════════════════════════════════════════════


class TestGatheringStormFields(unittest.TestCase):

    def test_title(self):
        w = GatheringStorm()
        self.assertEqual(w.title, "Gathering Storm")

    def test_no_inclement_trait(self):
        w = GatheringStorm()
        self.assertFalse(w.has_trait("Inclement"))

    def test_starts_with_0_rain(self):
        w = GatheringStorm()
        self.assertEqual(w.get_unique_token_count("rain"), 0)

    def test_backside_is_downpour(self):
        w = GatheringStorm()
        self.assertIsInstance(w.backside, Downpour)

    def test_has_shelter_test(self):
        w = GatheringStorm()
        tests = w.get_tests()
        self.assertEqual(len(tests), 1)
        t = tests[0]
        self.assertEqual(t.aspect, Aspect.FOC)
        self.assertEqual(t.approach, Approach.REASON)
        self.assertEqual(t.verb, "Shelter")


class TestGatheringStormShelterTest(unittest.TestCase):

    def test_shelter_removes_rain_per_2_effort(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 3}
        hand_card = Card(id="hand0", title="Hand Card",
                         approach_icons={Approach.REASON: 1})
        eng = make_engine(w)
        eng.state.ranger.hand = [hand_card]
        stack_deck(eng.state, Aspect.FOC, 0, ChallengeIcon.SUN)
        tests = w.get_tests()
        # energy(1) + 1 icon = 2 effort → removes 1 rain
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(tests[0], decision, w.id)
        self.assertEqual(w.get_unique_token_count("rain"), 2)

    def test_shelter_high_effort_removes_more_rain(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 3}
        hand_card = Card(id="hand0", title="Hand Card",
                         approach_icons={Approach.REASON: 3})
        eng = make_engine(w)
        eng.state.ranger.hand = [hand_card]
        stack_deck(eng.state, Aspect.FOC, 0, ChallengeIcon.SUN)
        tests = w.get_tests()
        # energy(1) + 3 icons = 4 effort → removes 2 rain
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(tests[0], decision, w.id)
        self.assertEqual(w.get_unique_token_count("rain"), 1)


class TestGatheringStormRefresh(unittest.TestCase):

    def test_adds_2_rain(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 0}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertEqual(w.get_unique_token_count("rain"), 2)

    def test_flips_to_downpour_at_4_rain(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 2}
        eng = make_engine(w)
        eng.phase4_refresh()
        # 2 + 2 = 4 → flip
        self.assertIsInstance(eng.state.weather, Downpour)

    def test_does_not_flip_below_4(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 1}
        eng = make_engine(w)
        eng.phase4_refresh()
        # 1 + 2 = 3 < 4 → no flip
        self.assertIs(eng.state.weather, w)
        self.assertEqual(w.get_unique_token_count("rain"), 3)

    def test_refresh_exhausts_role_on_flip(self):
        """Call _refresh_effect directly since phase4_refresh readies all cards at the end."""
        w = GatheringStorm()
        w.unique_tokens = {"rain": 2}
        eng = make_engine(w)
        self.assertFalse(eng.state.role_card.is_exhausted())
        w._refresh_effect(eng, 0)
        self.assertTrue(eng.state.role_card.is_exhausted())

    def test_refresh_moves_prey_to_along_the_way(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 2}
        prey = Card(id="prey1", title="Sitka Doe", traits={"Prey"},
                    card_types={CardType.PATH, CardType.BEING}, presence=1)
        eng = make_engine(w)
        eng.state.areas[Area.WITHIN_REACH].append(prey)
        eng.phase4_refresh()
        self.assertIn(prey, eng.state.areas[Area.ALONG_THE_WAY])
        self.assertNotIn(prey, eng.state.areas[Area.WITHIN_REACH])

    def test_refresh_does_not_move_non_prey(self):
        w = GatheringStorm()
        w.unique_tokens = {"rain": 2}
        non_prey = Card(id="feature1", title="Some Feature",
                        card_types={CardType.PATH, CardType.FEATURE}, presence=1)
        eng = make_engine(w)
        eng.state.areas[Area.WITHIN_REACH].append(non_prey)
        eng.phase4_refresh()
        self.assertIn(non_prey, eng.state.areas[Area.WITHIN_REACH])


# ═══════════════════════════════════════════════════════════════════════
# Howling Winds
# ═══════════════════════════════════════════════════════════════════════


class TestHowlingWindsFields(unittest.TestCase):

    def test_title(self):
        w = HowlingWinds()
        self.assertEqual(w.title, "Howling Winds")

    def test_inclement_trait(self):
        w = HowlingWinds()
        self.assertTrue(w.has_trait("Inclement"))

    def test_starts_with_0_wind(self):
        w = HowlingWinds()
        self.assertEqual(w.get_unique_token_count("wind"), 0)

    def test_backside_is_thunderhead(self):
        w = HowlingWinds()
        self.assertIsInstance(w.backside, Thunderhead)

    def test_has_sun_challenge_handler(self):
        w = HowlingWinds()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.SUN, handlers)


class TestHowlingWindsArrivalSetup(unittest.TestCase):

    def test_arrival_setup_returns_cyclone(self):
        w = HowlingWinds()
        eng = make_engine(w)
        cards = w.get_arrival_setup_cards(eng)
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], CerberusianCyclone)


class TestHowlingWindsSunEffect(unittest.TestCase):

    def test_adds_2_wind_with_no_fatigue(self):
        """amount_chooser returns lo=0, so no fatigue, full 2 wind."""
        w = HowlingWinds()
        eng = make_engine(w)
        w._sun_effect(eng)
        self.assertEqual(w.get_unique_token_count("wind"), 2)

    def test_adds_0_wind_with_max_fatigue(self):
        """amount_chooser returns hi=2, so 2 fatigue, 0 wind."""
        w = HowlingWinds()
        eng = make_engine(w, amount_chooser=lambda _e, lo, hi, _p: hi)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        w._sun_effect(eng)
        self.assertEqual(w.get_unique_token_count("wind"), 0)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 2)

    def test_adds_1_wind_with_1_fatigue(self):
        """amount_chooser returns 1."""
        w = HowlingWinds()
        eng = make_engine(w, amount_chooser=lambda _e, lo, hi, _p: 1)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        w._sun_effect(eng)
        self.assertEqual(w.get_unique_token_count("wind"), 1)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)


class TestHowlingWindsRefresh(unittest.TestCase):

    def test_no_flip_below_3_wind(self):
        w = HowlingWinds()
        w.unique_tokens = {"wind": 2}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIs(eng.state.weather, w)

    def test_flips_at_3_wind(self):
        w = HowlingWinds()
        w.unique_tokens = {"wind": 3}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, Thunderhead)

    def test_removes_all_wind_on_flip(self):
        w = HowlingWinds()
        w.unique_tokens = {"wind": 5}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertEqual(w.get_unique_token_count("wind"), 0)

    def test_sets_extra_path_draw_pending(self):
        w = HowlingWinds()
        w.unique_tokens = {"wind": 3}
        eng = make_engine(w)
        self.assertFalse(w._extra_path_draw_pending)
        eng.phase4_refresh()
        self.assertTrue(w._extra_path_draw_pending)


class TestHowlingWindsExtraPathDraw(unittest.TestCase):

    def _make_path_cards(self, count: int) -> list[Card]:
        return [Card(id=f"path{i}", title=f"Path {i}",
                     card_types={CardType.PATH, CardType.FEATURE},
                     starting_area=Area.ALONG_THE_WAY, presence=1)
                for i in range(count)]

    def test_phase1_extra_draw_draws_card(self):
        w = HowlingWinds()
        w._extra_path_draw_pending = True
        eng = make_engine(w)
        eng.state.path_deck = self._make_path_cards(5)
        initial_deck = len(eng.state.path_deck)
        w.phase1_extra_draw(eng)
        self.assertEqual(len(eng.state.path_deck), initial_deck - 1)
        self.assertFalse(w._extra_path_draw_pending)

    def test_phase1_extra_draw_does_nothing_when_not_pending(self):
        w = HowlingWinds()
        eng = make_engine(w)
        eng.state.path_deck = self._make_path_cards(5)
        initial_deck = len(eng.state.path_deck)
        w.phase1_extra_draw(eng)
        self.assertEqual(len(eng.state.path_deck), initial_deck)

    def test_phase1_draw_paths_checks_thunderhead_backside(self):
        """After HowlingWinds flips to Thunderhead during refresh, the next
        phase1_draw_paths should still find and use the extra draw."""
        w = HowlingWinds()
        w.unique_tokens = {"wind": 3}
        eng = make_engine(w)
        eng.state.path_deck = self._make_path_cards(10)

        # Refresh flips to Thunderhead and sets pending
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, Thunderhead)
        self.assertTrue(w._extra_path_draw_pending)

        initial_deck = len(eng.state.path_deck)
        eng.phase1_draw_paths(count=1)
        # 1 normal draw + 1 extra = 2 fewer cards
        self.assertEqual(len(eng.state.path_deck), initial_deck - 2)
        self.assertFalse(w._extra_path_draw_pending)


# ═══════════════════════════════════════════════════════════════════════
# Thunderhead
# ═══════════════════════════════════════════════════════════════════════


class TestThunderheadFields(unittest.TestCase):

    def test_title(self):
        w = Thunderhead()
        self.assertEqual(w.title, "Thunderhead")

    def test_inclement_trait(self):
        w = Thunderhead()
        self.assertTrue(w.has_trait("Inclement"))

    def test_backside_is_howling_winds(self):
        w = Thunderhead()
        self.assertIsInstance(w.backside, HowlingWinds)

    def test_has_sun_and_crest_handlers(self):
        w = Thunderhead()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.SUN, handlers)
        self.assertIn(ChallengeIcon.CREST, handlers)


class TestThunderheadSunEffect(unittest.TestCase):

    def test_removes_progress_from_path_cards(self):
        w = Thunderhead()
        path_card = Card(id="path1", title="Path Feature",
                         card_types={CardType.PATH, CardType.FEATURE},
                         presence=2, progress_threshold=5)
        path_card.progress = 3
        eng = make_engine(w)
        eng.state.areas[Area.ALONG_THE_WAY].append(path_card)
        w._sun_effect(eng)
        self.assertEqual(path_card.progress, 2)

    def test_removes_progress_from_location(self):
        w = Thunderhead()
        eng = make_engine(w)
        eng.state.location.progress = 4
        w._sun_effect(eng)
        self.assertEqual(eng.state.location.progress, 3)

    def test_does_not_remove_progress_below_zero(self):
        w = Thunderhead()
        eng = make_engine(w)
        eng.state.location.progress = 0
        w._sun_effect(eng)
        self.assertEqual(eng.state.location.progress, 0)


class TestThunderheadCrestEffect(unittest.TestCase):

    def test_readies_exhausted_predator(self):
        w = Thunderhead()
        pred = Card(id="pred1", title="Test Predator",
                    card_types={CardType.PATH, CardType.BEING},
                    traits={"Predator"}, presence=2)
        pred.exhausted = True
        eng = make_engine(w)
        eng.state.areas[Area.ALONG_THE_WAY].append(pred)
        w._crest_effect(eng)
        self.assertFalse(pred.is_exhausted())

    def test_no_exhausted_pred_or_prey_returns_false(self):
        w = Thunderhead()
        eng = make_engine(w)
        result = w._crest_effect(eng)
        self.assertFalse(result)


class TestThunderheadRefresh(unittest.TestCase):

    def test_flips_to_howling_winds(self):
        w = Thunderhead()
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, HowlingWinds)


# ═══════════════════════════════════════════════════════════════════════
# Electric Fog
# ═══════════════════════════════════════════════════════════════════════


class TestElectricFogFields(unittest.TestCase):

    def test_title(self):
        w = ElectricFog()
        self.assertEqual(w.title, "Electric Fog")

    def test_inclement_trait(self):
        w = ElectricFog()
        self.assertTrue(w.has_trait("Inclement"))

    def test_starts_with_4_fog(self):
        w = ElectricFog()
        self.assertEqual(w.get_unique_token_count("fog"), 4)

    def test_backside_is_clinging_mist(self):
        w = ElectricFog()
        self.assertIsInstance(w.backside, ClingingMist)

    def test_has_sun_challenge_handler(self):
        w = ElectricFog()
        handlers = w.get_challenge_handlers()
        self.assertIn(ChallengeIcon.SUN, handlers)


class TestElectricFogArrivalSetup(unittest.TestCase):

    def test_arrival_setup_returns_ball_lightning(self):
        w = ElectricFog()
        eng = make_engine(w)
        cards = w.get_arrival_setup_cards(eng)
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], BallLightning)


class TestElectricFogSunEffect(unittest.TestCase):

    def test_removes_1_fog_and_fatigues(self):
        w = ElectricFog()
        eng = make_engine(w)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        w._sun_effect(eng)
        self.assertEqual(w.get_unique_token_count("fog"), 3)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)

    def test_flips_when_fog_reaches_zero(self):
        w = ElectricFog()
        w.unique_tokens = {"fog": 1}
        eng = make_engine(w)
        w._sun_effect(eng)
        self.assertIsInstance(eng.state.weather, ClingingMist)

    def test_does_not_flip_with_fog_remaining(self):
        w = ElectricFog()
        w.unique_tokens = {"fog": 2}
        eng = make_engine(w)
        w._sun_effect(eng)
        self.assertIs(eng.state.weather, w)


class TestElectricFogAvoidResponse(unittest.TestCase):

    def test_fog_response_adds_effort_when_accepted(self):
        w = ElectricFog()
        eng = make_engine(w, response_decider=lambda _e, _p: True)
        result = w._fog_response(eng, 0)
        self.assertEqual(result, 1)
        self.assertTrue(w._fog_used_this_test)
        self.assertEqual(w.get_unique_token_count("fog"), 3)

    def test_fog_response_no_effort_when_declined(self):
        w = ElectricFog()
        eng = make_engine(w, response_decider=lambda _e, _p: False)
        result = w._fog_response(eng, 0)
        self.assertEqual(result, 0)
        self.assertFalse(w._fog_used_this_test)
        self.assertEqual(w.get_unique_token_count("fog"), 4)

    def test_fog_fail_penalty_injures_ranger(self):
        w = ElectricFog()
        w._fog_used_this_test = True
        eng = make_engine(w)
        initial_injury = eng.state.ranger.injury
        w._fog_fail_penalty(eng, 0)
        self.assertEqual(eng.state.ranger.injury, initial_injury + 1)
        self.assertFalse(w._fog_used_this_test)

    def test_fog_reset_clears_flag(self):
        w = ElectricFog()
        w._fog_used_this_test = True
        eng = make_engine(w)
        w._fog_reset(eng, 0)
        self.assertFalse(w._fog_used_this_test)

    def test_listeners_include_avoid_filters(self):
        w = ElectricFog()
        listeners = w.get_listeners()
        self.assertEqual(len(listeners), 3)
        # PERFORM_TEST listener for Avoid
        self.assertEqual(listeners[0].event_type, EventType.PERFORM_TEST)
        self.assertEqual(listeners[0].test_type, "Avoid")
        # TEST_FAIL listener for Avoid
        self.assertEqual(listeners[1].event_type, EventType.TEST_FAIL)
        self.assertEqual(listeners[1].test_type, "Avoid")
        # TEST_SUCCEED listener for Avoid
        self.assertEqual(listeners[2].event_type, EventType.TEST_SUCCEED)
        self.assertEqual(listeners[2].test_type, "Avoid")


# ═══════════════════════════════════════════════════════════════════════
# Clinging Mist
# ═══════════════════════════════════════════════════════════════════════


class TestClingingMistFields(unittest.TestCase):

    def test_title(self):
        w = ClingingMist()
        self.assertEqual(w.title, "Clinging Mist")

    def test_inclement_trait(self):
        w = ClingingMist()
        self.assertTrue(w.has_trait("Inclement"))

    def test_starts_with_0_fog(self):
        w = ClingingMist()
        self.assertEqual(w.get_unique_token_count("fog"), 0)

    def test_backside_is_electric_fog(self):
        w = ClingingMist()
        self.assertIsInstance(w.backside, ElectricFog)


class TestClingingMistDifficultyModifier(unittest.TestCase):

    def test_has_modify_difficulty_ability(self):
        w = ClingingMist()
        abilities = w.get_constant_abilities()
        self.assertEqual(len(abilities), 1)
        self.assertEqual(abilities[0].ability_type, ConstantAbilityType.MODIFY_DIFFICULTY)
        self.assertEqual(abilities[0].modifier.amount, 1)

    def test_difficulty_increased_by_1_in_engine(self):
        """Clinging Mist's constant ability should increase test difficulty by 1.
        Traverse difficulty = presence (2) + 1 from mist = 3."""
        w = ClingingMist()
        target = Card(id="target", title="Target",
                      card_types={CardType.PATH, CardType.FEATURE},
                      presence=2, progress_threshold=5,
                      starting_area=Area.WITHIN_REACH)
        eng = make_engine(w)
        eng.state.areas[Area.WITHIN_REACH].append(target)
        stack_deck(eng.state, Aspect.FIT, 0, ChallengeIcon.SUN)
        from ebr.registry import provide_common_tests
        tests = provide_common_tests(eng.state)
        traverse = next(t for t in tests if "Traverse" in t.name)
        # Commit 3 energy + 0 mod = 3 effort vs difficulty 2+1=3 → success
        decision = CommitDecision(energy=3, hand_indices=[])
        outcome = eng.perform_test(traverse, decision, target.id)
        self.assertTrue(outcome.success)
        # But 2 energy would fail (2 < 3)
        target.progress = 0
        stack_deck(eng.state, Aspect.FIT, 0, ChallengeIcon.SUN)
        decision2 = CommitDecision(energy=2, hand_indices=[])
        outcome2 = eng.perform_test(traverse, decision2, target.id)
        self.assertFalse(outcome2.success)


class TestClingingMistSunEffect(unittest.TestCase):

    def test_discards_1_energy(self):
        w = ClingingMist()
        eng = make_engine(w)
        # Ranger starts with some energy
        eng.state.ranger.energy[Aspect.AWA] = 3
        w._sun_effect(eng)
        self.assertEqual(eng.state.ranger.energy[Aspect.AWA], 2)

    def test_no_energy_does_not_crash(self):
        w = ClingingMist()
        eng = make_engine(w)
        # Zero out all energy
        for a in Aspect:
            eng.state.ranger.energy[a] = 0
        w._sun_effect(eng)  # should not raise


class TestClingingMistRefresh(unittest.TestCase):

    def test_adds_2_fog(self):
        w = ClingingMist()
        w.unique_tokens = {"fog": 0}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertEqual(w.get_unique_token_count("fog"), 2)

    def test_flips_to_electric_fog_at_4(self):
        w = ClingingMist()
        w.unique_tokens = {"fog": 2}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, ElectricFog)

    def test_does_not_flip_below_4(self):
        w = ClingingMist()
        w.unique_tokens = {"fog": 1}
        eng = make_engine(w)
        eng.phase4_refresh()
        self.assertIs(eng.state.weather, w)
        self.assertEqual(w.get_unique_token_count("fog"), 3)


# ═══════════════════════════════════════════════════════════════════════
# Day-Start Weather Loading (Weather Forecast System)
# ═══════════════════════════════════════════════════════════════════════


class TestWeatherForecast(unittest.TestCase):
    """Test that the full new-day-start procedure loads the correct weather
    based on the day_registry forecast."""

    def test_day_1_loads_a_perfect_day(self):
        eng = make_day_engine(1)
        self.assertIsInstance(eng.state.weather, APerfectDay)
        self.assertIn(eng.state.weather, eng.state.areas[Area.SURROUNDINGS])

    def test_day_4_loads_downpour(self):
        eng = make_day_engine(4)
        self.assertIsInstance(eng.state.weather, Downpour)
        self.assertIn(eng.state.weather, eng.state.areas[Area.SURROUNDINGS])

    def test_day_13_loads_howling_winds(self):
        eng = make_day_engine(13)
        self.assertIsInstance(eng.state.weather, HowlingWinds)
        self.assertIn(eng.state.weather, eng.state.areas[Area.SURROUNDINGS])

    def test_day_21_loads_a_perfect_day(self):
        eng = make_day_engine(21)
        self.assertIsInstance(eng.state.weather, APerfectDay)

    def test_weather_has_correct_starting_tokens_on_day_start(self):
        """Downpour should start with 4 rain tokens via normal instantiation."""
        eng = make_day_engine(5)
        self.assertIsInstance(eng.state.weather, Downpour)
        self.assertEqual(eng.state.weather.get_unique_token_count("rain"), 4)

    def test_howling_winds_arrival_setup_adds_cyclone(self):
        """When Howling Winds is the day's weather, its arrival setup should
        add a Cerberusian Cyclone. It may be in the path deck or already drawn
        into play by the location's arrival setup."""
        eng = make_day_engine(13)
        cyclone_in_deck = any(isinstance(c, CerberusianCyclone)
                             for c in eng.state.path_deck)
        cyclone_in_play = any(isinstance(c, CerberusianCyclone)
                              for c in eng.state.all_cards_in_play())
        self.assertTrue(cyclone_in_deck or cyclone_in_play,
                        "Cerberusian Cyclone should be in the path deck or already in play")


class TestWeatherRegistry(unittest.TestCase):
    """Test that get_current_weather returns the correct card for each title."""

    def test_electric_fog_in_registry(self):
        card = get_current_weather("Electric Fog")
        self.assertIsInstance(card, ElectricFog)
        self.assertTrue(card.has_type(CardType.WEATHER))


# ═══════════════════════════════════════════════════════════════════════
# Mid-Day Weather Changes
# ═══════════════════════════════════════════════════════════════════════


class TestMidDayWeatherChange(unittest.TestCase):
    """Test weather changes that happen mid-day via game effects (flipping)."""

    def test_downpour_to_gathering_storm_via_sun_effects(self):
        """Repeatedly triggering sun effects on Downpour should eventually
        flip it to Gathering Storm when rain runs out."""
        w = Downpour()
        eng = make_engine(w)
        # Downpour starts with 4 rain; each sun effect removes 1
        for _ in range(4):
            w._sun_effect(eng)
        self.assertIsInstance(eng.state.weather, GatheringStorm)

    def test_gathering_storm_to_downpour_via_refreshes(self):
        """Gathering Storm starts with 0 rain and adds 2 per refresh.
        After 2 refreshes (4 rain), it should flip to Downpour."""
        w = GatheringStorm()
        eng = make_engine(w)
        # First refresh: 0 → 2 (no flip)
        eng.phase4_refresh()
        self.assertIs(eng.state.weather, w)
        # Second refresh: 2 → 4 (flip!)
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, Downpour)

    def test_howling_winds_to_thunderhead_and_back(self):
        """HowlingWinds flips to Thunderhead at 3+ wind during refresh.
        Thunderhead flips back to HowlingWinds on its own refresh."""
        w = HowlingWinds()
        eng = make_engine(w)
        w.unique_tokens = {"wind": 3}
        eng.phase4_refresh()
        th = eng.state.weather
        self.assertIsInstance(th, Thunderhead)
        # Thunderhead refresh flips back
        eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, HowlingWinds)

    def test_electric_fog_to_clinging_mist_via_sun(self):
        """Draining all fog from Electric Fog via sun effects should flip to Clinging Mist."""
        w = ElectricFog()
        eng = make_engine(w)
        for _ in range(4):
            w._sun_effect(eng)
        self.assertIsInstance(eng.state.weather, ClingingMist)

    def test_clinging_mist_to_electric_fog_via_refreshes(self):
        """Clinging Mist adds 2 fog per refresh. At 4+, flips to Electric Fog."""
        w = ClingingMist()
        eng = make_engine(w)
        eng.phase4_refresh()  # 0 → 2
        self.assertIs(eng.state.weather, w)
        eng.phase4_refresh()  # 2 → 4 → flip
        self.assertIsInstance(eng.state.weather, ElectricFog)

    def test_full_perfect_day_midday_sun_cycle(self):
        """A Perfect Day should flip to Midday Sun after 3 refreshes,
        then Midday Sun flips back after 3 more refreshes."""
        w = APerfectDay()
        eng = make_engine(w)
        # 3 refreshes to drain clouds (3 → 2 → 1 → 0 → flip)
        for _ in range(3):
            eng.phase4_refresh()
        ms = eng.state.weather
        self.assertIsInstance(ms, MiddaySun)
        # 3 more refreshes to build clouds (0 → 1 → 2 → 3 → flip)
        for _ in range(3):
            eng.phase4_refresh()
        self.assertIsInstance(eng.state.weather, APerfectDay)

    def test_weather_change_updates_surroundings(self):
        """When weather flips, the old card should leave Surroundings and
        the new card should be in Surroundings."""
        w = Downpour()
        w.unique_tokens = {"rain": 1}
        eng = make_engine(w)
        w._sun_effect(eng)
        new_weather = eng.state.weather
        self.assertIsInstance(new_weather, GatheringStorm)
        self.assertNotIn(w, eng.state.areas[Area.SURROUNDINGS])
        self.assertIn(new_weather, eng.state.areas[Area.SURROUNDINGS])

    def test_modified_forecast_loads_electric_fog(self):
        """If the day_registry is modified to have Electric Fog, it should load correctly."""
        role_card = PeerlessPathfinder()
        campaign_tracker = CampaignTracker(
            day_number=1,
            ranger_name="Test Ranger",
            ranger_aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            current_location_id="Lone Tree Station",
            current_terrain_type="Woods"
        )
        campaign_tracker.day_registry[1] = DayContent("Electric Fog")
        state = GameEngine.setup_new_day(campaign_tracker, role_card)
        state.ranger.deck = [Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(20)]
        engine = GameEngine(state)
        for _ in range(5):
            state.ranger.draw_card(engine)
        engine.arrival_setup(start_of_day=True)
        self.assertIsInstance(engine.state.weather, ElectricFog)
        self.assertEqual(engine.state.weather.get_unique_token_count("fog"), 4)
        # Should also have Ball Lightning in path deck
        bl_in_deck = any(isinstance(c, BallLightning)
                         for c in engine.state.path_deck)
        self.assertTrue(bl_in_deck,
                        "Path deck should contain Ball Lightning from Electric Fog arrival setup")


if __name__ == '__main__':
    unittest.main()
