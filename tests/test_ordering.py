#type:ignore
import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import *
from src.registry import provide_common_tests
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(10)],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
    )




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

class ChallengeEffectOrderingTests(unittest.TestCase):
    """Tests for ordering multiple challenge effects in the same area"""

    def test_multiple_challenge_effects_use_order_decider(self):
        """Test that multiple challenge effects in same area are passed to order_decider"""
        from src.cards import SitkaDoe

        doe_a = SitkaDoe()
        doe_b = SitkaDoe()
        doe_c = SitkaDoe()
        buck = SitkaBuck()
        buck.exhausted = True

        ranger = make_test_ranger()
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [buck],
                Area.WITHIN_REACH: [doe_a, doe_b, doe_c],  # All in same area
                Area.PLAYER_AREA: [],
            }
        )

        # Track order_decider calls
        order_decider_calls = []

        def tracking_order_decider(_engine: GameEngine, items: list, prompt: str) -> list:
            order_decider_calls.append((items, prompt))
            # Return reversed order
            return list(reversed(items))

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        order_decider=tracking_order_decider)

        # Perform a test to trigger SUN challenge
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify order_decider was called with the three does
        self.assertEqual(len(order_decider_calls), 1, "order_decider should be called once")
        items, prompt = order_decider_calls[0]
        self.assertEqual(len(items), 3, "Should be ordering 3 cards")
        self.assertIn("Within Reach", prompt, "Prompt should mention the area")
        self.assertIn("SUN", prompt, "Prompt should mention the challenge symbol")

    def test_single_challenge_effect_skips_order_decider(self):
        """Test that a single challenge effect doesn't call order_decider"""
        from src.cards import SitkaDoe

        doe = SitkaDoe()

        ranger = make_test_ranger()
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],  # Only one card
                Area.PLAYER_AREA: [],
            }
        )

        order_decider_called = False

        def tracking_order_decider(_engine: GameEngine, items: list, _prompt: str) -> list:
            nonlocal order_decider_called
            order_decider_called = True
            return items

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        order_decider=tracking_order_decider)

        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Verify order_decider was NOT called (only 1 effect)
        self.assertFalse(order_decider_called, "order_decider should not be called for single effect")

    def test_challenge_effects_resolve_in_reversed_order(self):
        """Test that challenge effects actually resolve in the order specified by order_decider"""
        from src.cards import SitkaDoe, SitkaBuck

        doe = SitkaDoe()
        buck_a = SitkaBuck()
        buck_b = SitkaBuck()
        buck_c = SitkaBuck()

        ranger = make_test_ranger()
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [buck_a, buck_b, buck_c],  #bucks that will harm each other
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )

        # Order decider that reverses the buck order
        def reverse_order(_engine: GameEngine, items: list, _prompt: str) -> list:
            return list(reversed(items))

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        order_decider=reverse_order)

        # Trigger SUN - bucks harm each other, then all move within reach
        # since order is reversed and card_chooser defaults to index-0, the sequence is:
        # buck c exhausts itself; buck c and buck a harm each other
        # buck b exhausts itself; buck b and buck a harm each other; buck a clears
        # buck a is cleared so its challenge effect does not resolve
        # sitka doe moves all of them within reach
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # All bucks should have moved
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 3, "2 surviving bucks + doe should be Within Reach")
        self.assertNotIn(buck_a, state.areas[Area.WITHIN_REACH]) #buck a should be cleared
        self.assertIn(buck_b, state.areas[Area.WITHIN_REACH])
        self.assertIn(buck_c, state.areas[Area.WITHIN_REACH])

    def test_challenge_effects_resolve_in_specified_order(self):
        """Test that challenge effects actually resolve in the order specified by order_decider"""
        from src.cards import SitkaDoe, SitkaBuck

        doe = SitkaDoe()
        buck_a = SitkaBuck()
        buck_b = SitkaBuck()
        buck_c = SitkaBuck()

        ranger = make_test_ranger()
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [buck_a, buck_b, buck_c],  #bucks that will harm each other
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )

        # Order decider that reverses the buck order
        def maintain_order(_engine: GameEngine, items: list, _prompt: str) -> list:
            return list(items)

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        order_decider=maintain_order)

        # Trigger SUN - bucks harm each other, then all move within reach
        # since order is not reversed and card_chooser defaults to index-0, the sequence is:
        # buck a exhausts itself; buck a and buck b harm each other
        # buck b exhausts itself; buck b and buck c harm each other; buck b clears
        # buck b is cleared so its challenge effect does not resolve
        # sitka doe moves all of them within reach
        dummy_action = Action(
            id="dummy",
            name="dummy",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda _e, _eff, _t: None,
        )
        eng.perform_test(dummy_action, CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # All bucks should have moved
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 3, "2 surviving bucks + doe should be Within Reach")
        self.assertIn(buck_a, state.areas[Area.WITHIN_REACH]) #buck a should be cleared
        self.assertNotIn(buck_b, state.areas[Area.WITHIN_REACH])
        self.assertIn(buck_c, state.areas[Area.WITHIN_REACH])

class EventListenerOrderingTests(unittest.TestCase):
    """Tests for ordering multiple event listeners that trigger simultaneously"""

    def test_multiple_listeners_use_order_decider(self):
        """Test that multiple listeners triggering simultaneously are passed to order_decider"""
        from src.cards import WalkWithMe

        # Create two Walk With Me cards to create two listeners
        wwm1 = WalkWithMe()
        wwm2 = WalkWithMe()

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
            hand=[wwm1, wwm2],
            deck=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 1}
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

        order_decider_calls = []

        def tracking_order_decider(_engine: GameEngine, items: list, prompt: str) -> list:
            order_decider_calls.append((items, prompt))
            return items  # Keep original order

        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_yes,
                        order_decider=tracking_order_decider)


        # Perform Traverse test to trigger both Walk With Me listeners
        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.extend([
            Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}),
            Card(id="e2", title="E+1", approach_icons={Approach.EXPLORATION: 1})
        ])

        eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[2, 3]), target_id=feature.id)

        # Verify order_decider was called with the two listeners
        self.assertEqual(len(order_decider_calls), 1, "order_decider should be called once for listeners")
        items, prompt = order_decider_calls[0]
        self.assertEqual(len(items), 2, "Should be ordering 2 listeners")

    def test_single_listener_skips_order_decider(self):
        """Test that a single listener doesn't call order_decider"""
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
            aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 1}
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

        order_decider_called = False

        def tracking_order_decider(_engine: GameEngine, items: list, _prompt: str) -> list:
            nonlocal order_decider_called
            order_decider_called = True
            return items

        def always_yes(_engine: GameEngine, _prompt: str) -> bool:
            return True

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=always_yes,
                        order_decider=tracking_order_decider)

        

        actions = provide_common_tests(state)
        traverse = next(a for a in actions if a.id == "common-traverse")

        ranger.hand.append(Card(id="e1", title="E+1", approach_icons={Approach.EXPLORATION: 1}))

        eng.perform_test(traverse, CommitDecision(energy=1, hand_indices=[1]), target_id=feature.id)

        # Verify order_decider was NOT called (only 1 listener)
        self.assertFalse(order_decider_called, "order_decider should not be called for single listener")


class RememberTestTests(unittest.TestCase):
    """Tests for the Remember common test (scouts ranger deck)"""

    def test_remember_scouts_cards_from_ranger_deck(self):
        """Test that Remember test scouts cards from ranger deck"""
        ranger = make_test_ranger()
        # Give ranger a specific deck so we can track what gets scouted
        ranger.deck = [
            Card(id="card1", title="Card 1"),
            Card(id="card2", title="Card 2"),
            Card(id="card3", title="Card 3"),
            Card(id="card4", title="Card 4"),
        ]
        initial_deck_size = len(ranger.deck)

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )

        # Mock order_decider and response_decider to simulate player choices
        # Player will put all cards on top in reversed order
        def mock_order_decider(_engine: GameEngine, items: list, _prompt: str) -> list:
            return list(reversed(items))

        # Track which cards were asked about
        response_prompts = []

        def mock_response_decider(_engine: GameEngine, prompt: str) -> bool:
            response_prompts.append(prompt)
            # Say yes (top) for all cards
            return True

        stack_deck(state, Aspect.FOC, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=mock_response_decider,
                        order_decider=mock_order_decider)

        # Get Remember test
        actions = provide_common_tests(state)
        remember = next(a for a in actions if a.id == "common-remember")

        # Perform Remember test, committing 2 effort to scout 2 cards with fixed challenge draw of 0
        ranger.hand.append(Card(id="reason1", title="Reason+1", approach_icons={Approach.REASON: 1}))
        outcome = eng.perform_test(remember, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify test succeeded
        self.assertTrue(outcome.success, "Remember test should succeed")

        # Verify deck still has 4 cards (scouted cards were put back)
        self.assertEqual(len(ranger.deck), initial_deck_size-1, "Deck should have 1 fewer card because Remember auto-draws 1")

        # Verify we were asked about 3 cards (scouting count)
        self.assertEqual(len(response_prompts), 2, "Should be asked about 2 cards")

    def test_remember_handles_deck_smaller_than_scout_count(self):
        """Test that Remember handles scouting when deck has fewer cards than scout count"""
        ranger = make_test_ranger()
        # Only 2 cards in deck, but Remember scouts 3
        ranger.deck = [
            Card(id="card1", title="Card 1"),
            Card(id="card2", title="Card 2"),
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )

        response_prompts = []

        def mock_response_decider(_engine: GameEngine, prompt: str) -> bool:
            response_prompts.append(prompt)
            return True

        def mock_order_decider(_engine: GameEngine, items: list, _prompt: str) -> list:
            return items

        stack_deck(state, Aspect.FOC, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
                        response_decider=mock_response_decider,
                        order_decider=mock_order_decider)

        actions = provide_common_tests(state)
        remember = next(a for a in actions if a.id == "common-remember")

        ranger.hand.append(Card(id="reason1", title="Reason+1", approach_icons={Approach.REASON: 1}))
        outcome = eng.perform_test(remember, CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Verify test succeeded
        self.assertTrue(outcome.success, "Remember test should succeed")

        # Should only scout the 2 available cards, not 3
        self.assertEqual(len(response_prompts), 2, "Should only be asked about 2 cards (all available)")
        self.assertEqual(len(ranger.deck), 1, "Deck should have 1 card left after remember auto-draw")


class ScoutCardsTests(unittest.TestCase):
    """Tests for the generic scout_cards method"""

    def test_scout_cards_basic_functionality(self):
        """Test basic scouting with top and bottom placement"""
        ranger = make_test_ranger()
        deck = [
            Card(id="card1", title="Card 1"),
            Card(id="card2", title="Card 2"),
            Card(id="card3", title="Card 3"),
            Card(id="card4", title="Card 4"),
            Card(id="card5", title="Card 5"),
        ]

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
        })

        # Mock: Card 1 -> bottom, Card 2 -> top, Card 3 -> top
        responses = [False, True, True]  # First is bottom, next two are top
        response_idx = [0]

        def mock_response_decider(_engine: GameEngine, _prompt: str) -> bool:
            result = responses[response_idx[0]]
            response_idx[0] += 1
            return result

        # Mock: Reverse the order of top pile (Card 3, Card 2)
        def mock_order_decider(_engine: GameEngine, items: list, prompt: str) -> list:
            if "TOP" in prompt:
                return list(reversed(items))
            return items

        eng = GameEngine(state,
                        response_decider=mock_response_decider,
                        order_decider=mock_order_decider)

        # Scout 3 cards from the deck
        eng.scout_cards(deck, 3)

        # Expected result:
        # - Card 3 on top (reversed from [Card 2, Card 3])
        # - Card 2 next
        # - Card 4 (not scouted)
        # - Card 5 (not scouted)
        # - Card 1 on bottom (bottom pile)

        self.assertEqual(len(deck), 5, "Deck should still have 5 cards")
        self.assertEqual(deck[0].id, "card3", "Card 3 should be on top (reversed top pile)")
        self.assertEqual(deck[1].id, "card2", "Card 2 should be second")
        self.assertEqual(deck[2].id, "card4", "Card 4 should be third (untouched)")
        self.assertEqual(deck[3].id, "card5", "Card 5 should be fourth (untouched)")
        self.assertEqual(deck[4].id, "card1", "Card 1 should be on bottom")

    def test_scout_cards_all_to_top(self):
        """Test scouting where all cards go to top"""
        deck = [
            Card(id="card1", title="Card 1"),
            Card(id="card2", title="Card 2"),
            Card(id="card3", title="Card 3"),
        ]

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
        })

        # All cards go to top
        def all_top(_engine: GameEngine, _prompt: str) -> bool:
            return True

        # Keep original order
        def keep_order(_engine: GameEngine, items: list, _prompt: str) -> list:
            return items

        eng = GameEngine(state,
                        response_decider=all_top,
                        order_decider=keep_order)

        eng.scout_cards(deck, 2)

        # Card 1 and Card 2 were scouted, both go to top in order [1, 2]
        self.assertEqual(len(deck), 3)
        self.assertEqual(deck[0].id, "card1", "Card 1 should be on top (last in reversed insertion)")
        self.assertEqual(deck[1].id, "card2", "Card 2 should be second")
        self.assertEqual(deck[2].id, "card3", "Card 3 should remain at bottom")

    def test_scout_cards_all_to_bottom(self):
        """Test scouting where all cards go to bottom"""
        deck = [
            Card(id="card1", title="Card 1"),
            Card(id="card2", title="Card 2"),
            Card(id="card3", title="Card 3"),
        ]

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
        })

        # All cards go to bottom
        def all_bottom(_engine: GameEngine, _prompt: str) -> bool:
            return False

        def keep_order(_engine: GameEngine, items: list, _prompt: str) -> list:
            return items

        eng = GameEngine(state,
                        response_decider=all_bottom,
                        order_decider=keep_order)

        eng.scout_cards(deck, 2)

        # Card 1 and Card 2 scouted, both go to bottom in order
        # Result: [Card 3 (not scouted), Card 1, Card 2]
        self.assertEqual(len(deck), 3)
        self.assertEqual(deck[0].id, "card3", "Card 3 should be on top (not scouted)")
        self.assertEqual(deck[1].id, "card1", "Card 1 should be second (bottom pile)")
        self.assertEqual(deck[2].id, "card2", "Card 2 should be last (bottom pile)")

    def test_scout_cards_zero_count(self):
        """Test that scouting 0 cards does nothing"""
        deck = [Card(id="card1", title="Card 1")]
        original_deck = deck.copy()

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
        })

        eng = GameEngine(state)
        eng.scout_cards(deck, 0)

        self.assertEqual(deck, original_deck, "Deck should be unchanged when scouting 0 cards")

    def test_scout_cards_empty_deck(self):
        """Test that scouting from empty deck does nothing"""
        deck = []

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
        })

        eng = GameEngine(state)
        eng.scout_cards(deck, 3)

        self.assertEqual(len(deck), 0, "Empty deck should remain empty")

    def test_scout_cards_works_with_path_deck(self):
        """Test that scout_cards works with path_deck (not just ranger deck)"""
        ranger = make_test_ranger()
        path_deck = [
            Card(id="path1", title="Path 1", card_types={CardType.PATH}),
            Card(id="path2", title="Path 2", card_types={CardType.PATH}),
            Card(id="path3", title="Path 3", card_types={CardType.PATH}),
        ]

        state = GameState(
            ranger=ranger,
            path_deck=path_deck,
            areas={
                Area.SURROUNDINGS: [], Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [], Area.PLAYER_AREA: []
            }
        )

        def all_top(_engine: GameEngine, _prompt: str) -> bool:
            return True

        def keep_order(_engine: GameEngine, items: list, _prompt: str) -> list:
            return items

        eng = GameEngine(state,
                        response_decider=all_top,
                        order_decider=keep_order)

        # Scout from path_deck
        eng.scout_cards(state.path_deck, 2)

        # Path deck should still have 3 cards
        self.assertEqual(len(state.path_deck), 3, "Path deck should still have 3 cards")


if __name__ == '__main__':
    unittest.main()
