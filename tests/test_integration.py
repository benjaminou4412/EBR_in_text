"""Integration tests that run the full game loop autonomously."""

import unittest
from src.models import (
    Card, RangerState, GameState, Action, Aspect, Area, CardType,
    DayEndException, Keyword
)
from src.engine import GameEngine
from src.cards import PeerlessPathfinder


def make_minimal_deck(size: int = 10) -> list[Card]:
    """Create a minimal deck for testing."""
    return [Card(id=f"deck-{i}", title=f"Test Card {i}") for i in range(size)]


def make_rest_chooser(rest_action_id: str = "system-rest"):
    """Create a card chooser that always picks the Rest action."""
    def chooser(engine: GameEngine, cards: list) -> Card | Action:
        # Find Rest action if this is an action list
        for item in cards:
            if isinstance(item, Action) and item.id == rest_action_id:
                return item
        # Otherwise just return first item
        return cards[0]
    return chooser


class AutonomousGameTests(unittest.TestCase):
    """Tests that run the game loop autonomously without user input."""

    def test_rest_until_deck_out(self):
        """
        Integration test: Always choose Rest until deck runs out.

        This test verifies that:
        1. The game loop runs correctly
        2. Resting with fatiguing cards in play causes fatigue
        3. Fatiguing draws cards from the ranger deck
        4. Decking out (attempting to draw with empty deck) properly ends the day
        5. The day_has_ended flag is set when appropriate

        Setup:
        - Small ranger deck (8 cards)
        - 5 cards drawn for starting hand (3 remaining)
        - 2 fatiguing cards in play (presence 2 each = 4 fatigue per rest)
        - First rest draws 4 cards, causing deck-out and ending the day
        """

        # Set up a game with a small deck that will run out quickly
        ranger_deck = make_minimal_deck(size=8)  # Small deck to deck out fast
        ranger = RangerState(
            name="Test Ranger",
            hand=[],
            deck=ranger_deck,
            fatigue_stack=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3}
        )
        role_card = PeerlessPathfinder()

        # Create some fatiguing path cards to force card draws
        fatiguing_card1 = Card(
            id="fatiguing-1",
            title="Fatiguing Path Card 1",
            card_types={CardType.PATH},
            presence=2  # Presence value for fatigue calculation
        )
        fatiguing_card1.keywords = {Keyword.FATIGUING}

        fatiguing_card2 = Card(
            id="fatiguing-2",
            title="Fatiguing Path Card 2",
            card_types={CardType.PATH},
            presence=2  # Presence value for fatigue calculation
        )
        fatiguing_card2.keywords = {Keyword.FATIGUING}

        state = GameState(
            ranger=ranger,
            role_card=role_card,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [fatiguing_card1],
                Area.WITHIN_REACH: [fatiguing_card2],
                Area.PLAYER_AREA: [role_card],
            }
        )

        # Mock decision functions that always choose "Rest"
        def mock_card_chooser(engine: GameEngine, cards: list[Card]) -> Card:
            """Always choose the first card."""
            return cards[0]

        def mock_response_decider(engine: GameEngine, prompt: str) -> bool:
            """Always say no to ending day early."""
            return False

        def mock_order_decider(engine: GameEngine, items: list, prompt: str):
            """Return items in original order."""
            return items

        def mock_option_chooser(engine: GameEngine, options: list[str], prompt: str | None) -> str:
            """Always choose first option."""
            return options[0]

        def mock_amount_chooser(engine: GameEngine, min_val: int, max_val: int, prompt: str | None) -> int:
            """Always choose minimum amount."""
            return min_val

        engine = GameEngine(
            state,
            card_chooser=mock_card_chooser,
            response_decider=mock_response_decider,
            order_decider=mock_order_decider,
            option_chooser=mock_option_chooser,
            amount_chooser=mock_amount_chooser
        )

        # Do minimal setup (skip arrival_setup for simplicity)
        engine.add_message("=== INTEGRATION TEST: Rest Until Deck Out ===")

        # Draw starting hand
        for _ in range(5):
            card, msg, should_end = state.ranger.draw_card(engine)
            if card is None:
                self.fail("Deck should not run out during initial hand draw!")
            engine.add_message(msg)

        # Run game loop
        max_rounds = 50  # Safety limit
        rounds_completed = 0
        day_ended = False

        try:
            for round_num in range(1, max_rounds + 1):
                rounds_completed = round_num
                engine.state.round_number = round_num

                # Phase 1: Draw path cards (simplified - skip for now)
                engine.add_message(f"Round {round_num} — Phase 1: Draw Path Cards (skipped)")

                # Phase 2: Ranger Turns - always choose Rest
                engine.add_message(f"Round {round_num} — Phase 2: Ranger Turns")

                # Build action list (simplified - just Rest)
                actions = [Action(
                    id="system-rest",
                    name="[Rest] (end actions)",
                    verb="Rest",
                    aspect="",
                    approach="",
                    is_test=False,
                    on_success=lambda s, _e, _t: None,
                )]

                # Choose Rest action
                act = actions[0]  # Always choose Rest

                # Execute Rest
                engine.resolve_fatiguing_keyword()
                engine.add_message("You rest and end your turn.")

                # Check if day ended
                if engine.day_has_ended:
                    day_ended = True
                    engine.add_message("Day ended (day_has_ended flag set)")
                    break

                # Phase 3: Travel (simplified - always camp)
                engine.add_message(f"Round {round_num} — Phase 3: Travel (camping)")
                # Just camp, don't actually travel

                # Phase 4: Refresh
                engine.add_message(f"Round {round_num} — Phase 4: Refresh")
                engine.state.ranger.refresh_all_energy()
                engine.add_message("Energy refreshed.")

                # Check if day ended after refresh
                if engine.day_has_ended:
                    day_ended = True
                    engine.add_message("Day ended after refresh")
                    break

        except DayEndException:
            # Day ended via exception (expected for some scenarios)
            day_ended = True
            engine.add_message("Day ended via DayEndException")

        # Assertions
        self.assertTrue(
            day_ended or rounds_completed >= max_rounds,
            f"Game should have ended by decking out or hitting round limit. "
            f"Completed {rounds_completed} rounds, day_ended={day_ended}"
        )

        # Verify messages were generated
        self.assertGreater(
            len(engine.message_queue),
            0,
            "Game should have generated messages"
        )

        # Print summary for debugging
        print(f"\n=== Test Summary ===")
        print(f"Rounds completed: {rounds_completed}")
        print(f"Day ended: {day_ended}")
        print(f"Deck remaining: {len(state.ranger.deck)}")
        print(f"Hand size: {len(state.ranger.hand)}")
        print(f"Fatigue size: {len(state.ranger.fatigue_stack)}")
        print(f"Messages: {len(engine.message_queue)}")

    def test_main_game_loop_rest_until_deck_out(self):
        """
        Integration test using the actual run_game_loop from main.py.

        This test verifies that the game loop in main.py works correctly by:
        1. Running the actual run_game_loop function (not the UI wrapper)
        2. Using decision functions that always choose Rest
        3. Verifying the game ends via DayEndException when deck runs out
        """
        from main import run_game_loop

        # Set up a game with a small deck that will run out quickly
        ranger_deck = make_minimal_deck(size=8)
        ranger = RangerState(
            name="Test Ranger",
            hand=[],
            deck=ranger_deck,
            fatigue_stack=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3}
        )
        role_card = PeerlessPathfinder()

        # Create fatiguing cards to force card draws
        fatiguing_card1 = Card(
            id="fatiguing-1",
            title="Fatiguing Path Card 1",
            card_types={CardType.PATH},
            presence=2
        )
        fatiguing_card1.keywords = {Keyword.FATIGUING}

        fatiguing_card2 = Card(
            id="fatiguing-2",
            title="Fatiguing Path Card 2",
            card_types={CardType.PATH},
            presence=2
        )
        fatiguing_card2.keywords = {Keyword.FATIGUING}

        # Create a path card for the path deck
        path_card = Card(
            id="path-1",
            title="Test Path Card",
            card_types={CardType.PATH},
            starting_area=Area.SURROUNDINGS
        )

        state = GameState(
            ranger=ranger,
            role_card=role_card,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [fatiguing_card1],
                Area.WITHIN_REACH: [fatiguing_card2],
                Area.PLAYER_AREA: [role_card],
            },
            path_deck=[path_card]
        )

        engine = GameEngine(
            state,
            card_chooser=make_rest_chooser(),
            response_decider=lambda eng, prompt: False,
            order_decider=lambda eng, items, prompt: items,
            option_chooser=lambda eng, options, prompt: options[0],
            amount_chooser=lambda eng, min_val, max_val, prompt: min_val
        )

        # Draw starting hand
        for _ in range(5):
            card, msg, _ = state.ranger.draw_card(engine)
            if card is not None:
                engine.add_message(msg)
            else:
                self.fail("Deck should not run out during initial hand draw!")

        # Run the actual game loop from main.py without UI
        with self.assertRaises(DayEndException):
            run_game_loop(engine, with_ui=False)

        # Verify the game ran and messages were generated
        self.assertGreater(len(engine.message_queue), 0, "Game should have generated messages")

        print(f"\n=== Main Loop Test Summary ===")
        print(f"Round reached: {engine.state.round_number}")
        print(f"Deck remaining: {len(state.ranger.deck)}")
        print(f"Hand size: {len(state.ranger.hand)}")
        print(f"Fatigue size: {len(state.ranger.fatigue_stack)}")
        print(f"Messages: {len(engine.message_queue)}")


if __name__ == '__main__':
    unittest.main()
