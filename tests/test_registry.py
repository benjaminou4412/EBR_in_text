"""
Tests for registry.py — common test wiring, search test helper, and filter logic.
"""

import unittest
from ebr.models import (
    GameState, RangerState, Card, Action, Area, Aspect, Approach,
    CardType, ChallengeIcon, CampaignTracker
)
from ebr.engine import GameEngine
from ebr.registry import (
    provide_common_tests, get_search_test, filter_tests_by_targets
)
from ebr.cards import (
    PeerlessPathfinder, LoneTreeStation, APerfectDay, SitkaBuck,
    OvergrownThicket, ProwlingWolhund
)
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_test_state() -> GameState:
    """Create a minimal test game state with a being and feature in play."""
    role = PeerlessPathfinder()
    location = LoneTreeStation()
    weather = APerfectDay()
    ranger = RangerState(
        name="Test Ranger",
        aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
        deck=[Card(id=f"deck-{i}", title=f"Deck Card {i}") for i in range(10)]
    )

    state = GameState(
        ranger=ranger,
        role_card=role,
        location=location,
        weather=weather,
        campaign_tracker=CampaignTracker(day_number=1)
    )
    state.areas[Area.SURROUNDINGS].append(location)
    state.areas[Area.SURROUNDINGS].append(weather)
    return state


def make_engine(state: GameState) -> GameEngine:
    """Create a GameEngine with deterministic choosers."""
    return GameEngine(
        state,
        card_chooser=lambda _e, cards: cards[0],
        response_decider=lambda _e, _p: True,
        order_decider=lambda _e, items, _p: items,
        option_chooser=lambda _e, opts, _p: opts[0],
        amount_chooser=lambda _e, lo, hi, _p: lo
    )


def find_action_by_id(actions: list[Action], action_id: str) -> Action:
    """Find an action by its id, raising if not found."""
    for a in actions:
        if a.id == action_id:
            return a
    raise ValueError(f"No action with id '{action_id}' in {[a.id for a in actions]}")


# ── Theme 1: Common test Action wiring ───────────────────────────────────

class CommonTestActionFieldTests(unittest.TestCase):
    """Verify Action field values for each of the 4 common tests."""

    def setUp(self):
        self.state = make_test_state()
        self.actions = provide_common_tests(self.state)

    def test_exactly_four_actions(self):
        self.assertEqual(len(self.actions), 4)

    def test_traverse_fields(self):
        a = find_action_by_id(self.actions, "common-traverse")
        self.assertEqual(a.aspect, Aspect.FIT)
        self.assertEqual(a.approach, Approach.EXPLORATION)
        self.assertEqual(a.verb, "Traverse")
        self.assertTrue(a.is_test)
        self.assertEqual(a.source_id, "common")

    def test_connect_fields(self):
        a = find_action_by_id(self.actions, "common-connect")
        self.assertEqual(a.aspect, Aspect.SPI)
        self.assertEqual(a.approach, Approach.CONNECTION)
        self.assertEqual(a.verb, "Connect")
        self.assertTrue(a.is_test)
        self.assertEqual(a.source_id, "common")

    def test_avoid_fields(self):
        a = find_action_by_id(self.actions, "common-avoid")
        self.assertEqual(a.aspect, Aspect.AWA)
        self.assertEqual(a.approach, Approach.CONFLICT)
        self.assertEqual(a.verb, "Avoid")
        self.assertTrue(a.is_test)
        self.assertEqual(a.source_id, "common")

    def test_remember_fields(self):
        a = find_action_by_id(self.actions, "common-remember")
        self.assertEqual(a.aspect, Aspect.FOC)
        self.assertEqual(a.approach, Approach.REASON)
        self.assertEqual(a.verb, "Remember")
        self.assertTrue(a.is_test)
        self.assertEqual(a.source_id, "common")


class CommonTestTargetProviderTests(unittest.TestCase):
    """Verify target providers return the correct card types."""

    def setUp(self):
        self.state = make_test_state()
        # Add a being and a feature to play areas
        self.being = SitkaBuck()
        self.feature = OvergrownThicket()
        self.state.areas[Area.WITHIN_REACH].append(self.being)
        self.state.areas[Area.ALONG_THE_WAY].append(self.feature)
        self.actions = provide_common_tests(self.state)

    def test_traverse_targets_features_and_location(self):
        a = find_action_by_id(self.actions, "common-traverse")
        targets = a.target_provider(self.state)
        # Should include the feature and the location
        self.assertIn(self.feature, targets)
        self.assertIn(self.state.location, targets)
        # Should NOT include the being
        self.assertNotIn(self.being, targets)

    def test_connect_targets_beings(self):
        a = find_action_by_id(self.actions, "common-connect")
        targets = a.target_provider(self.state)
        self.assertIn(self.being, targets)
        self.assertNotIn(self.feature, targets)

    def test_avoid_targets_beings(self):
        a = find_action_by_id(self.actions, "common-avoid")
        targets = a.target_provider(self.state)
        self.assertIn(self.being, targets)
        self.assertNotIn(self.feature, targets)

    def test_remember_has_no_target_provider(self):
        a = find_action_by_id(self.actions, "common-remember")
        self.assertIsNone(a.target_provider)


class CommonTestDifficultyTests(unittest.TestCase):
    """Verify difficulty functions use presence with min-1 floor."""

    def setUp(self):
        self.state = make_test_state()
        self.engine = make_engine(self.state)
        self.actions = provide_common_tests(self.state)

    def test_traverse_difficulty_is_presence(self):
        feature = OvergrownThicket()  # has presence, but features might not - let's use a being
        # OvergrownThicket is a feature, features may not have presence
        # Use location which has no presence - should fall back to 1
        a = find_action_by_id(self.actions, "common-traverse")
        difficulty = a.difficulty_fn(self.engine, self.state.location)
        self.assertEqual(difficulty, 1)  # location has no presence, defaults to 1

    def test_traverse_difficulty_with_presence(self):
        """Feature with presence should use that presence as difficulty."""
        card = Card(title="Test Feature", card_types={CardType.FEATURE}, presence=3)
        self.state.areas[Area.ALONG_THE_WAY].append(card)
        a = find_action_by_id(self.actions, "common-traverse")
        difficulty = a.difficulty_fn(self.engine, card)
        self.assertEqual(difficulty, 3)

    def test_connect_difficulty_is_presence(self):
        being = SitkaBuck()  # presence=1
        self.state.areas[Area.WITHIN_REACH].append(being)
        a = find_action_by_id(self.actions, "common-connect")
        difficulty = a.difficulty_fn(self.engine, being)
        self.assertEqual(difficulty, 1)

    def test_avoid_difficulty_is_presence(self):
        being = ProwlingWolhund()  # presence=2
        self.state.areas[Area.WITHIN_REACH].append(being)
        a = find_action_by_id(self.actions, "common-avoid")
        difficulty = a.difficulty_fn(self.engine, being)
        self.assertEqual(difficulty, 2)

    def test_difficulty_with_no_target_returns_1(self):
        """All difficulty functions return 1 when card is None."""
        for action_id in ["common-traverse", "common-connect", "common-avoid"]:
            with self.subTest(action_id=action_id):
                a = find_action_by_id(self.actions, action_id)
                self.assertEqual(a.difficulty_fn(self.engine, None), 1)

    def test_remember_difficulty_always_1(self):
        a = find_action_by_id(self.actions, "common-remember")
        self.assertEqual(a.difficulty_fn(self.engine, None), 1)

    def test_difficulty_minimum_is_1(self):
        """Even a card with presence 0 should have difficulty 1."""
        card = Card(title="Zero Presence", card_types={CardType.BEING}, presence=0)
        self.state.areas[Area.WITHIN_REACH].append(card)
        a = find_action_by_id(self.actions, "common-connect")
        difficulty = a.difficulty_fn(self.engine, card)
        self.assertEqual(difficulty, 1)


class CommonTestSuccessEffectTests(unittest.TestCase):
    """Verify success callbacks produce the correct game effects."""

    def setUp(self):
        self.state = make_test_state()
        self.engine = make_engine(self.state)
        self.actions = provide_common_tests(self.state)

    def test_traverse_success_adds_progress_to_feature(self):
        feature = OvergrownThicket()
        self.state.areas[Area.ALONG_THE_WAY].append(feature)
        a = find_action_by_id(self.actions, "common-traverse")
        a.on_success(self.engine, 3, feature)
        self.assertEqual(feature.progress, 3)

    def test_traverse_success_adds_progress_to_location(self):
        a = find_action_by_id(self.actions, "common-traverse")
        location = self.state.location
        a.on_success(self.engine, 2, location)
        self.assertEqual(location.progress, 2)

    def test_connect_success_adds_progress_to_being(self):
        being = SitkaBuck()
        self.state.areas[Area.WITHIN_REACH].append(being)
        a = find_action_by_id(self.actions, "common-connect")
        a.on_success(self.engine, 4, being)
        self.assertEqual(being.progress, 4)

    def test_avoid_success_exhausts_target(self):
        being = SitkaBuck()
        self.state.areas[Area.WITHIN_REACH].append(being)
        self.assertFalse(being.exhausted)
        a = find_action_by_id(self.actions, "common-avoid")
        a.on_success(self.engine, 0, being)
        self.assertTrue(being.exhausted)

    def test_remember_success_draws_card(self):
        initial_hand_size = len(self.state.ranger.hand)
        initial_deck_size = len(self.state.ranger.deck)
        a = find_action_by_id(self.actions, "common-remember")
        a.on_success(self.engine, 2, None)
        # Should have drawn 1 card
        self.assertEqual(len(self.state.ranger.hand), initial_hand_size + 1)
        self.assertLess(len(self.state.ranger.deck), initial_deck_size)


class CommonTestFailEffectTests(unittest.TestCase):
    """Verify fail callbacks produce the correct game effects."""

    def setUp(self):
        self.state = make_test_state()
        self.engine = make_engine(self.state)
        self.actions = provide_common_tests(self.state)

    def test_traverse_fail_injures_ranger(self):
        initial_injury = self.state.ranger.injury
        a = find_action_by_id(self.actions, "common-traverse")
        a.on_fail(self.engine, 0, None)
        self.assertEqual(self.state.ranger.injury, initial_injury + 1)

    def test_connect_has_no_fail_effect(self):
        """Connect's on_fail is the default no-op lambda."""
        a = find_action_by_id(self.actions, "common-connect")
        initial_injury = self.state.ranger.injury
        # Calling on_fail should not raise or change state
        a.on_fail(self.engine, 0, None)
        self.assertEqual(self.state.ranger.injury, initial_injury)

    def test_avoid_has_no_explicit_fail(self):
        """Avoid does not define a custom on_fail."""
        a = find_action_by_id(self.actions, "common-avoid")
        initial_injury = self.state.ranger.injury
        a.on_fail(self.engine, 0, None)
        self.assertEqual(self.state.ranger.injury, initial_injury)


# ── Theme 2: Search test helper ──────────────────────────────────────────

class SearchTestActionFieldTests(unittest.TestCase):
    """Verify get_search_test wires the Action correctly."""

    def setUp(self):
        self.source_card = Card(id="test-source-123", title="Test Source Card")
        self.action = get_search_test(self.source_card, "Search")

    def test_id_built_from_source_card(self):
        self.assertEqual(self.action.id, "test-source-123-search-test")

    def test_name_built_from_source_title(self):
        self.assertIn("Test Source Card", self.action.name)

    def test_aspect_is_awa(self):
        self.assertEqual(self.action.aspect, Aspect.AWA)

    def test_approach_is_connection(self):
        self.assertEqual(self.action.approach, Approach.CONNECTION)

    def test_is_test(self):
        self.assertTrue(self.action.is_test)

    def test_verb_is_passed_through(self):
        self.assertEqual(self.action.verb, "Search")

    def test_verb_varies_with_argument(self):
        action2 = get_search_test(self.source_card, "Harvest")
        self.assertEqual(action2.verb, "Harvest")

    def test_source_id_matches_card(self):
        self.assertEqual(self.action.source_id, "test-source-123")

    def test_source_title_matches_card(self):
        self.assertEqual(self.action.source_title, "Test Source Card")

    def test_target_provider_returns_source_card(self):
        state = make_test_state()
        targets = self.action.target_provider(state)
        self.assertEqual(targets, [self.source_card])


class SearchTestSuccessEffectTests(unittest.TestCase):
    """Verify _search_test_success scouts path cards then draws 1."""

    def setUp(self):
        self.state = make_test_state()
        # Put some cards in the path deck
        self.path_cards = [Card(id=f"path-{i}", title=f"Path Card {i}",
                                card_types={CardType.PATH, CardType.FEATURE},
                                starting_area=Area.ALONG_THE_WAY)
                           for i in range(5)]
        self.state.path_deck = list(self.path_cards)
        self.engine = make_engine(self.state)

    def test_success_draws_path_card_into_play(self):
        source = Card(id="src", title="Source")
        action = get_search_test(source, "Search")
        initial_path_deck_size = len(self.state.path_deck)
        action.on_success(self.engine, 2, None)
        # Should have drawn 1 card from path deck into play
        self.assertLess(len(self.state.path_deck), initial_path_deck_size)


# ── Theme 3: filter_tests_by_targets ─────────────────────────────────────

class FilterTestsByTargetsTests(unittest.TestCase):
    """Verify all 3 branches of filter_tests_by_targets."""

    def setUp(self):
        self.state = make_test_state()

    def test_non_test_action_always_included(self):
        """Actions with is_test=False pass through regardless of targets."""
        non_test = Action(id="play-1", name="Play Card", aspect="", approach="",
                          is_test=False, target_provider=lambda _s: [])
        result = filter_tests_by_targets([non_test], self.state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "play-1")

    def test_no_target_test_always_included(self):
        """Tests with target_provider=None (like Remember) always included."""
        remember_like = Action(id="no-target", name="Remember-like", aspect=Aspect.FOC,
                               approach=Approach.REASON, is_test=True, target_provider=None)
        result = filter_tests_by_targets([remember_like], self.state)
        self.assertEqual(len(result), 1)

    def test_test_with_empty_targets_excluded(self):
        """Tests whose target_provider returns [] are excluded."""
        no_targets = Action(id="empty-targets", name="No targets", aspect=Aspect.FIT,
                            approach=Approach.EXPLORATION, is_test=True,
                            target_provider=lambda _s: [])
        result = filter_tests_by_targets([no_targets], self.state)
        self.assertEqual(len(result), 0)

    def test_test_with_valid_targets_included(self):
        """Tests whose target_provider returns non-empty list are included."""
        being = SitkaBuck()
        self.state.areas[Area.WITHIN_REACH].append(being)
        has_targets = Action(id="has-targets", name="Has targets", aspect=Aspect.SPI,
                             approach=Approach.CONNECTION, is_test=True,
                             target_provider=lambda s: s.beings_in_play())
        result = filter_tests_by_targets([has_targets], self.state)
        self.assertEqual(len(result), 1)

    def test_mixed_filtering(self):
        """Mix of included and excluded actions filters correctly."""
        being = SitkaBuck()
        self.state.areas[Area.WITHIN_REACH].append(being)

        actions = [
            Action(id="non-test", name="Play", aspect="", approach="",
                   is_test=False, target_provider=lambda _s: []),
            Action(id="no-target", name="Remember", aspect=Aspect.FOC,
                   approach=Approach.REASON, is_test=True, target_provider=None),
            Action(id="empty", name="Empty", aspect=Aspect.FIT,
                   approach=Approach.EXPLORATION, is_test=True,
                   target_provider=lambda _s: []),
            Action(id="valid", name="Valid", aspect=Aspect.SPI,
                   approach=Approach.CONNECTION, is_test=True,
                   target_provider=lambda s: s.beings_in_play()),
        ]
        result = filter_tests_by_targets(actions, self.state)
        result_ids = [a.id for a in result]
        self.assertIn("non-test", result_ids)
        self.assertIn("no-target", result_ids)
        self.assertNotIn("empty", result_ids)
        self.assertIn("valid", result_ids)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
