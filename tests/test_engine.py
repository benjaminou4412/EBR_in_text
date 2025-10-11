import unittest
from src.models import *
from src.engine import GameEngine


def fixed_draw(mod : int, sym: Symbol):
    return lambda: (mod, sym)


class EngineTests(unittest.TestCase):
    def test_thicket_progress_and_energy(self):
        # Setup state: one feature (thicket), ranger with two exploration cards in hand
        thicket = Card(
            title = "Overgrown Thicket",
            id="woods-011-overgrown-thicket",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=2
        )
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Create two pseudo cards with Exploration+1 each
        ranger.hand = [
            Card(id="c1", title="E+1", approach_icons={Approach.EXPLORATION: 1}),
            Card(id="c2", title="E+1", approach_icons={Approach.EXPLORATION: 1})
        ]
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))


        # Perform action using the engine API directly
        from src.models import Action
        act = Action(
            id="t1",
            name="thicket",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
        eng.perform_action(
            act,
            decision=CommitDecision(energy=1, hand_indices=[0, 1]),
            target_id=None)

        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(thicket.progress, 3)
        self.assertEqual(len(state.ranger.hand), 0)
    
    def test_single_energy(self):
        # Setup state: one feature (thicket), ranger with no cards in hand
        thicket = Card(
            title="Overgrown Thicket",
            id="woods-011-overgrown-thicket",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=1,
            progress_threshold=2
        )
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action using the engine API directly
        act = Action(
            id="t1",
            name="thicket",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
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
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.hand = [Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1})]
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [feat],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.CREST))

        act = Action(
            id="t2",
            name="traverse",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: max(1, feat.presence if feat.presence is not None else 0),
            on_success=lambda s, eff, _t: feat.add_progress(eff),
            on_fail=lambda s, _t: setattr(state.ranger, "injury", state.ranger.injury + 1),
        )
        eng.perform_action(
            act,
            decision=CommitDecision(energy=1, hand_indices=[0]),
            target_id=None)

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
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.hand = [Card(id="c1", title="E+1", approach_icons={Approach.EXPLORATION: 1})]
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [feature],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action that adds exactly enough progress to clear (1 energy + 1 icon = 2 effort)
        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: feature.add_progress(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Feature should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.zones.values())
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
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 5, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Add a card with +1 Conflict icon so we get 2 total effort (1 energy + 1 icon)
        ranger.hand = [Card(id="c1", title="Conflict+1", approach_icons={Approach.CONFLICT: 1})]
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [being],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action that adds exactly enough harm to clear (1 energy + 1 icon = 2 effort = 2 harm)
        act = Action(
            id="test-harm",
            name="test harm",
            aspect=Aspect.AWA,
            approach=Approach.CONFLICT,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: being.add_harm(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Being should be removed from zones and moved to path_discard
        all_cards_in_zones = sum(len(cards) for cards in state.zones.values())
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
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [feature],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Add progress that doesn't reach threshold (only 1 effort)
        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: feature.add_progress(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Assert: Feature should still be in zones (not cleared)
        all_cards_in_zones = sum(len(cards) for cards in state.zones.values())
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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [feature],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [feature],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(-1, Symbol.SUN))  # Negative modifier

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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [being],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [being],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(-2, Symbol.SUN))

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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [being],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

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
            energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
        )
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [being],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(-2, Symbol.SUN))

        from src.registry import provide_common_tests
        actions = provide_common_tests(state)
        avoid = next(a for a in actions if a.id == "common-avoid")

        # Commit 1 AWA + (-2 modifier) = 0 effort, difficulty 3
        outcome = eng.perform_action(avoid, CommitDecision(energy=1, hand_indices=[]), target_id=being.id)

        self.assertFalse(outcome.success)
        self.assertFalse(being.exhausted)  # Being not exhausted on failure
        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(state.ranger.injury, 0)  # Avoid has no failure effect


if __name__ == '__main__':
    unittest.main()
