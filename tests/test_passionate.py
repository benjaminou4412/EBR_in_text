#type:ignore
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import Passionate
from tests.test_utils import MockChallengeDeck, make_challenge_card


def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    """Helper to stack the challenge deck with a single predetermined card."""
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


class PassionateTests(unittest.TestCase):
    """Tests for Passionate attribute card with ephemeral commit listener"""

    def test_passionate_not_playable(self):
        """Test that Passionate cannot be played (it's an attribute)"""
        passionate = Passionate()

        # Attributes should not provide a play action
        play_action = passionate.get_play_action()
        self.assertIsNone(play_action)

    def test_passionate_has_connection_icon(self):
        """Test that Passionate has 1 Connection approach icon"""
        passionate = Passionate()

        self.assertEqual(passionate.approach_icons.get(Approach.CONNECTION, 0), 1)

    def test_passionate_commits_successfully(self):
        """Test that Passionate can be committed to a test"""
        passionate = Passionate()

        # Create a being to target
        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Stack deck for guaranteed success
        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        # Decline recovery to test just the commit mechanic
        eng = GameEngine(state, response_decider=lambda _e, _p: False)

        # Create a Connect test action
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit Passionate (1 Connection icon)
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify Passionate was discarded
        self.assertNotIn(passionate, ranger.hand)
        self.assertIn(passionate, ranger.discard)

        # Verify test succeeded
        self.assertTrue(outcome.success)

    def test_passionate_recovery_on_success(self):
        """Test that Passionate can be recovered to hand after successful test"""
        passionate = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Stack deck for guaranteed success
        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        # Custom response decider that says "yes" to recovery
        def say_yes(_eng, _prompt):
            return True

        eng = GameEngine(state, response_decider=say_yes)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit Passionate
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Verify starting state
        self.assertEqual(len(ranger.hand), 1)
        self.assertEqual(len(ranger.discard), 0)
        self.assertEqual(len(ranger.fatigue_stack), 0)
        self.assertEqual(len(ranger.deck), 10)

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)

        # Verify Passionate was recovered to hand
        self.assertIn(passionate, ranger.hand)
        self.assertNotIn(passionate, ranger.discard)

        # Verify 1 fatigue was suffered
        self.assertEqual(len(ranger.fatigue_stack), 1)
        self.assertEqual(len(ranger.deck), 9)

    def test_passionate_can_decline_recovery(self):
        """Test that player can choose not to recover Passionate"""
        passionate = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        # Custom response decider that says "no" to recovery
        def say_no(_eng, _prompt):
            return False

        eng = GameEngine(state, response_decider=say_no)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit Passionate
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)

        # Verify Passionate stayed in discard
        self.assertNotIn(passionate, ranger.hand)
        self.assertIn(passionate, ranger.discard)

        # Verify no fatigue was suffered
        self.assertEqual(len(ranger.fatigue_stack), 0)
        self.assertEqual(len(ranger.deck), 10)

    def test_passionate_no_recovery_on_failure(self):
        """Test that Passionate recovery doesn't trigger on failed test"""
        passionate = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=5,  # High difficulty
            progress_threshold=10
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 1, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Stack deck for guaranteed failure (negative modifier)
        stack_deck(state, Aspect.SPI, -2, ChallengeIcon.MOUNTAIN)

        # Track if response decider was called
        response_called = [False]
        def track_response(_eng, _prompt):
            response_called[0] = True
            return True

        eng = GameEngine(state, response_decider=track_response)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit Passionate
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify test failed
        self.assertFalse(outcome.success)

        # Verify response was NOT called (no recovery on failure)
        self.assertFalse(response_called[0])

        # Verify Passionate stayed in discard
        self.assertNotIn(passionate, ranger.hand)
        self.assertIn(passionate, ranger.discard)

        # Verify no fatigue was suffered
        self.assertEqual(len(ranger.fatigue_stack), 0)

    def test_passionate_listener_cleaned_up_after_test(self):
        """Test that the ephemeral listener is removed after test completes"""
        passionate = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Verify no listeners initially
        initial_listener_count = len(eng.listeners)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit Passionate
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Perform test
        eng.perform_test(connect, decision, being.id)

        # Verify listener was cleaned up after test
        self.assertEqual(len(eng.listeners), initial_listener_count)

    def test_multiple_passionate_cards_independent(self):
        """Test that multiple Passionate cards each get their own listener"""
        passionate1 = Passionate()
        passionate2 = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate1, passionate2],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        # Say yes to both recoveries
        eng = GameEngine(state, response_decider=lambda _e, _p: True)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit both Passionate cards
        decision = CommitDecision(energy=1, hand_indices=[0, 1])

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)

        # Verify both Passionate cards recovered
        self.assertIn(passionate1, ranger.hand)
        self.assertIn(passionate2, ranger.hand)

        # Verify 2 fatigue suffered (one per card)
        self.assertEqual(len(ranger.fatigue_stack), 2)

    def test_passionate_recovery_with_other_committed_cards(self):
        """Test that Passionate recovery works when committed alongside other cards"""
        passionate = Passionate()
        other_card = Card(
            title="Other Card",
            id="other1",
            card_types={CardType.RANGER, CardType.ATTRIBUTE},
            approach_icons={Approach.CONNECTION: 1}
        )

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate, other_card],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state, response_decider=lambda _e, _p: True)

        # Create a Connect test
        from ebr.registry import provide_common_tests
        actions = provide_common_tests(state)
        connect = next(a for a in actions if a.id == "common-connect")

        # Commit both cards
        decision = CommitDecision(energy=1, hand_indices=[0, 1])

        # Perform test
        outcome = eng.perform_test(connect, decision, being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)

        # Verify Passionate recovered
        self.assertIn(passionate, ranger.hand)

        # Verify other card stayed in discard
        self.assertNotIn(other_card, ranger.hand)
        self.assertIn(other_card, ranger.discard)

        # Verify only 1 fatigue (for Passionate)
        self.assertEqual(len(ranger.fatigue_stack), 1)

    def test_passionate_works_across_different_test_types(self):
        """Test that Passionate recovery works for different test types"""
        passionate = Passionate()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            presence=1,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[passionate],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state, response_decider=lambda _e, _p: True)

        # Create a custom test with Connection approach but different verb than "Connect"
        # This proves Passionate's listener triggers for any test type, not just Connect
        custom_test = Action(
            id="test-befriend",
            name="Befriend (SPI + Connection)",
            aspect=Aspect.SPI,
            approach=Approach.CONNECTION,
            verb="Befriend",  # Different verb than "Connect"
            target_provider=lambda s: s.beings_in_play(),
            difficulty_fn=lambda e, c: c.get_current_presence(e) if c else 1,
            on_success=lambda e, eff, c: e.add_message(f"Befriended {c.title}!") if c else None,
            on_fail=lambda e, c: e.add_message("Failed to befriend."),
            source_id="test",
            is_test=True
        )

        # Commit Passionate (1 Connection icon) to this custom test
        decision = CommitDecision(energy=1, hand_indices=[0])

        # Perform test
        outcome = eng.perform_test(custom_test, decision, being.id)

        # Verify test succeeded
        self.assertTrue(outcome.success)

        # Verify Passionate recovered for a non-Connect test
        self.assertIn(passionate, ranger.hand)
        self.assertEqual(len(ranger.fatigue_stack), 1)


if __name__ == '__main__':
    unittest.main()
