import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import *
from src.registry import *


def fixed_draw(mod : int, sym: ChallengeIcon):
    return lambda: (mod, sym)


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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))


        # Perform action using the engine API directly
        thicket_test = thicket.get_tests()
        if thicket_test is None:
            raise RuntimeError(f"Failed to fetch thicket test")
        else:
            act = thicket_test[0]
            eng.perform_action(
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Perform action using the engine API directly
        thicket_test = thicket.get_tests()
        if thicket_test is None:
            raise RuntimeError(f"Failed to fetch thicket test")
        else:
            act = thicket_test[0]
            eng.perform_action(
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.CREST))

        tests = provide_common_tests(state)
        act = tests[0]
        eng.perform_action(
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

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
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Feature should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 0, "Feature should be removed from zones")
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

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
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Being should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 0, "Being should be removed from zones")
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

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
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Assert: Feature should still be in zones (not cleared)
        all_cards_in_zones = sum(len(cards) for cards in state.areas.values())
        self.assertEqual(all_cards_in_zones, 1, "Feature should still be in play")
        self.assertEqual(len(state.path_discard), 0, "Nothing should be discarded")
        self.assertEqual(feature.progress, 1, "Feature should have 1 progress")


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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Traverse: FIT + Exploration
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Commit 1 FIT energy + 1 card with Exploration = 2 effort
        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[0]), target_id=feature.id)

        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)
        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)  # Started with 2, spent 1
        self.assertEqual(len(state.ranger.hand), 0)  # Committed card discarded
        self.assertEqual(state.ranger.injury, 0)  # No injury on success

    def test_traverse_failure(self):
        """Test failed Traverse test causes injury"""
        feature = Card(
            title="Test Feature",
            id="test-feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=2,  # Difficulty is 2
            progress_threshold=3
        )
        ranger = RangerState(
            name="Ranger",
            hand=[],  # No cards to commit
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(-1, ChallengeIcon.SUN))  # Negative modifier

        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Commit 1 FIT energy + 0 cards + (-1 modifier) = 0 effort, difficulty 2
        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[]), target_id=feature.id)

        self.assertFalse(outcome.success)
        self.assertEqual(feature.progress, 0)  # No progress on failure
        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)
        self.assertEqual(state.ranger.injury, 1)  # Injury on failure

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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Connect: SPI + Connection
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit 1 SPI energy + 1 card with Connection = 2 effort
        outcome = eng.perform_action(connect, CommitDecision(energy=1, hand_indices=[0]), target_id=being.id)

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
        eng = GameEngine(state, challenge_drawer=fixed_draw(-2, ChallengeIcon.SUN))

        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit 1 SPI + (-2 modifier) = 0 effort (clamped), difficulty 3
        outcome = eng.perform_action(connect, CommitDecision(energy=1, hand_indices=[]), target_id=being.id)

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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Avoid: AWA + Conflict
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        avoid = next(a for a in actions if a.id == "common-avoid")

        # Commit 1 AWA energy + 1 card with Conflict = 2 effort
        outcome = eng.perform_action(avoid, CommitDecision(energy=1, hand_indices=[0]), target_id=being.id)

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
        eng = GameEngine(state, challenge_drawer=fixed_draw(-2, ChallengeIcon.SUN))

        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        avoid = next(a for a in actions if a.id == "common-avoid")

        # Commit 1 AWA + (-2 modifier) = 0 effort, difficulty 3
        outcome = eng.perform_action(avoid, CommitDecision(energy=1, hand_indices=[]), target_id=being.id)

        self.assertFalse(outcome.success)
        self.assertFalse(being.exhausted)  # Being not exhausted on failure
        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(state.ranger.injury, 0)  # Avoid has no failure effect

    def test_sitka_doe_spook_success_moves_to_along_the_way(self):
        """Test that Sitka Doe's Spook test moves it from Within Reach to Along the Way on success"""
        from src.cards import SitkaDoe
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Get the Sitka Doe spook action from registry
        from src.registry import provide_card_tests
        actions = provide_card_tests(state)
        spook = next(a for a in actions if a.verb == "Spook" and "Sitka Doe" in a.name)

        # Perform the spook action with 1 SPI energy + 1 Conflict card = 2 effort, difficulty 1
        outcome = eng.perform_action(spook, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)  # Started with 2, spent 1

        # Verify the doe moved from Within Reach to Along the Way
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 0, "Doe should no longer be in Within Reach")
        self.assertEqual(len(state.areas[Area.ALONG_THE_WAY]), 1, "Doe should now be in Along the Way")
        self.assertEqual(state.areas[Area.ALONG_THE_WAY][0].id, doe.id, "The card in Along the Way should be the doe")

    def test_sitka_doe_spook_failure_does_not_move(self):
        """Test that failing Sitka Doe's Spook test does not move it"""
        from src.cards import SitkaDoe
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(-2, ChallengeIcon.SUN))  # Negative modifier to ensure failure

        # Get the Sitka Doe spook action from registry
        from src.registry import provide_card_tests
        actions = provide_card_tests(state)
        spook = next(a for a in actions if a.verb == "Spook" and "Sitka Doe" in a.name)

        # Perform the spook action with 1 SPI energy + no cards + (-2 modifier) = 0 effort (clamped), difficulty 1
        outcome = eng.perform_action(spook, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify test failed
        self.assertFalse(outcome.success)
        self.assertEqual(state.ranger.energy[Aspect.SPI], 1)  # Started with 2, spent 1

        # Verify the doe stayed in Within Reach
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 1, "Doe should still be in Within Reach")
        self.assertEqual(len(state.areas[Area.ALONG_THE_WAY]), 0, "Nothing should be in Along the Way")
        self.assertEqual(state.areas[Area.WITHIN_REACH][0].id, doe.id, "The card in Within Reach should be the doe")

    def test_sitka_doe_sun_effect_moves_bucks_to_within_reach(self):
        """Test that Sitka Doe's sun challenge effect moves all Sitka Bucks within reach"""
        from src.cards import SitkaDoe, SitkaBuck
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
                Area.ALONG_THE_WAY: [buck_a, buck_b],  # Bucks start here
                Area.WITHIN_REACH: [doe],  # Doe is here
                Area.PLAYER_AREA: [],
            }
        )
        # Draw SUN symbol to trigger sun effect
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Perform any test to trigger challenge resolution
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,
        )
        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

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
        from src.cards import SitkaDoe, ProwlingWolhund
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.MOUNTAIN))

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
        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify wolhund is exhausted and doe took harm equal to wolhund's presence
        self.assertTrue(wolhund.exhausted, "Wolhund should be exhausted")
        self.assertEqual(doe.harm, wolhund.presence, f"Doe should have {wolhund.presence} harm (wolhund's presence)")

    def test_sitka_doe_mountain_effect_no_active_predators(self):
        """Test that Sitka Doe's mountain effect does nothing when no active predators exist"""
        from src.cards import SitkaDoe, ProwlingWolhund
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
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.MOUNTAIN))

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
        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify no harm was dealt (no active predators)
        self.assertEqual(doe.harm, 0, "Doe should still have 0 harm (no active predators)")
        self.assertTrue(wolhund.exhausted, "Wolhund should still be exhausted")


class WalkWithMeTests(unittest.TestCase):
    """Tests for Walk With Me response card"""

    def test_walk_with_me_standard_play(self):
        """Test Walk With Me triggers after successful Traverse, player says yes, and has energy"""
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=pick_first,
                        response_decider=always_yes)

        # Register listener when card enters hand
        listener = wwm.enters_hand(eng)
        self.assertIsNotNone(listener, "Walk With Me should create a listener")
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform Traverse test (3 effort = 1 FIT energy + 2 Exploration icons)
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Add cards with Exploration icons for effort
        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))
        ranger.hand.append(Card(id="e2", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[1, 2]), target_id=feature.id)

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
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        response_decider=always_no)

        # Register listener
        listener = wwm.enters_hand(eng)
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform Traverse test
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

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
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        response_decider=always_yes)

        # Register listener
        listener = wwm.enters_hand(eng)
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform Traverse test
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

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
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        response_decider=always_yes)

        # Register listener
        listener = wwm.enters_hand(eng)
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform Traverse test
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)
        self.assertEqual(feature.progress, 2)

        # Verify Walk With Me was NOT played (no valid targets)
        self.assertIn(wwm, state.ranger.hand, "Walk With Me should still be in hand (no targets)")
        self.assertNotIn(wwm, state.ranger.discard, "Walk With Me should not be discarded")
        self.assertEqual(state.ranger.energy[Aspect.SPI], 2, "SPI should be unchanged (no targets)")

        # Verify listener remains active
        self.assertEqual(len(eng.listeners), 1, "Listener should remain active")

    def test_walk_with_me_only_triggers_on_traverse(self):
        """Test that Walk With Me only triggers on Traverse tests, not Connect tests"""
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        response_decider=always_yes)

        # Register listener
        listener = wwm.enters_hand(eng)
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform CONNECT test (not Traverse!)
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        ranger.hand.append(Card(id="c1", title="Conn+1", approach_icons={Approach.CONNECTION: 1}))

        outcome = eng.perform_action(connect, CommitDecision(energy=1, hand_indices=[1]), target_id=being.id)

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
        from src.cards import WalkWithMe
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=pick_being_b,
                        response_decider=always_yes)

        # Register listener
        listener = wwm.enters_hand(eng)
        if listener:  # Type guard for mypy
            eng.add_listener(listener)

        # Perform Traverse test with 5 effort
        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        # Add 4 exploration icons for total of 5 effort
        for i in range(4):
            ranger.hand.append(Card(id=f"e{i}", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        outcome = eng.perform_action(traverse, CommitDecision(energy=1, hand_indices=[1, 2, 3, 4]), target_id=feature.id)

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
        from src.cards import WalkWithMe
        wwm = WalkWithMe()

        # Create minimal engine for testing
        state = GameState(
            ranger=RangerState(name="Ranger", hand=[], aspects={Aspect.AWA: 1, Aspect.FIT: 1, Aspect.SPI: 1, Aspect.FOC: 1}),
            areas={Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [], Area.WITHIN_REACH: [], Area.PLAYER_AREA: []}
        )
        eng = GameEngine(state)

        listener = wwm.enters_hand(eng)

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
        from src.cards import CalypsaRangerMentor
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

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.MOUNTAIN),
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

        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify feature got 1 progress from Calypsa's Mountain effect
        self.assertEqual(feature.progress, 1, "Feature should have 1 progress from Calypsa's Mountain effect")

    def test_calypsa_mountain_effect_can_target_self(self):
        """Test that Calypsa can add progress to herself"""
        from src.cards import CalypsaRangerMentor
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
        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.MOUNTAIN))

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

        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify Calypsa got 1 progress
        self.assertEqual(calypsa.progress, 1, "Calypsa should be able to add progress to herself")

    def test_calypsa_crest_effect_harms_from_predator(self):
        """Test that Calypsa's Crest effect uses harm_from_predator (same as Sitka Doe)"""
        from src.cards import CalypsaRangerMentor, ProwlingWolhund
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
        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.CREST))

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

        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify wolhund exhausted and Calypsa took harm equal to wolhund's presence (2)
        self.assertTrue(wolhund.exhausted, "Wolhund should be exhausted after Crest effect")
        self.assertEqual(calypsa.harm, 2, "Calypsa should have 2 harm from Wolhund's presence")

    def test_calypsa_crest_effect_no_predators(self):
        """Test that Calypsa's Crest effect does nothing when no predators are in play"""
        from src.cards import CalypsaRangerMentor
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
        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.CREST))

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

        eng.perform_action(dummy_action, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify Calypsa took no harm
        self.assertEqual(calypsa.harm, 0, "Calypsa should have no harm when no predators present")


class KeywordTests(unittest.TestCase):
    def test_friendly_keyword_prevents_interaction_fatigue(self):
        """Test that cards with Friendly keyword don't cause interaction fatigue"""
        from src.cards import CalypsaRangerMentor, SitkaDoe

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

        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

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
        self.assertEqual(len(ranger.fatigue_pile), 0,
                        "Fatigue pile should be empty - Friendly cards don't cause fatigue")

    def test_obstacle_keyword_blocks_targeting(self):
        """Test that Obstacle keyword prevents targeting cards beyond it"""
        from src.cards import OvergrownThicket, SitkaDoe, ProwlingWolhund

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
        from src.cards import OvergrownThicket, SitkaDoe

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


if __name__ == '__main__':
    unittest.main()
