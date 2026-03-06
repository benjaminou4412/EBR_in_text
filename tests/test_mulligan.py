"""Tests for draw_starting_hand_and_mulligan."""

import unittest
from ebr.models import (
    GameState, RangerState, Card, Aspect, Area,
)
from ebr.engine import GameEngine
from tests.test_utils import MockChallengeDeck, make_challenge_card


def _make_state(deck_size: int = 12) -> GameState:
    """Create a minimal GameState with a deck of generic cards."""
    ranger = RangerState(
        name="Ranger",
        hand=[],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1},
    )
    ranger.deck = [
        Card(id=f"card-{i}", title=f"Card {i}") for i in range(deck_size)
    ]
    return GameState(
        ranger=ranger,
        areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        },
    )


class DrawStartingHandTests(unittest.TestCase):
    def test_draws_six_cards(self):
        state = _make_state(12)
        eng = GameEngine(state)
        eng.draw_starting_hand_and_mulligan()
        self.assertEqual(len(state.ranger.hand), 6)
        self.assertEqual(len(state.ranger.deck), 6)

    def test_hand_contains_top_six_cards(self):
        state = _make_state(12)
        expected_ids = [c.id for c in state.ranger.deck[:6]]
        eng = GameEngine(state)
        eng.draw_starting_hand_and_mulligan()
        drawn_ids = [c.id for c in state.ranger.hand]
        self.assertEqual(drawn_ids, expected_ids)

    def test_raises_if_deck_too_small(self):
        state = _make_state(4)
        eng = GameEngine(state)
        with self.assertRaises(RuntimeError):
            eng.draw_starting_hand_and_mulligan()


class MulliganDeclineTests(unittest.TestCase):
    def test_decline_mulligan_keeps_hand(self):
        """Default response_decider returns True, so we override to decline."""
        state = _make_state(12)
        eng = GameEngine(
            state,
            response_decider=lambda _e, _p: False,
        )
        eng.draw_starting_hand_and_mulligan()
        self.assertEqual(len(state.ranger.hand), 6)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("Keeping starting hand" in m for m in messages))


class MulliganAcceptTests(unittest.TestCase):
    def test_mulligan_no_cards_selected(self):
        """Accept mulligan but select nothing — hand unchanged."""
        state = _make_state(12)
        eng = GameEngine(
            state,
            response_decider=lambda _e, _p: True,
            cards_chooser=lambda _e, _cards, _p: [],
        )
        eng.draw_starting_hand_and_mulligan()
        self.assertEqual(len(state.ranger.hand), 6)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("No cards set aside" in m for m in messages))

    def test_mulligan_set_aside_two(self):
        """Set aside 2 cards, draw 2 replacements, shuffle 2 back."""
        state = _make_state(12)
        original_hand_ids = [c.id for c in state.ranger.deck[:6]]

        def choose_first_two(_eng, cards, _prompt):
            return cards[:2]

        eng = GameEngine(
            state,
            response_decider=lambda _e, _p: True,
            cards_chooser=choose_first_two,
        )
        eng.draw_starting_hand_and_mulligan()

        # Still 6 cards in hand (2 removed, 2 drawn)
        self.assertEqual(len(state.ranger.hand), 6)
        # The 2 set-aside cards should no longer be in hand
        hand_ids = {c.id for c in state.ranger.hand}
        self.assertNotIn(original_hand_ids[0], hand_ids)
        self.assertNotIn(original_hand_ids[1], hand_ids)
        # Deck should have 6 remaining (12 - 6 drawn - 2 replacement drawn + 2 shuffled back)
        self.assertEqual(len(state.ranger.deck), 6)

    def test_mulligan_set_aside_all(self):
        """Set aside entire hand — draw 6 new, shuffle 6 back."""
        state = _make_state(18)

        def choose_all(_eng, cards, _prompt):
            return list(cards)

        eng = GameEngine(
            state,
            response_decider=lambda _e, _p: True,
            cards_chooser=choose_all,
        )
        eng.draw_starting_hand_and_mulligan()

        self.assertEqual(len(state.ranger.hand), 6)
        # 18 - 6 initial - 6 replacement + 6 shuffled back = 12
        self.assertEqual(len(state.ranger.deck), 12)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("Shuffled 6 card(s) back" in m for m in messages))

    def test_mulligan_deck_runs_out_during_redraw(self):
        """If deck runs out during replacement draws, partial redraw is fine."""
        state = _make_state(8)  # 8 cards: draw 6, only 2 left for replacements

        def choose_all(_eng, cards, _prompt):
            return list(cards)

        eng = GameEngine(
            state,
            response_decider=lambda _e, _p: True,
            cards_chooser=choose_all,
        )
        eng.draw_starting_hand_and_mulligan()

        # Drew 6 initially, set aside all 6, only 2 left to redraw
        self.assertEqual(len(state.ranger.hand), 2)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("Deck ran out during mulligan" in m for m in messages))


class DefaultCardsChooserTests(unittest.TestCase):
    def test_default_returns_empty(self):
        """Default cards_chooser returns [] (no mulligan selection in tests)."""
        state = _make_state(12)
        eng = GameEngine(state)
        result = eng.cards_chooser(eng, state.ranger.deck[:3], "test")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
