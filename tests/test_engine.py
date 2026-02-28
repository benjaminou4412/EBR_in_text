import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import *
from ebr.registry import *
from tests.test_utils import MockChallengeDeck, make_challenge_card


def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    """Helper to stack the challenge deck with a single predetermined card."""
    # Build mods based on which aspect is being tested
    awa_mod = mod if aspect == Aspect.AWA else 0
    fit_mod = mod if aspect == Aspect.FIT else 0
    spi_mod = mod if aspect == Aspect.SPI else 0
    foc_mod = mod if aspect == Aspect.FOC else 0

    state.challenge_deck = MockChallengeDeck([make_challenge_card(
        icon=symbol,
        awa=awa_mod,
        fit=fit_mod,
        spi=spi_mod,
        foc=foc_mod
    )])


class EngineTests(unittest.TestCase):
    def test_thicket_progress_and_energy(self):
        # Setup state: one feature (thicket), ranger with two exploration cards in hand
        thicket = OvergrownThicket()
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Create two pseudo cards with Exploration+1 each
        ranger.hand = [
            Card(id="c1", title="E+1", approach_icons={Approach.EXPLORATION: 1}),
            Card(id="c2", title="E+1", approach_icons={Approach.EXPLORATION: 1})
        ]
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)


        # Perform action using the engine API directly
        thicket_test = thicket.get_tests()
        if thicket_test is None:
            raise RuntimeError(f"Failed to fetch thicket test")
        else:
            act = thicket_test[0]
            eng.perform_test(
                act,
                decision=CommitDecision(energy=1, hand_indices=[0, 1]),
                target_id=None)

            self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
            self.assertEqual(thicket.progress, 3)
            self.assertEqual(len(state.ranger.hand), 0)
    
    def test_single_energy(self):
        # Setup state: one feature (thicket), ranger with no cards in hand
        thicket = OvergrownThicket()
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform action using the engine API directly
        thicket_test = thicket.get_tests()
        if thicket_test is None:
            raise RuntimeError(f"Failed to fetch thicket test")
        else:
            act = thicket_test[0]
            eng.perform_test(
                act,
                decision=CommitDecision(energy=1, hand_indices=[]),
                target_id=None)

            self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
            self.assertEqual(thicket.progress, 1)
            self.assertEqual(len(state.ranger.hand), 0)

    def test_traverse_feature(self):
        feat = Card(
            title="Feature A",
            id="feat1",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=3
        )
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.hand = [Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1})]
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feat],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.FIT, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        tests = provide_common_tests(state)
        act = tests[0]
        eng.perform_test(
            act,
            decision=CommitDecision(energy=1, hand_indices=[0]),
            target_id=feat.id)

        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)
        self.assertEqual(feat.progress, 2)
        self.assertEqual(state.ranger.injury, 0)

    def test_clear_on_progress_threshold(self):
        # Setup: Feature with progress_threshold=2
        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=2,
        )
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.hand = [Card(id="c1", title="E+1", approach_icons={Approach.EXPLORATION: 1})]
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform action that adds exactly enough progress to clear (1 energy + 1 icon = 2 effort)
        def add_progress_callback(_s: GameEngine, eff: int, _t: Card | None) -> None:
            feature.add_progress(eff)

        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=add_progress_callback,
        )
        eng.perform_test(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Feature should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 1, "Feature should be removed from zones; only role card remains")
        self.assertEqual(len(state.path_discard), 1, "Feature should be in path_discard")
        self.assertEqual(state.path_discard[0].id, "test-feature", "Cleared feature should be the one we added progress to")

    def test_clear_on_harm_threshold(self):
        # Setup: Being with harm_threshold=2
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            harm_threshold=2,
        )
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 5, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Add a card with +1 Conflict icon so we get 2 total effort (1 energy + 1 icon)
        ranger.hand = [Card(id="c1", title="Conflict+1", approach_icons={Approach.CONFLICT: 1})]
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform action that adds exactly enough harm to clear (1 energy + 1 icon = 2 effort = 2 harm)
        def add_harm_callback(_s: GameEngine, eff: int, _t: Card | None) -> None:
            being.add_harm(eff)

        act = Action(
            id="test-harm",
            name="test harm",
            aspect=Aspect.AWA,
            approach=Approach.CONFLICT,
            difficulty_fn=lambda _s, _t: 1,
            on_success=add_harm_callback,
        )
        eng.perform_test(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Being should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 1, "Being should be removed from zones; only role card remains")
        self.assertEqual(len(state.path_discard), 1, "Being should be in path_discard")
        self.assertEqual(state.path_discard[0].id, "test-being", "Cleared being should be the one we added harm to")

    def test_no_clear_below_threshold(self):
        # Setup: Feature with progress_threshold=3
        feature = Card(
            title="Test Feature 2",
            id="test-feature-2",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=3,
        )
        ranger = RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Add progress that doesn't reach threshold (only 1 effort)
        def add_progress_callback(_s: GameEngine, eff: int, _t: Card | None) -> None:
            feature.add_progress(eff)

        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=add_progress_callback,
        )
        eng.perform_test(act, decision=CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Assert: Feature should still be in zones (not cleared)
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 2, "Feature should still be in play along with role card")
        self.assertEqual(len(state.path_discard), 0, "Nothing should be discarded")
        self.assertEqual(feature.progress, 1, "Feature should have 1 progress")


class NonTestActionTests(unittest.TestCase):
    """Tests for non-test actions (Rest, Play, Exhaust) routed through perform_test."""

    def _make_engine(self, target: Card | None = None) -> GameEngine:
        ranger = RangerState(
            name="Ranger", hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1},
        )
        areas = {
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [target] if target else [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        }
        return GameEngine(GameState(ranger=ranger, areas=areas))

    def test_non_test_action_calls_on_success_with_zero_effort(self):
        """on_success must receive effort=0 for non-test actions."""
        received: list[tuple] = []

        def track_success(engine, effort, target):
            received.append((effort, target))

        action = Action(
            id="rest", name="Rest", aspect="", approach="",
            is_test=False, on_success=track_success,
        )
        eng = self._make_engine()
        eng.perform_test(action, CommitDecision(), target_id=None)

        self.assertEqual(len(received), 1, "on_success should be called exactly once")
        self.assertEqual(received[0][0], 0, "effort passed to on_success should be 0")
        self.assertIsNone(received[0][1], "target should be None when no target_id given")

    def test_non_test_action_returns_correct_outcome(self):
        """Returned ChallengeOutcome should indicate success with zero effort."""
        action = Action(
            id="rest", name="Rest", aspect="", approach="",
            is_test=False,
        )
        eng = self._make_engine()
        outcome = eng.perform_test(action, CommitDecision(), target_id=None)

        self.assertTrue(outcome.success)
        self.assertEqual(outcome.resulting_effort, 0)
        self.assertEqual(outcome.modifier, 0)
        self.assertEqual(outcome.symbol, ChallengeIcon.SUN)

    def test_non_test_action_passes_target_to_on_success(self):
        """on_success receives the resolved target card when target_id is provided."""
        received_target: list = []
        target = Card(id="t1", title="Target Feature")

        action = Action(
            id="play", name="Play", aspect="", approach="",
            is_test=False, is_play=True,
            on_success=lambda eng, effort, t: received_target.append(t),
        )
        eng = self._make_engine(target=target)
        eng.perform_test(action, CommitDecision(), target_id="t1")

        self.assertEqual(len(received_target), 1)
        self.assertIs(received_target[0], target)

    def test_non_test_action_does_not_draw_challenge_card(self):
        """Non-test actions should skip the challenge deck entirely."""
        action = Action(
            id="rest", name="Rest", aspect="", approach="",
            is_test=False,
        )
        eng = self._make_engine()
        # Don't set up a challenge deck at all — if it tries to draw, it'll error
        eng.state.challenge_deck = None  # type: ignore[assignment]
        # Should not raise
        eng.perform_test(action, CommitDecision(), target_id=None)


class CommonTestsTests(unittest.TestCase):
    """Tests for the four common tests: Traverse, Connect, Avoid, Remember"""

    def test_traverse_success(self):
        """Test successful Traverse test adds progress"""
        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=3
        )
        ranger = RangerState(
            name="Ranger",
            hand=[Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1})],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.FIT, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Traverse: FIT + Exploration
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Commit 1 FIT energy + 1 card with Exploration = 2 effort
        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[0]), target_id=feature.id)

        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)
        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)  # Started with 2, spent 1
        self.assertEqual(len(state.ranger.hand), 0)  # Committed card discarded
        self.assertEqual(state.ranger.injury, 0)  # No injury on success

    def test_traverse_failure(self):
        """Test failed Traverse test calls injure(), which discards fatigue and increments injury"""
        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=2,  # Difficulty is 2
            progress_threshold=3
        )
        # Put some cards in fatigue stack so we can verify injure() discards them
        fatigue_cards = [Card(id=f"fat{i}", title=f"Fatigue {i}") for i in range(3)]
        ranger = RangerState(
            name="Ranger",
            hand=[],  # No cards to commit
            fatigue_stack=fatigue_cards,
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.FIT, -1, ChallengeIcon.SUN)

        eng = GameEngine(state)  # Negative modifier

        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Commit 1 FIT energy + 0 cards + (-1 modifier) = 0 effort, difficulty 2
        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[]), target_id=feature.id)

        self.assertFalse(outcome.success)
        self.assertEqual(feature.progress, 0)  # No progress on failure
        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)
        self.assertEqual(state.ranger.injury, 1)  # Injury on failure
        # injure() should have discarded the entire fatigue stack
        self.assertEqual(len(state.ranger.fatigue_stack), 0, "Fatigue stack should be cleared by injure()")
        self.assertEqual(len(state.ranger.discard), 3, "Fatigue cards should move to discard")

    def test_connect_success(self):
        """Test successful Connect test adds progress to being"""
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=3
        )
        ranger = RangerState(
            name="Ranger",
            hand=[Card(id="c1", title="Conn+1", approach_icons={Approach.CONNECTION: 1})],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Connect: SPI + Connection
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit 1 SPI energy + 1 card with Connection = 2 effort
        outcome = eng.perform_test(connect, CommitDecision(energy=1, hand_indices=[0]), target_id=being.id)

        self.assertTrue(outcome.success)
        self.assertEqual(being.progress, 2)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)  # Started with 2, spent 1
        self.assertEqual(len(state.ranger.hand), 0)  # Committed card discarded

    def test_connect_failure(self):
        """Test failed Connect test has no special failure effect"""
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=3,  # High difficulty
            progress_threshold=5
        )
        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.SPI, -2, ChallengeIcon.SUN)

        eng = GameEngine(state)

        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit 1 SPI + (-2 modifier) = 0 effort (clamped), difficulty 3
        outcome = eng.perform_test(connect, CommitDecision(energy=1, hand_indices=[]), target_id=being.id)

        self.assertFalse(outcome.success)
        self.assertEqual(being.progress, 0)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)
        self.assertEqual(state.ranger.injury, 0)  # Connect has no failure effect

    def test_avoid_success(self):
        """Test successful Avoid test exhausts the being"""
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            exhausted=False
        )
        ranger = RangerState(
            name="Ranger",
            hand=[Card(id="conf1", title="Conflict+1", approach_icons={Approach.CONFLICT: 1})],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Avoid: AWA + Conflict
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        avoid = next(a for a in actions if a.id == "common-avoid")

        # Commit 1 AWA energy + 1 card with Conflict = 2 effort
        outcome = eng.perform_test(avoid, CommitDecision(energy=1, hand_indices=[0]), target_id=being.id)

        self.assertTrue(outcome.success)
        self.assertTrue(being.exhausted)  # Being should be exhausted
        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)  # Started with 3, spent 1
        self.assertEqual(len(state.ranger.hand), 0)

    def test_avoid_failure(self):
        """Test failed Avoid test has no special failure effect"""
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=3,
            exhausted=False
        )
        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, -2, ChallengeIcon.SUN)

        eng = GameEngine(state)

        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        avoid = next(a for a in actions if a.id == "common-avoid")

        # Commit 1 AWA + (-2 modifier) = 0 effort, difficulty 3
        outcome = eng.perform_test(avoid, CommitDecision(energy=1, hand_indices=[]), target_id=being.id)

        self.assertFalse(outcome.success)
        self.assertFalse(being.exhausted)  # Being not exhausted on failure
        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(state.ranger.injury, 0)  # Avoid has no failure effect

    def test_sitka_doe_spook_success_moves_to_along_the_way(self):
        """Test that Sitka Doe's Spook test moves it from Within Reach to Along the Way on success"""
        from ebr.cards import SitkaDoe
        doe = SitkaDoe()
        ranger = RangerState(
            name="Ranger",
            hand=[Card(id="conf1", title="Conflict+1", approach_icons={Approach.CONFLICT: 1})],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Get the Sitka Doe spook action from registry
        from ebr.registry import provide_card_tests
        actions = provide_card_tests(eng)
        spook = next(a for a in actions if a.verb == "Spook" and "Sitka Doe" in a.name)

        # Perform the spook action with 1 SPI energy + 1 Conflict card = 2 effort, difficulty 1
        outcome = eng.perform_test(spook, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)  # Started with 2, spent 1

        # Verify the doe moved from Within Reach to Along the Way
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 0, "Doe should no longer be in Within Reach")
        self.assertEqual(len(state.areas[Area.ALONG_THE_WAY]), 1, "Doe should now be in Along the Way")
        self.assertEqual(state.areas[Area.ALONG_THE_WAY][0].id, doe.id, "The card in Along the Way should be the doe")

    def test_sitka_doe_spook_failure_does_not_move(self):
        """Test that failing Sitka Doe's Spook test does not move it"""
        from ebr.cards import SitkaDoe
        doe = SitkaDoe()
        ranger = RangerState(
            name="Ranger",
            hand=[],  # No cards to commit
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.SPI, -2, ChallengeIcon.SUN)

        eng = GameEngine(state)  # Negative modifier to ensure failure

        # Get the Sitka Doe spook action from registry
        from ebr.registry import provide_card_tests
        actions = provide_card_tests(eng)
        spook = next(a for a in actions if a.verb == "Spook" and "Sitka Doe" in a.name)

        # Perform the spook action with 1 SPI energy + no cards + (-2 modifier) = 0 effort (clamped), difficulty 1
        outcome = eng.perform_test(spook, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify test failed
        self.assertFalse(outcome.success)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)  # Started with 2, spent 1

        # Verify the doe stayed in Within Reach
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 1, "Doe should still be in Within Reach")
        self.assertEqual(len(state.areas[Area.ALONG_THE_WAY]), 0, "Nothing should be in Along the Way")
        self.assertEqual(state.areas[Area.WITHIN_REACH][0].id, doe.id, "The card in Within Reach should be the doe")

    def test_sitka_doe_sun_effect_moves_bucks_to_within_reach(self):
        """Test that Sitka Doe's sun challenge effect moves all Sitka Bucks within reach"""
        from ebr.cards import SitkaDoe, SitkaBuck
        doe = SitkaDoe()
        buck_a = SitkaBuck()
        buck_b = SitkaBuck()
        buck_a.exhausted = True
        buck_b.exhausted = True #Suppress Sitka Buck challenge effect

        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [buck_a, buck_b],  # Bucks start here
                Area.WITHIN_REACH: [doe],  # Doe is here
                Area.PLAYER_AREA: [],
            }
        )
        # Draw SUN symbol to trigger sun effect
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform any test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify both bucks moved to Within Reach
        self.assertEqual(len(state.areas[Area.ALONG_THE_WAY]), 0, "No bucks should remain in Along the Way")
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 3, "Doe + 2 bucks should be Within Reach")

        # Check that the bucks are the ones that moved
        within_reach_ids = {card.id for card in state.areas[Area.WITHIN_REACH]}
        self.assertIn(buck_a.id, within_reach_ids, "Buck A should be in Within Reach")
        self.assertIn(buck_b.id, within_reach_ids, "Buck B should be in Within Reach")
        self.assertIn(doe.id, within_reach_ids, "Doe should still be in Within Reach")

    def test_sitka_doe_mountain_effect_harms_doe_with_predator_presence(self):
        """Test that Sitka Doe's mountain effect exhausts a predator and adds harm equal to its presence"""
        from ebr.cards import SitkaDoe, ProwlingWolhund
        doe = SitkaDoe()
        wolhund = ProwlingWolhund()

        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [wolhund],  # Active predator
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        # Draw MOUNTAIN symbol to trigger mountain effect
        # Use deterministic chooser (default picks first option)
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Verify initial state
        self.assertFalse(wolhund.exhausted, "Wolhund should start active")
        self.assertEqual(doe.harm, 0, "Doe should start with 0 harm")

        # Perform any test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify wolhund is exhausted and doe took harm equal to wolhund's presence
        self.assertTrue(wolhund.exhausted, "Wolhund should be exhausted")
        self.assertEqual(doe.harm, wolhund.presence, f"Doe should have {wolhund.presence} harm (wolhund's presence)")

    def test_sitka_doe_mountain_effect_no_active_predators(self):
        """Test that Sitka Doe's mountain effect does nothing when no active predators exist"""
        from ebr.cards import SitkaDoe, ProwlingWolhund
        doe = SitkaDoe()
        wolhund = ProwlingWolhund()
        wolhund.exhausted = True  # Predator is exhausted

        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [wolhund],  # Exhausted predator
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        # Draw MOUNTAIN symbol
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Verify initial state
        self.assertEqual(doe.harm, 0, "Doe should start with 0 harm")

        # Perform any test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify no harm was dealt (no active predators)
        self.assertEqual(doe.harm, 0, "Doe should still have 0 harm (no active predators)")
        self.assertTrue(wolhund.exhausted, "Wolhund should still be exhausted")


class WalkWithMeTests(unittest.TestCase):
    """Tests for Walk With Me response card"""

    def test_walk_with_me_standard_play(self):
        """Test Walk With Me triggers after successful Traverse, player says yes, and has energy"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5,
            harm_threshold=3
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],  # Walk With Me in hand
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}  # Has SPI
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [being],  # Target for Walk With Me
                Area.PLAYER_AREA: [],
            }
        )

        # Deterministic choosers: always say yes, always pick first option
        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        def pick_first(_engine: GameEngine, choices: list[Card]) -> Card:
            return choices[0]

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        card_chooser=pick_first,
                        response_decider=always_yes)


        # Perform Traverse test (3 effort = 1 FIT energy + 2 Exploration icons)
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Add cards with Exploration icons for effort
        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))
        ranger.hand.append(Card(id="e2", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1, 2]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.resulting_effort, 3)  # 1 energy + 2 icons
        self.assertEqual(feature.progress, 3)  # Feature gets 3 progress from test

        # Verify Walk With Me was played
        self.assertNotIn(wwm, state.ranger.hand, "Walk With Me should be removed from hand")
        self.assertIn(wwm, state.ranger.discard, "Walk With Me should be in discard")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1, "Should have spent 1 SPI (started with 2)")

        # Verify being got progress equal to effort (3)
        self.assertEqual(being.progress, 3, "Being should have 3 progress from Walk With Me")

        # Verify listener was cleaned up
        self.assertEqual(len(eng.listeners), 0, "Listener should be removed after triggering")

    def test_walk_with_me_player_declines(self):
        """Test Walk With Me when player chooses not to play it"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )

        # Response decider says NO
        def always_no(_engine: GameEngine, _prompt: str) -> bool:
            return False

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_no)

        

        # Perform Traverse test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)

        # Verify Walk With Me was NOT played
        self.assertIn(wwm, state.ranger.hand, "Walk With Me should still be in hand")
        self.assertNotIn(wwm, state.ranger.discard, "Walk With Me should not be discarded")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 2, "SPI should be unchanged")

        # Verify being got no progress
        self.assertEqual(being.progress, 0, "Being should have no progress")

        # Verify listener is still active (can trigger again)
        self.assertEqual(len(eng.listeners), 1, "Listener should remain active")

    def test_walk_with_me_insufficient_energy(self):
        """Test Walk With Me when player has insufficient SPI"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )
        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 0, Aspect.FOC: 1}  # NO SPI!
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )

        # Player says yes but has no energy
        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_yes)

        

        # Perform Traverse test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)

        # Verify Walk With Me was NOT played (insufficient energy)
        self.assertIn(wwm, state.ranger.hand, "Walk With Me should still be in hand (no energy)")
        self.assertNotIn(wwm, state.ranger.discard, "Walk With Me should not be discarded")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 0, "SPI should still be 0")

        # Verify being got no progress
        self.assertEqual(being.progress, 0, "Being should have no progress")

        # Verify listener remains active
        self.assertEqual(len(eng.listeners), 1, "Listener should remain active")

    def test_walk_with_me_no_valid_targets(self):
        """Test Walk With Me when there are no Beings in play to target"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],  # NO BEINGS!
                Area.PLAYER_AREA: [],
            }
        )

        # Player says yes
        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_yes)

        

        # Perform Traverse test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)

        # Verify Walk With Me was played (can be played even with no valid targets)
        self.assertNotIn(wwm, state.ranger.hand, "Walk With Me should not be in hand")
        self.assertIn(wwm, state.ranger.discard, "Walk With Me should be in discard")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1, "SPI should be spent")

        # Verify listener remains active
        self.assertEqual(len(eng.listeners), 0, "Listener should be cleaned up")

    def test_walk_with_me_only_triggers_on_traverse(self):
        """Test that Walk With Me only triggers on Traverse tests, not Connect tests"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        being = Card(
            title="Test Being",
            id="test-being",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: [],
            }
        )

        # Player would say yes if prompted
        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.FIT, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_yes)

        # Perform CONNECT test (not Traverse!)
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        ranger.hand.append(Card(id="c1", title="Conn+1", approach_icons={Approach.CONNECTION: 1}))

        outcome = eng.perform_test(connect, CommitDecision(energy=1, hand_indices=[1]), target_id=being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(being.progress, 2)  # From Connect test

        # Verify Walk With Me did NOT trigger
        self.assertIn(wwm, state.ranger.hand, "Walk With Me should still be in hand")
        self.assertNotIn(wwm, state.ranger.discard, "Walk With Me should not be discarded")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1, "SPI should only go down by 1 from initiating the Connect")

        # Being should only have progress from Connect, not from Walk With Me
        self.assertEqual(being.progress, 2, "Being should only have 2 progress from Connect test")

        # Listener should still be active
        self.assertEqual(len(eng.listeners), 1, "Listener should remain active for future Traverse tests")

    def test_walk_with_me_chooses_correct_being(self):
        """Test that Walk With Me targets the Being chosen by card_chooser"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )
        being_a = Card(
            title="Being A",
            id="being-a",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )
        being_b = Card(
            title="Being B",
            id="being-b",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[wwm],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [being_a, being_b],  # Two beings
                Area.PLAYER_AREA: [],
            }
        )

        # Chooser picks Being B specifically
        def pick_being_b(_engine: GameEngine, choices: list[Card]) -> Card:
            return next(c for c in choices if c.id == "being-b")

        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        card_chooser=pick_being_b,
                        response_decider=always_yes)


        # Perform Traverse test with 5 effort
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Add 4 exploration icons for total of 5 effort
        for i in range(4):
            ranger.hand.append(Card(id=f"e{i}", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1, 2, 3, 4]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.resulting_effort, 5)

        # Verify Walk With Me was played
        self.assertIn(wwm, state.ranger.discard, "Walk With Me should be discarded")

        # Verify Being B got the progress, not Being A
        self.assertEqual(being_b.progress, 5, "Being B should have 5 progress from Walk With Me")
        self.assertEqual(being_a.progress, 0, "Being A should have no progress")

    def test_walk_with_me_listener_created_on_enters_hand(self):
        """Test that Walk With Me creates the correct listener when entering hand"""
        from ebr.cards import WalkWithMe
        wwm = WalkWithMe()

        # Create minimal engine for testing
        state = GameState(
            ranger=RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 1, Aspect.FIT: 1, Aspect.SPI: 1, Aspect.FOC: 1}),
            areas={Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [], Area.WITHIN_REACH: [], Area.PLAYER_AREA: []}
        )
        eng = GameEngine(state)

        listeners = wwm.enters_hand(eng)
        listener = listeners[0]

        self.assertIsNotNone(listener, "Walk With Me should create a listener")
        # Type assertion for tests - we know it's not None after the check
        assert listener is not None
        self.assertEqual(listener.event_type, EventType.TEST_SUCCEED, "Should listen for test success")
        self.assertEqual(listener.timing_type, TimingType.AFTER, "Should trigger after test")
        self.assertEqual(listener.test_type, "Traverse", "Should only trigger on Traverse tests")
        self.assertEqual(listener.source_card_id, wwm.id, "Should have card's ID")
        self.assertIsNotNone(listener.effect_fn, "Should have an effect function")


class CalypsaRangerMentorTests(unittest.TestCase):
    """Tests for Calypsa, Ranger Mentor from Valley set"""

    def test_calypsa_mountain_effect_adds_progress(self):
        """Test that Calypsa's Mountain effect adds 1 progress to chosen path card"""
        from ebr.cards import CalypsaRangerMentor
        calypsa = CalypsaRangerMentor()

        # Add another being/feature to give choices
        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Ranger",
            hand=[],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [calypsa],
                Area.PLAYER_AREA: [],
            }
        )

        # Chooser picks the feature
        def pick_feature(_engine: GameEngine, choices: list[Card]) -> Card:
            return next(c for c in choices if c.id == "test-feature")

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)


        eng = GameEngine(state,
                        card_chooser=pick_feature)

        # Perform a test to trigger Mountain challenge
        dummy_action = Action(
            id="dummy",
            name="Dummy Test",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify feature got 1 progress from Calypsa's Mountain effect
        self.assertEqual(feature.progress, 1, "Feature should have 1 progress from Calypsa's Mountain effect")

    def test_calypsa_mountain_effect_can_target_self(self):
        """Test that Calypsa can add progress to herself"""
        from ebr.cards import CalypsaRangerMentor
        calypsa = CalypsaRangerMentor()

        ranger = RangerState(
            name="Ranger",
            hand=[],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [calypsa],  # Only Calypsa in play
                Area.PLAYER_AREA: [],
            }
        )

        # Default chooser picks first (only) option
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Perform a test to trigger Mountain challenge
        dummy_action = Action(
            id="dummy",
            name="Dummy Test",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify Calypsa got 1 progress
        self.assertEqual(calypsa.progress, 1, "Calypsa should be able to add progress to herself")

    def test_calypsa_crest_effect_harms_from_predator(self):
        """Test that Calypsa's Crest effect uses harm_from_predator (same as Sitka Doe)"""
        from ebr.cards import CalypsaRangerMentor, ProwlingWolhund
        calypsa = CalypsaRangerMentor()
        wolhund = ProwlingWolhund()

        ranger = RangerState(
            name="Ranger",
            hand=[],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [wolhund],
                Area.WITHIN_REACH: [calypsa],
                Area.PLAYER_AREA: [],
            }
        )

        # Draw CREST symbol to trigger crest effect
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        # Verify initial state
        self.assertFalse(wolhund.exhausted, "Wolhund should start active")
        self.assertEqual(calypsa.harm, 0, "Calypsa should start with 0 harm")

        # Perform a test to trigger Crest challenge
        dummy_action = Action(
            id="dummy",
            name="Dummy Test",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify wolhund exhausted and Calypsa took harm equal to wolhund's presence (2)
        self.assertTrue(wolhund.exhausted, "Wolhund should be exhausted after Crest effect")
        self.assertEqual(calypsa.harm, 2, "Calypsa should have 2 harm from Wolhund's presence")

    def test_calypsa_crest_effect_no_predators(self):
        """Test that Calypsa's Crest effect does nothing when no predators are in play"""
        from ebr.cards import CalypsaRangerMentor
        calypsa = CalypsaRangerMentor()

        ranger = RangerState(
            name="Ranger",
            hand=[],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [calypsa],
                Area.PLAYER_AREA: [],
            }
        )

        # Draw CREST symbol
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        # Perform a test to trigger Crest challenge
        dummy_action = Action(
            id="dummy",
            name="Dummy Test",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify Calypsa took no harm
        self.assertEqual(calypsa.harm, 0, "Calypsa should have no harm when no predators present")


class KeywordTests(unittest.TestCase):
    def test_friendly_keyword_prevents_interaction_fatigue(self):
        """Test that cards with Friendly keyword don't cause interaction fatigue"""
        from ebr.cards import CalypsaRangerMentor, SitkaDoe

        calypsa = CalypsaRangerMentor()
        doe = SitkaDoe()

        # Calypsa should have Friendly keyword
        self.assertIn(Keyword.FRIENDLY, calypsa.keywords, "Calypsa should have Friendly keyword")

        ranger = RangerState(
            name="Ranger",
            hand=[Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1})],
            deck=[Card(id=f"deck{i}", title=f"Deck {i}") for i in range(10)],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [doe],  # Target
                Area.WITHIN_REACH: [calypsa],  # Friendly card between ranger and target
                Area.PLAYER_AREA: [],
            }
        )

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state)

        # Perform a test on the doe (Calypsa is between ranger and doe)
        spook_action = Action(
            id="spook",
            name="Spook Doe",
            aspect=Aspect.SPI,
            approach=Approach.CONFLICT,
            target_provider=lambda _s: [doe],
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        initial_deck_size = len(ranger.deck)
        eng.initiate_test(spook_action, state, doe.id)

        # Verify no fatigue occurred (Calypsa is Friendly)
        self.assertEqual(len(ranger.deck), initial_deck_size,
                        "Deck size should not change - Friendly cards don't cause fatigue")
        self.assertEqual(len(ranger.fatigue_stack), 0,
                        "Fatigue pile should be empty - Friendly cards don't cause fatigue")

    def test_obstacle_keyword_blocks_targeting(self):
        """Test that Obstacle keyword prevents targeting cards beyond it"""
        from ebr.cards import OvergrownThicket, SitkaDoe, ProwlingWolhund

        thicket = OvergrownThicket()
        doe = SitkaDoe()
        wolhund = ProwlingWolhund()

        # Thicket should have Obstacle keyword
        self.assertIn(Keyword.OBSTACLE, thicket.keywords, "Overgrown Thicket should have Obstacle keyword")

        state = GameState(
            ranger=RangerState(
                name="Ranger",
                hand=[],
                aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
            ),
            areas={
                Area.SURROUNDINGS: [wolhund],  # Beyond the obstacle
                Area.ALONG_THE_WAY: [doe],  # Beyond the obstacle
                Area.WITHIN_REACH: [thicket],  # Obstacle here
                Area.PLAYER_AREA: [],
            }
        )

        eng = GameEngine(state)

        # Create an action that targets all path cards (beings and features)
        target_all_path = Action(
            id="test",
            name="Target All Path Cards",
            aspect=Aspect.SPI,
            approach=Approach.CONFLICT,
            target_provider=lambda s: s.path_cards_in_play(),
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        # Get valid targets - should be filtered by obstacle
        valid_targets = eng.get_valid_targets(target_all_path)

        # Should only be able to target thicket (at obstacle), not doe or wolhund (beyond it)
        self.assertEqual(len(valid_targets), 1, "Should only have 1 valid target due to Obstacle")
        self.assertIn(thicket, valid_targets, "Thicket (at Obstacle zone) should be targetable")
        self.assertNotIn(doe, valid_targets, "Doe (beyond Obstacle) should not be targetable")
        self.assertNotIn(wolhund, valid_targets, "Wolhund (beyond Obstacle) should not be targetable")

    def test_exhausted_obstacle_does_not_block(self):
        """Test that exhausted Obstacles don't block targeting"""
        from ebr.cards import OvergrownThicket, SitkaDoe

        thicket = OvergrownThicket()
        thicket.exhausted = True  # Exhausted obstacle
        doe = SitkaDoe()

        state = GameState(
            ranger=RangerState(
                name="Ranger",
                hand=[],
                aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
            ),
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [doe],  # Beyond the exhausted obstacle
                Area.WITHIN_REACH: [thicket],  # Exhausted Obstacle
                Area.PLAYER_AREA: [],
            }
        )

        eng = GameEngine(state)

        target_all_path = Action(
            id="test",
            name="Target All Path Cards",
            aspect=Aspect.SPI,
            approach=Approach.CONFLICT,
            target_provider=lambda s: s.path_cards_in_play(),
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

        valid_targets = eng.get_valid_targets(target_all_path)

        # Both should be targetable since obstacle is exhausted
        self.assertEqual(len(valid_targets), 2, "Both path cards should be targetable when Obstacle is exhausted")
        self.assertIn(thicket, valid_targets)
        self.assertIn(doe, valid_targets)


class _SunEffectCard(Card):
    """Test helper: card with a SUN challenge handler that tracks call count."""

    def __post_init__(self):
        super().__post_init__()
        self.call_count = 0
        self._move_to: Area | None = None

    def get_challenge_handlers(self):
        return {ChallengeIcon.SUN: self._sun_effect}

    def _sun_effect(self, engine):
        self.call_count += 1
        if self._move_to is not None:
            for area_cards in engine.state.areas.values():
                if self in area_cards:
                    area_cards.remove(self)
                    break
            engine.state.areas[self._move_to].append(self)
        return True


class ChallengeResolutionTests(unittest.TestCase):
    """Tests for Step 5 challenge effect ordering, retrigger guards, and the no-effects message."""

    def _make_engine(self, areas: dict[Area, list]) -> GameEngine:
        ranger = RangerState(
            name="Ranger", hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1},
        )
        state = GameState(ranger=ranger, areas=areas)
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        return GameEngine(state)

    def _dummy_action(self) -> Action:
        return Action(
            id="dummy", name="dummy",
            aspect=Aspect.AWA, approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )

    # --- Retrigger guard (and → or on already_resolved_ids check) ---

    def test_card_moving_to_later_area_does_not_retrigger(self):
        """A card that resolves in SURROUNDINGS and moves itself to WITHIN_REACH
        must not resolve again when the loop reaches WITHIN_REACH."""
        card = _SunEffectCard(id="mover", title="Mover")
        card._move_to = Area.WITHIN_REACH

        eng = self._make_engine(areas={
            Area.SURROUNDINGS: [card],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng.perform_test(self._dummy_action(), CommitDecision(energy=1, hand_indices=[]), target_id=None)

        self.assertEqual(card.call_count, 1, "Handler should fire once, not again after moving to a later area")
        self.assertIn(card, eng.state.areas[Area.WITHIN_REACH], "Card should end up in WITHIN_REACH")

    # --- order_decider invocation (len > 1 boundary) ---

    def test_order_decider_called_for_two_resolvable_cards_in_same_area(self):
        """When two cards have resolvable effects in the same area, order_decider must be invoked."""
        card_a = _SunEffectCard(id="a", title="A")
        card_b = _SunEffectCard(id="b", title="B")

        eng = self._make_engine(areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [card_a, card_b],
            Area.PLAYER_AREA: [],
        })

        order_calls: list[list] = []
        original_decider = eng.order_decider
        def tracking_decider(engine, cards, prompt):
            order_calls.append(list(cards))
            return original_decider(engine, cards, prompt)
        eng.order_decider = tracking_decider

        eng.perform_test(self._dummy_action(), CommitDecision(energy=1, hand_indices=[]), target_id=None)

        self.assertEqual(len(order_calls), 1, "order_decider should be called once for the area")
        self.assertEqual(len(order_calls[0]), 2, "order_decider should receive both cards")

    def test_order_decider_not_called_for_single_resolvable_card(self):
        """When only one card has a resolvable effect in an area, order_decider must NOT be invoked."""
        card = _SunEffectCard(id="solo", title="Solo")

        eng = self._make_engine(areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [card],
            Area.PLAYER_AREA: [],
        })

        order_calls: list = []
        eng.order_decider = lambda engine, cards, prompt: (order_calls.append(1), cards)[1]

        eng.perform_test(self._dummy_action(), CommitDecision(energy=1, hand_indices=[]), target_id=None)

        self.assertEqual(len(order_calls), 0, "order_decider should not be called for a single card")
        self.assertEqual(card.call_count, 1, "The single card's effect should still resolve")

    # --- zero_challenge_effects_resolved flag ---

    def test_no_effects_message_when_no_handlers_exist(self):
        """'No challenge effects resolved.' should appear when no cards have handlers for the drawn icon."""
        plain_card = Card(id="plain", title="Plain Card")

        eng = self._make_engine(areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [plain_card],
            Area.PLAYER_AREA: [],
        })
        eng.perform_test(self._dummy_action(), CommitDecision(energy=1, hand_indices=[]), target_id=None)

        messages = [msg.message for msg in eng.get_messages()]
        self.assertIn("No challenge effects resolved.", messages)

    def test_no_effects_message_absent_when_effects_do_resolve(self):
        """'No challenge effects resolved.' must NOT appear when at least one effect resolved."""
        card = _SunEffectCard(id="active", title="Active")

        eng = self._make_engine(areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [card],
            Area.PLAYER_AREA: [],
        })
        eng.perform_test(self._dummy_action(), CommitDecision(energy=1, hand_indices=[]), target_id=None)

        messages = [msg.message for msg in eng.get_messages()]
        self.assertNotIn("No challenge effects resolved.", messages)
        self.assertEqual(card.call_count, 1)


class ChallengeRetriggerPreventionTests(unittest.TestCase):
    """Tests for preventing challenge effects from retriggering when cards move during challenge resolution"""

    def test_challenge_effect_does_not_retrigger_when_card_moves_to_challenge_area(self):
        """Test that a challenge effect doesn't trigger twice when a card moves into a challenge area during resolution"""
        from ebr.cards import SitkaDoe, SitkaBuck

        doe = SitkaDoe()
        buck = SitkaBuck()

        # Initial setup: Doe in Within Reach (challenge area), Buck in Surroundings (not challenge area)
        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [buck],  # Buck starts here (not a challenge area)
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],  # Doe here with Sun effect
                Area.PLAYER_AREA: [],
            }
        )

        # Draw SUN symbol - this should trigger doe's Sun effect which moves buck to Within Reach
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform a test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify buck moved to Within Reach
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 2, "Buck should have moved to Within Reach")
        self.assertIn(buck, state.areas[Area.WITHIN_REACH], "Buck should be in Within Reach")

        # The key check: messages should only show ONE sun effect trigger for the doe
        # Not two (one before buck moved, one after)
        messages = [msg.message for msg in eng.get_messages()]
        sun_triggers = [msg for msg in messages if "Challenge (Sun) on" in msg and "Sitka Doe" in msg]
        self.assertEqual(len(sun_triggers), 1,
                        "Doe's Sun effect should only trigger once, not again after buck moves to Within Reach")

    def test_non_resolvable_effects_dont_execute(self):
        """Test that multiple cards with the same challenge symbol will not execute if the wouldn't resolve"""
        from ebr.cards import SitkaDoe

        doe_a = SitkaDoe()
        doe_b = SitkaDoe()

        # Both does in Within Reach
        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe_a, doe_b],
                Area.PLAYER_AREA: [],
            }
        )

        # Draw SUN symbol - both does have Sun effects
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Perform a test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Each doe should trigger exactly once
        messages = [msg.message for msg in eng.get_messages()]
        sun_triggers = [msg for msg in messages if "Challenge (Sun) on" in msg and "Sitka Doe" in msg]
        self.assertEqual(len(sun_triggers), 0,
                        "Neither doe should trigger their Sun effect")

    def test_challenge_effect_can_trigger_again_on_next_test(self):
        """Test that challenge effects can trigger again on a subsequent test (not permanently blocked)"""
        from ebr.cards import SitkaDoe, SitkaBuck

        doe = SitkaDoe()
        buck_a = SitkaBuck()
        buck_b = SitkaBuck()

        ranger = RangerState(
            name="Ranger",
            hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [buck_a],  # First buck
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )

        # First test with SUN symbol
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Buck A should have moved
        self.assertIn(buck_a, state.areas[Area.WITHIN_REACH], "Buck A should have moved on first test")

        # Clear messages
        eng.clear_messages()

        # Add second buck to Along the Way
        state.areas[Area.ALONG_THE_WAY].append(buck_b)

        # Second test with SUN symbol (new test, so effects should trigger again)
        # The already_resolved_ids list is local to each perform_test call, so it resets automatically
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Buck B should also have moved (doe's Sun effect triggered again)
        self.assertIn(buck_b, state.areas[Area.WITHIN_REACH], "Buck B should have moved on second test")

        # Verify Sun effect triggered on second test
        messages = [msg.message for msg in eng.get_messages()]
        sun_triggers = [msg for msg in messages if "Challenge (Sun) on" in msg and "Sitka Doe" in msg]
        self.assertEqual(len(sun_triggers), 1,
                        "Doe's Sun effect should trigger again on the second test")


class Phase3TravelTests(unittest.TestCase):
    """Tests for phase3_travel: eligibility checks and travel blockers."""

    def _make_engine(self, location: Card, extra_cards: dict[Area, list] | None = None,
                     response_decider=None) -> GameEngine:
        """Build a GameEngine with the given location in SURROUNDINGS."""
        ranger = RangerState(
            name="Ranger", hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1},
        )
        areas = {
            Area.SURROUNDINGS: [location],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        }
        if extra_cards:
            for area, cards in extra_cards.items():
                areas[area].extend(cards)
        state = GameState(ranger=ranger, areas=areas, location=location)
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        return GameEngine(state, response_decider=response_decider)

    def test_insufficient_progress_blocks_travel(self):
        """Location with progress < threshold should not allow travel."""
        location = LoneTreeStation()  # progress_threshold = 3
        location.progress = 2
        eng = self._make_engine(location)
        result = eng.phase3_travel()

        self.assertFalse(result)
        messages = [m.message for m in eng.get_messages()]
        self.assertTrue(any("insufficient" in m.lower() for m in messages))

    def test_sufficient_progress_allows_travel_when_accepted(self):
        """Location with progress >= threshold should offer travel; accepting triggers execute_travel."""
        location = LoneTreeStation()
        location.progress = 3

        # Say yes to "travel?" but no to "camp?"
        eng = self._make_engine(location,
                                response_decider=lambda _e, p: "camp" not in p.lower())
        result = eng.phase3_travel()

        self.assertFalse(result, "Should return False when not camping")
        self.assertNotEqual(eng.state.location.title, "Lone Tree Station",
                            "Location should have changed after travel")

    def test_sufficient_progress_declined_does_not_travel(self):
        """If ranger declines to travel, nothing happens."""
        location = LoneTreeStation()
        location.progress = 3
        eng = self._make_engine(location, response_decider=lambda _e, _p: False)
        result = eng.phase3_travel()

        self.assertFalse(result)
        self.assertEqual(eng.state.location.title, "Lone Tree Station",
                         "Location should remain unchanged when travel declined")

    def test_active_obstacle_blocks_travel(self):
        """A ready Obstacle card should prevent travel even with enough progress."""
        location = LoneTreeStation()
        location.progress = 5  # well above threshold

        thicket = OvergrownThicket()  # has Obstacle keyword → PREVENT_TRAVEL when ready
        eng = self._make_engine(location,
                                extra_cards={Area.WITHIN_REACH: [thicket]})
        result = eng.phase3_travel()

        self.assertFalse(result)
        messages = [m.message for m in eng.get_messages()]
        self.assertTrue(any("cannot travel" in m.lower() for m in messages))

    def test_exhausted_obstacle_does_not_block_travel(self):
        """An exhausted Obstacle should not prevent travel."""
        location = LoneTreeStation()
        location.progress = 3

        thicket = OvergrownThicket()
        thicket.exhausted = True
        eng = self._make_engine(location,
                                extra_cards={Area.WITHIN_REACH: [thicket]},
                                response_decider=lambda _e, p: "camp" not in p.lower())
        result = eng.phase3_travel()

        # Travel should proceed (not blocked)
        self.assertNotEqual(eng.state.location.title, "Lone Tree Station",
                            "Should have traveled despite exhausted obstacle")

    def test_ranger_token_travel_allowed_when_token_on_location(self):
        """Locations with ranger-token clearing allow travel when token is there."""
        location = Card(id="token-loc", title="Token Location",
                        progress_clears_by_ranger_tokens=True)
        eng = self._make_engine(location, response_decider=lambda _e, _p: True)
        eng.state.ranger.ranger_token_location = location.id

        # execute_travel will fail (no real destinations), but we can check the path
        # by mocking execute_travel instead — or just verify the prompt gets called
        prompts: list[str] = []
        def tracking_decider(_e, prompt):
            prompts.append(prompt)
            return False  # decline travel to avoid execute_travel complexity
        eng.response_decider = tracking_decider

        eng.phase3_travel()
        self.assertTrue(any("Ranger Token" in p for p in prompts),
                        "Should offer ranger-token-based travel")

    def test_ranger_token_travel_blocked_when_token_elsewhere(self):
        """Locations with ranger-token clearing block travel when token is on another card."""
        location = Card(id="token-loc", title="Token Location",
                        progress_clears_by_ranger_tokens=True)
        eng = self._make_engine(location)
        eng.state.ranger.ranger_token_location = "some-other-card"

        result = eng.phase3_travel()
        self.assertFalse(result)
        messages = [m.message for m in eng.get_messages()]
        self.assertTrue(any("not yet on the location" in m.lower() for m in messages))


class ExecuteTravelTests(unittest.TestCase):
    """Tests for execute_travel: play area cleanup, destination change, and camping."""

    def _make_travel_engine(self, extra_path_cards: list[Card] | None = None,
                            extra_ranger_cards: dict[Area, list[Card]] | None = None,
                            response_decider=None) -> GameEngine:
        """Build an engine ready for execute_travel with LoneTreeStation as current location."""
        location = LoneTreeStation()
        ranger = RangerState(
            name="Ranger", hand=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1},
        )
        areas: dict[Area, list] = {
            Area.SURROUNDINGS: [location],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        }
        if extra_path_cards:
            areas[Area.WITHIN_REACH].extend(extra_path_cards)
        if extra_ranger_cards:
            for area, cards in extra_ranger_cards.items():
                areas[area].extend(cards)

        state = GameState(ranger=ranger, areas=areas, location=location,
                          path_deck=[Card(id="pd1", title="Deck Card")],
                          path_discard=[Card(id="pd2", title="Discard Card")])
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        return GameEngine(state, response_decider=response_decider)

    def test_non_persistent_path_cards_discarded_during_travel(self):
        """Non-persistent path cards should be removed from play areas during travel."""
        doe = SitkaDoe()
        thicket = OvergrownThicket()
        thicket.exhausted = True  # exhaust so it doesn't block travel via phase3

        eng = self._make_travel_engine(
            extra_path_cards=[doe, thicket],
            response_decider=lambda _e, _p: False,  # decline camping
        )
        eng.execute_travel()

        all_in_play = eng.state.all_cards_in_play()
        self.assertNotIn(doe, all_in_play, "Non-persistent path card should be discarded")
        self.assertNotIn(thicket, all_in_play, "Non-persistent path card should be discarded")

    def test_persistent_path_card_survives_travel(self):
        """Path cards with the Persistent keyword should stay in play after travel."""
        persistent_card = Card(id="persist", title="Persistent Feature",
                               card_types={CardType.PATH},
                               keywords={Keyword.PERSISTENT})

        eng = self._make_travel_engine(
            extra_path_cards=[persistent_card],
            response_decider=lambda _e, _p: False,
        )
        eng.execute_travel()

        all_in_play = eng.state.all_cards_in_play()
        self.assertIn(persistent_card, all_in_play,
                      "Persistent path card should remain in play after travel")

    def test_ranger_cards_in_path_areas_discarded(self):
        """Non-persistent ranger cards in path areas (not PLAYER_AREA) should be discarded."""
        ranger_card = Card(id="rc1", title="Ranger Gear",
                           card_types={CardType.RANGER, CardType.GEAR})

        eng = self._make_travel_engine(
            extra_ranger_cards={Area.ALONG_THE_WAY: [ranger_card]},
            response_decider=lambda _e, _p: False,
        )
        eng.execute_travel()

        all_in_play = eng.state.all_cards_in_play()
        self.assertNotIn(ranger_card, all_in_play,
                         "Ranger card in path area should be discarded during travel")
        self.assertIn(ranger_card, eng.state.ranger.discard,
                      "Ranger card should go to ranger discard pile")

    def test_ranger_cards_in_player_area_not_discarded(self):
        """Ranger cards in PLAYER_AREA should NOT be discarded during travel."""
        player_card = Card(id="pc1", title="Player Gear",
                           card_types={CardType.RANGER, CardType.GEAR})

        eng = self._make_travel_engine(response_decider=lambda _e, _p: False)
        eng.state.areas[Area.PLAYER_AREA].append(player_card)
        eng.execute_travel()

        all_in_play = eng.state.all_cards_in_play()
        self.assertIn(player_card, all_in_play,
                      "Ranger card in PLAYER_AREA should survive travel")

    def test_path_deck_and_discard_cleared(self):
        """Path deck and path discard should be emptied during travel cleanup."""
        eng = self._make_travel_engine(response_decider=lambda _e, _p: False)

        self.assertTrue(len(eng.state.path_deck) > 0, "Precondition: path deck not empty")
        self.assertTrue(len(eng.state.path_discard) > 0, "Precondition: path discard not empty")

        eng.execute_travel()

        # After travel, arrival_setup rebuilds path_deck, so check that OLD cards are gone
        old_ids = {"pd1", "pd2"}
        current_ids = {c.id for c in eng.state.path_deck}
        self.assertTrue(old_ids.isdisjoint(current_ids),
                        "Old path deck/discard contents should be gone after travel")

    def test_location_changes_to_destination(self):
        """After travel, the engine's location should be a different location."""
        eng = self._make_travel_engine(response_decider=lambda _e, _p: False)
        old_title = eng.state.location.title

        eng.execute_travel()

        self.assertNotEqual(eng.state.location.title, old_title,
                            "Location should change after travel")
        self.assertIn(eng.state.location, eng.state.areas[Area.SURROUNDINGS],
                      "New location should be in SURROUNDINGS")

    def test_path_deck_rebuilt_after_travel(self):
        """After travel (without camping), arrival_setup should rebuild the path deck."""
        eng = self._make_travel_engine(response_decider=lambda _e, _p: False)
        eng.execute_travel()

        self.assertTrue(len(eng.state.path_deck) > 0,
                        "Path deck should be rebuilt by arrival_setup after travel")

    def test_camping_ends_day(self):
        """Choosing to camp during travel should raise DayEndException."""
        # response_decider returns True for both "travel?" and "camp?" prompts
        eng = self._make_travel_engine(response_decider=lambda _e, _p: True)

        with self.assertRaises(DayEndException):
            eng.execute_travel()

        messages = [m.message for m in eng.get_messages()]
        self.assertTrue(any("camp" in m.lower() for m in messages))

    def test_not_camping_returns_false(self):
        """Declining to camp should return False and continue to arrival setup."""
        eng = self._make_travel_engine(response_decider=lambda _e, _p: False)

        result = eng.execute_travel()
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
