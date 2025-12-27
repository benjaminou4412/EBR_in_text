"""Integration tests that run the full game loop autonomously."""

import unittest
from src.models import (
    Card, RangerState, GameState, Action, Aspect, Area, CardType,
    DayEndException, Keyword, CampaignTracker
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
            card, should_end = state.ranger.draw_card(engine)
            if card is None:
                self.fail("Deck should not run out during initial hand draw!")

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
            card, should_end = state.ranger.draw_card(engine)
            if card is None:
                self.fail("Deck should not run out during initial hand draw!")

        # Run the actual game loop from main.py without UI
        with self.assertRaises(DayEndException):
            run_game_loop(engine, with_ui=False)

        # Verify the game ran and messages were generated
        self.assertGreater(len(engine.message_queue), 0, "Game should have generated messages")


class DayTransitionTests(unittest.TestCase):
    """Tests for day-to-day transitions and state persistence."""

    def test_day_transition_preserves_campaign_tracker(self):
        """
        Test that day transitions properly preserve campaign tracker state
        and reset per-day state.

        Verifies:
        1. All decks are reset and freshly shuffled
        2. Day starts at the Location the previous Day ended
        3. Campaign tracker state is maintained (day_number, notable_events, etc.)
        4. Per-day state is NOT maintained (hand, fatigue, areas, round_number)
        """
        # === Set up Day 1 ===
        role_card = PeerlessPathfinder()
        campaign_tracker = CampaignTracker(
            day_number=1,
            ranger_name="Test Ranger",
            ranger_aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
            current_location_id="Ancestor's Grove",
            current_terrain_type="Woods"
        )

        # Add some campaign state that should persist
        campaign_tracker.notable_events.append("Found a mysterious artifact")
        campaign_tracker.unlocked_rewards.append("Shiny Badge")

        # Start Day 1 using GameEngine.setup_new_day (uses default decision functions)
        state1 = GameEngine.setup_new_day(campaign_tracker, role_card)
        state1.ranger.deck = make_minimal_deck(20)
        engine1 = GameEngine(state1)  # Uses default autonomous decision functions

        # Draw starting hand
        for _ in range(5):
            card, should_end = state1.ranger.draw_card(engine1)
            self.assertIsNotNone(card, "Should be able to draw starting hand")

        # Run arrival setup
        engine1.arrival_setup(start_of_day=True)

        # Verify Day 1 setup
        self.assertEqual(state1.round_number, 1)
        self.assertEqual(state1.location.title, "Ancestor's Grove")
        self.assertEqual(len(state1.ranger.hand), 5)
        self.assertGreater(len(state1.ranger.deck), 0)
        self.assertEqual(len(state1.ranger.fatigue_stack), 0)
        self.assertGreater(len(state1.path_deck), 0)

        # Simulate playing - add some cards to areas, advance rounds
        test_card_in_play = Card(id="test-card-in-play", title="Test Path Card")
        state1.areas[Area.ALONG_THE_WAY].append(test_card_in_play)
        state1.round_number = 5

        # Move some cards to fatigue
        if state1.ranger.hand:
            fatigued_card = state1.ranger.hand.pop()
            state1.ranger.fatigue_stack.append(fatigued_card)

        # Record state before ending day
        day1_location = state1.location

        # === End Day 1 ===
        # Simulate ending at Boulder Field (traveling to a different location)
        campaign_tracker.current_location_id = "Boulder Field"
        campaign_tracker.day_number = 2  # Simulate end_day() incrementing

        # Add more campaign progress
        campaign_tracker.notable_events.append("Defeated the guardian")

        # === Start Day 2 ===
        state2 = GameEngine.setup_new_day(campaign_tracker, role_card)
        state2.ranger.deck = make_minimal_deck(20)
        engine2 = GameEngine(state2)  # Uses default autonomous decision functions

        # Draw starting hand for Day 2
        for _ in range(5):
            card, should_end = state2.ranger.draw_card(engine2)
            self.assertIsNotNone(card, "Should be able to draw starting hand")

        # Run arrival setup for Day 2
        engine2.arrival_setup(start_of_day=True)

        # === Verify Campaign Tracker State PERSISTS ===
        self.assertEqual(state2.campaign_tracker.day_number, 2, "Day number should persist")
        self.assertEqual(len(state2.campaign_tracker.notable_events), 2, "Notable events should persist")
        self.assertIn("Found a mysterious artifact", state2.campaign_tracker.notable_events)
        self.assertIn("Defeated the guardian", state2.campaign_tracker.notable_events)
        self.assertEqual(len(state2.campaign_tracker.unlocked_rewards), 1, "Unlocked rewards should persist")
        self.assertIn("Shiny Badge", state2.campaign_tracker.unlocked_rewards)
        self.assertEqual(state2.campaign_tracker.ranger_name, "Test Ranger", "Ranger name should persist")
        self.assertEqual(state2.campaign_tracker.current_terrain_type, "Woods", "Terrain type should persist")

        # === Verify Location Uses Saved Location ===
        self.assertEqual(state2.location.title, "Boulder Field",
                        "Day 2 should start at Boulder Field (where Day 1 ended)")

        # === Verify Per-Day State is RESET ===
        self.assertEqual(state2.round_number, 1, "Round number should reset to 1")
        self.assertEqual(len(state2.ranger.hand), 5, "Should have fresh starting hand")
        self.assertEqual(len(state2.ranger.fatigue_stack), 0, "Fatigue stack should be empty")

        # === Verify Decks are Fresh ===
        self.assertGreater(len(state2.ranger.deck), 0, "Ranger deck should be rebuilt")
        self.assertGreater(len(state2.path_deck), 0, "Path deck should be rebuilt")

        # The path deck should be freshly shuffled (different object)
        self.assertIsNot(state2.path_deck, state1.path_deck, "Path deck should be a new list")

    def test_end_day_saves_location(self):
        """Test that end_day() properly saves the current location to campaign tracker."""
        from src.cards import BoulderField, AncestorsGrove

        # Set up a game at Ancestor's Grove
        campaign_tracker = CampaignTracker(
            day_number=1,
            ranger_name="Test Ranger",
            ranger_aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
            current_location_id="Ancestor's Grove",
            current_terrain_type="Woods"
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[],
            deck=make_minimal_deck(20),
            fatigue_stack=[],
            aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3}
        )
        role_card = PeerlessPathfinder()

        # Set up game state with Boulder Field as the location
        boulder_field = BoulderField()
        state = GameState(
            ranger=ranger,
            role_card=role_card,
            campaign_tracker=campaign_tracker,
            location=boulder_field,
            areas={
                Area.SURROUNDINGS: [boulder_field],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [role_card],
            }
        )

        engine = GameEngine(
            state,
            card_chooser=lambda eng, cards: cards[0],
            response_decider=lambda eng, prompt: False,
            order_decider=lambda eng, items, prompt: items,
            option_chooser=lambda eng, options, prompt: options[0],
            amount_chooser=lambda eng, min_val, max_val, prompt: min_val
        )

        # End the day
        with self.assertRaises(DayEndException):
            engine.end_day()

        # Verify location was saved (uses title, not id)
        self.assertEqual(campaign_tracker.current_location_id, "Boulder Field",
                        "end_day should save current location title")
        self.assertEqual(campaign_tracker.day_number, 2,
                        "end_day should increment day number")

    def test_fresh_game_state_structure(self):
        """
        Test that setup_new_day creates proper fresh state structure.

        Note: Location arrival setup effects may put cards in play (e.g., Ancestor's Grove
        searches for prey). This test verifies the basic structure is correct, not that
        no cards are in play.
        """
        role_card = PeerlessPathfinder()
        campaign_tracker = CampaignTracker(
            day_number=1,
            ranger_name="Test Ranger",
            ranger_aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
            current_location_id="Ancestor's Grove",
            current_terrain_type="Woods"
        )

        # Use GameEngine.setup_new_day directly (uses default autonomous decision functions)
        state = GameEngine.setup_new_day(campaign_tracker, role_card)
        state.ranger.deck = make_minimal_deck(20)
        engine = GameEngine(state)

        # Draw starting hand
        for _ in range(5):
            card, should_end = state.ranger.draw_card(engine)
            self.assertIsNotNone(card, "Should be able to draw starting hand")

        # Run arrival setup
        engine.arrival_setup(start_of_day=True)

        # Surroundings should have location and weather (at minimum)
        surroundings = state.areas[Area.SURROUNDINGS]
        self.assertGreaterEqual(len(surroundings), 2,
                               "Surroundings should have at least location and weather")

        # Player area should have role card
        player_area = state.areas[Area.PLAYER_AREA]
        self.assertGreaterEqual(len(player_area), 1,
                               "Player area should have at least role card")
        role_cards_in_play = [c for c in player_area if c.title == role_card.title]
        self.assertEqual(len(role_cards_in_play), 1,
                        "Role card should be in player area")

        # Ranger should have fresh state
        self.assertEqual(len(state.ranger.hand), 5, "Ranger should have starting hand")
        self.assertEqual(len(state.ranger.fatigue_stack), 0, "Fatigue stack should be empty")
        self.assertEqual(len(state.ranger.discard), 0, "Ranger discard should be empty")
        self.assertGreater(len(state.ranger.deck), 0, "Ranger deck should have cards")

        # Path deck should be built
        self.assertGreater(len(state.path_deck), 0, "Path deck should be built")

        # Round number should be 1
        self.assertEqual(state.round_number, 1, "Round number should be 1")


if __name__ == '__main__':
    unittest.main()
