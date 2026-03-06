"""
Theme B: Card-specific get_tests() Action field assertions.
Verifies aspect, approach, verb, and difficulty for each card's tests.
Source of truth: JSON rules text describing each card's tests.
"""

import unittest
from ebr.models import (
    GameState, RangerState, Card, Area, Aspect, Approach, CardType,
    ChallengeIcon, CampaignTracker
)
from ebr.engine import GameEngine
from ebr.cards import (
    SitkaDoe, CausticMulcher, SunberryBramble, OvergrownThicket,
    MiddaySun, BiscuitBasket, LoneTreeStation, PeerlessPathfinder,
    APerfectDay, SitkaBuck
)


def make_engine_with_card_in_play(card: Card, area: Area = Area.WITHIN_REACH) -> GameEngine:
    """Set up an engine with the given card in play."""
    role = PeerlessPathfinder()
    location = LoneTreeStation()
    weather = APerfectDay()
    ranger = RangerState(
        name="Test Ranger",
        aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
        deck=[Card(id=f"deck-{i}", title=f"Deck Card {i}") for i in range(10)]
    )
    state = GameState(
        ranger=ranger, role_card=role, location=location, weather=weather,
        campaign_tracker=CampaignTracker(day_number=1)
    )
    state.areas[Area.SURROUNDINGS].append(location)
    state.areas[Area.SURROUNDINGS].append(weather)
    state.areas[area].append(card)
    return GameEngine(
        state,
        card_chooser=lambda _e, cards: cards[0],
        response_decider=lambda _e, _p: True,
        order_decider=lambda _e, items, _p: items,
        option_chooser=lambda _e, opts, _p: opts[0],
        amount_chooser=lambda _e, lo, hi, _p: lo
    )


class SitkaDoeGetTestsTests(unittest.TestCase):
    """JSON: Spook test — SPI + Conflict, difficulty 1."""

    def setUp(self):
        self.card = SitkaDoe()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_spook_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.SPI)
        self.assertEqual(t.approach, Approach.CONFLICT)
        self.assertEqual(t.verb, "Spook")
        self.assertTrue(t.is_test)

    def test_spook_difficulty_is_1(self):
        eng = make_engine_with_card_in_play(self.card)
        t = self.tests[0]
        self.assertEqual(t.difficulty_fn(eng, self.card), 1)


class CausticMulcherGetTestsTests(unittest.TestCase):
    """JSON: Wrest test — FIT + Conflict, difficulty 2."""

    def setUp(self):
        self.card = CausticMulcher()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_wrest_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.FIT)
        self.assertEqual(t.approach, Approach.CONFLICT)
        self.assertEqual(t.verb, "Wrest")
        self.assertTrue(t.is_test)

    def test_wrest_difficulty_is_2(self):
        eng = make_engine_with_card_in_play(self.card)
        t = self.tests[0]
        self.assertEqual(t.difficulty_fn(eng, self.card), 2)


class SunberryBrambleGetTestsTests(unittest.TestCase):
    """JSON: Pluck test — AWA + Reason, difficulty 2."""

    def setUp(self):
        self.card = SunberryBramble()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_pluck_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.AWA)
        self.assertEqual(t.approach, Approach.REASON)
        self.assertEqual(t.verb, "Pluck")
        self.assertTrue(t.is_test)

    def test_pluck_difficulty_is_2(self):
        eng = make_engine_with_card_in_play(self.card)
        t = self.tests[0]
        self.assertEqual(t.difficulty_fn(eng, self.card), 2)

    def test_pluck_success_adds_harm_and_soothes(self):
        eng = make_engine_with_card_in_play(self.card)
        # Give ranger some fatigue to soothe
        for i in range(3):
            fc = Card(id=f"fat-{i}", title=f"Fatigue {i}")
            eng.state.ranger.fatigue_stack.append(fc)
        t = self.tests[0]
        t.on_success(eng, 2, self.card)
        self.assertEqual(self.card.harm, 1)  # adds 1 harm to self
        # Soothes 2 fatigue
        self.assertEqual(len(eng.state.ranger.fatigue_stack), 1)

    def test_pluck_fail_fatigues_ranger(self):
        eng = make_engine_with_card_in_play(self.card)
        t = self.tests[0]
        initial_deck = len(eng.state.ranger.deck)
        t.on_fail(eng, 0, self.card)
        # Should fatigue ranger equal to presence
        presence = self.card.get_current_presence(eng)
        self.assertIsNotNone(presence)
        self.assertEqual(len(eng.state.ranger.deck), initial_deck - presence)


class OvergrownThicketGetTestsTests(unittest.TestCase):
    """JSON: Hunt test — AWA + Exploration, difficulty 1."""

    def setUp(self):
        self.card = OvergrownThicket()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_hunt_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.AWA)
        self.assertEqual(t.approach, Approach.EXPLORATION)
        self.assertEqual(t.verb, "Hunt")
        self.assertTrue(t.is_test)

    def test_hunt_difficulty_is_1(self):
        eng = make_engine_with_card_in_play(self.card, Area.ALONG_THE_WAY)
        t = self.tests[0]
        self.assertEqual(t.difficulty_fn(eng, self.card), 1)

    def test_hunt_success_adds_progress(self):
        eng = make_engine_with_card_in_play(self.card, Area.ALONG_THE_WAY)
        t = self.tests[0]
        t.on_success(eng, 3, self.card)
        self.assertEqual(self.card.progress, 3)


class MiddaySunGetTestsTests(unittest.TestCase):
    """JSON: Locate test — FOC + Reason, difficulty 2."""

    def setUp(self):
        self.card = MiddaySun()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_locate_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.FOC)
        self.assertEqual(t.approach, Approach.REASON)
        self.assertEqual(t.verb, "Locate")
        self.assertTrue(t.is_test)

    def test_locate_difficulty_is_2(self):
        eng = make_engine_with_card_in_play(self.card, Area.SURROUNDINGS)
        t = self.tests[0]
        self.assertEqual(t.difficulty_fn(eng, self.card), 2)

    def test_locate_success_adds_cloud_and_soothes(self):
        eng = make_engine_with_card_in_play(self.card, Area.SURROUNDINGS)
        # Add fatigue to soothe
        fc = Card(id="fat-0", title="Fatigue 0")
        eng.state.ranger.fatigue_stack.append(fc)
        initial_clouds = self.card.get_unique_token_count("cloud")
        t = self.tests[0]
        t.on_success(eng, 2, self.card)
        self.assertEqual(self.card.get_unique_token_count("cloud"), initial_clouds + 1)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), 0)  # soothes 1


class BiscuitBasketGetTestsTests(unittest.TestCase):
    """JSON: Give test (SPI+Connection, diff 2) and Sneak test (AWA+Reason, diff 1)."""

    def setUp(self):
        self.card = BiscuitBasket()
        self.tests = self.card.get_tests()

    def test_has_two_tests(self):
        self.assertEqual(len(self.tests), 2)

    def test_give_test_fields(self):
        give = next(t for t in self.tests if t.verb == "Give")
        self.assertEqual(give.aspect, Aspect.SPI)
        self.assertEqual(give.approach, Approach.CONNECTION)
        self.assertTrue(give.is_test)

    def test_give_test_difficulty_is_2(self):
        eng = make_engine_with_card_in_play(self.card, Area.PLAYER_AREA)
        give = next(t for t in self.tests if t.verb == "Give")
        self.assertEqual(give.difficulty_fn(eng, None), 2)

    def test_sneak_test_fields(self):
        sneak = next(t for t in self.tests if t.verb == "Sneak")
        self.assertEqual(sneak.aspect, Aspect.AWA)
        self.assertEqual(sneak.approach, Approach.REASON)
        self.assertTrue(sneak.is_test)

    def test_sneak_test_difficulty_is_1(self):
        eng = make_engine_with_card_in_play(self.card, Area.PLAYER_AREA)
        sneak = next(t for t in self.tests if t.verb == "Sneak")
        self.assertEqual(sneak.difficulty_fn(eng, None), 1)


class LoneTreeStationGetTestsTests(unittest.TestCase):
    """Uses get_search_test helper: AWA + Connection, verb 'Search'."""

    def setUp(self):
        self.card = LoneTreeStation()
        self.tests = self.card.get_tests()

    def test_has_one_test(self):
        self.assertEqual(len(self.tests), 1)

    def test_search_fields(self):
        t = self.tests[0]
        self.assertEqual(t.aspect, Aspect.AWA)
        self.assertEqual(t.approach, Approach.CONNECTION)
        self.assertEqual(t.verb, "Search")
        self.assertTrue(t.is_test)

    def test_search_source_is_lone_tree_station(self):
        t = self.tests[0]
        self.assertEqual(t.source_id, self.card.id)
        self.assertEqual(t.source_title, "Lone Tree Station")


if __name__ == "__main__":
    unittest.main()
