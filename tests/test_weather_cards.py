#type: ignore
import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import APerfectDay, MiddaySun
from tests.test_utils import make_challenge_card


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        hand=[],
        aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
        deck=[Card(title=f"Dummy {i}") for i in range(20)],
        discard=[],
        fatigue_stack=[]
    )


def stack_deck(state: GameState, aspect: Aspect, modifier: int, icon: ChallengeIcon):
    """Helper to put a specific challenge card on top of the deck"""
    state.challenge_deck.deck.insert(0,make_challenge_card(icon=icon, awa=modifier if aspect == Aspect.AWA else 0,
                                                       fit=modifier if aspect == Aspect.FIT else 0,
                                                       spi=modifier if aspect == Aspect.SPI else 0,
                                                       foc=modifier if aspect == Aspect.FOC else 0))


class APerfectDayTests(unittest.TestCase):
    """Tests for A Perfect Day weather card"""

    def test_mountain_effect_adds_progress_when_test_added_progress(self):
        """Test that Mountain effect adds bonus progress when the test added progress"""
        weather = APerfectDay()
        target = Card(
            id="test-target",
            title="Test Feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=2,
            progress_threshold=5,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        ranger.aspects = {Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [target],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        # Stack deck with Mountain icon and +1 modifier to ensure success
        stack_deck(state, Aspect.FIT, +1, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)
        weather.enters_play(eng, Area.SURROUNDINGS)

        # Create a test that adds progress
        from src.registry import provide_common_tests
        tests = provide_common_tests(state)
        traverse_action = next(t for t in tests if "Traverse" in t.name)

        # Perform the test (should succeed and add progress)
        # Target has presence 2, so we need effort >= 2
        decision = CommitDecision(energy=2, hand_indices=[])
        outcome = eng.perform_test(traverse_action, decision, target.id)

        # Verify test succeeded and added progress
        self.assertTrue(outcome.success, "Test should succeed")
        # Traverse adds progress equal to effort (2 energy + 1 modifier = 3 effort)
        # Then Mountain effect should add 1 more
        self.assertEqual(target.progress, 4, "Target should have 4 progress (3 from test + 1 from Mountain effect)")

    def test_mountain_effect_does_nothing_when_test_added_no_progress(self):
        """Test that Mountain effect does nothing when test didn't add progress"""
        weather = APerfectDay()
        being = Card(
            id="test-being",
            title="Test Being",
            card_types={CardType.PATH, CardType.BEING},
            presence=2,
            progress_threshold=5,
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

        # Stack deck with Mountain icon
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Create a test that does NOT add progress (e.g., Search doesn't add progress to target)
        from src.registry import provide_common_tests
        tests = provide_common_tests(state)
        search_action = next(t for t in tests if "Remember" in t.name)

        # Perform the test
        decision = CommitDecision(energy=1, hand_indices=[])
        outcome = eng.perform_test(search_action, decision, being.id)

        # Verify being has no progress (Search doesn't add progress)
        self.assertEqual(being.progress, 0, "Being should have 0 progress (Search doesn't add progress)")

    def test_refresh_removes_cloud_token(self):
        """Test that refresh effect removes 1 cloud token"""
        weather = APerfectDay()
        weather.unique_tokens = {"cloud": 3}  # Start with 3 clouds

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        eng = GameEngine(state)
        weather.enters_play(eng, Area.SURROUNDINGS)

        # Trigger refresh
        eng.phase4_refresh()

        # Should have 2 clouds remaining
        self.assertEqual(weather.get_unique_token_count("Cloud"), 2,
                        "Should have 2 clouds after refresh (started with 3, removed 1)")

    def test_flips_to_midday_sun_when_clouds_reach_zero(self):
        """Test that A Perfect Day flips to Midday Sun when clouds reach 0"""
        weather = APerfectDay()
        weather.unique_tokens = {"cloud": 1}  # Start with 1 cloud

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        eng = GameEngine(state)
        weather.enters_play(eng, Area.SURROUNDINGS)
        # Trigger refresh (should remove last cloud and flip)
        eng.phase4_refresh()

        # Verify weather flipped
        self.assertIsInstance(state.weather, MiddaySun, "Weather should have flipped to Midday Sun")
        self.assertNotIn(weather, state.areas[Area.SURROUNDINGS],
                        "Old weather should be removed from play")
        self.assertIn(state.weather, state.areas[Area.SURROUNDINGS],
                     "New weather should be in Surroundings")


class MiddaySunTests(unittest.TestCase):
    """Tests for Midday Sun weather card"""

    def test_sun_effect_fatigues_ranger(self):
        """Test that Sun effect causes 1 fatigue"""
        weather = MiddaySun()

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        stack_deck(state, Aspect.FIT, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Trigger Sun effect directly
        handlers = weather.get_challenge_handlers()
        self.assertIsNotNone(handlers)
        self.assertIn(ChallengeIcon.SUN, handlers)

        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved, "Sun effect should resolve")
        self.assertEqual(len(ranger.fatigue_stack), 1, "Should suffer 1 fatigue")
        self.assertEqual(len(ranger.deck), initial_deck_size - 1, "Deck should be 1 card smaller")

    def test_refresh_adds_cloud_token(self):
        """Test that refresh effect adds 1 cloud token"""
        weather = MiddaySun()
        weather.unique_tokens = {"cloud": 1}  # Start with 1 cloud

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        eng = GameEngine(state)
        weather.enters_play(eng, Area.SURROUNDINGS)

        # Trigger refresh
        eng.phase4_refresh()

        # Should have 2 clouds now
        self.assertEqual(weather.get_unique_token_count("Cloud"), 2,
                        "Should have 2 clouds after refresh (started with 1, added 1)")

    def test_flips_to_perfect_day_when_clouds_reach_three(self):
        """Test that Midday Sun flips to A Perfect Day when clouds reach 3"""
        weather = MiddaySun()
        weather.unique_tokens = {"cloud": 2}  # Start with 2 clouds

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        state.weather = weather

        eng = GameEngine(state)
        weather.enters_play(eng, Area.SURROUNDINGS)

        # Trigger refresh (should add 1 cloud, reaching 3, and flip)
        eng.phase4_refresh()

        # Verify weather flipped
        self.assertIsInstance(state.weather, APerfectDay, "Weather should have flipped to A Perfect Day")
        self.assertNotIn(weather, state.areas[Area.SURROUNDINGS],
                        "Old weather should be removed from play")
        self.assertIn(state.weather, state.areas[Area.SURROUNDINGS],
                     "New weather should be in Surroundings")
        # New A Perfect Day should start with 3 clouds
        self.assertEqual(state.weather.get_unique_token_count("Cloud"), 3,
                        "New A Perfect Day should have 3 clouds")


if __name__ == '__main__':
    unittest.main()
