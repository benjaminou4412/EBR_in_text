#type: ignore
"""Tests for the save/load system."""

import unittest
import tempfile
import os
import json
from pathlib import Path

from src.models import (
    Card, RangerState, GameState, CampaignTracker, ChallengeDeck,
    Aspect, Area, CardType, Mission, Keyword
)
from src.engine import GameEngine
from src.save_load import (
    save_game, load_game, serialize_card, serialize_game_state,
    instantiate_card, get_card_class, SAVE_VERSION
)
from src.cards import (
    BiscuitDelivery, BiscuitBasket, PeerlessPathfinder, SitkaDoe,
    HyPimpotChef, LoneTreeStation, APerfectDay
)


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        aspects={
            Aspect.AWA: 2,
            Aspect.FIT: 2,
            Aspect.SPI: 2,
            Aspect.FOC: 2
        }
    )


def make_test_state() -> GameState:
    """Create a minimal test game state"""
    role = PeerlessPathfinder()
    location = LoneTreeStation()
    weather = APerfectDay()

    ranger = make_test_ranger()

    state = GameState(
        ranger=ranger,
        role_card=role,
        location=location,
        weather=weather,
        campaign_tracker=CampaignTracker(day_number=1)
    )

    # Add location to surroundings
    state.areas[Area.SURROUNDINGS].append(location)
    state.areas[Area.SURROUNDINGS].append(weather)

    return state


class CardSerializationTests(unittest.TestCase):
    """Tests for serializing and deserializing individual cards."""

    def test_serialize_basic_card(self):
        """Test serializing a basic card preserves class and ID."""
        card = SitkaDoe()
        card_data = serialize_card(card)

        self.assertEqual(card_data.card_class, "SitkaDoe")
        self.assertEqual(card_data.id, card.id)
        self.assertFalse(card_data.exhausted)

    def test_serialize_card_with_mutable_state(self):
        """Test that mutable state is properly serialized."""
        card = SitkaDoe()
        card.exhausted = True
        card.progress = 3
        card.harm = 2
        card.unique_tokens["test"] = 5

        card_data = serialize_card(card)

        self.assertTrue(card_data.exhausted)
        self.assertEqual(card_data.progress, 3)
        self.assertEqual(card_data.harm, 2)
        self.assertEqual(card_data.unique_tokens["test"], 5)

    def test_serialize_double_sided_card(self):
        """Test that double-sided cards include backside class."""
        card = BiscuitDelivery()
        card_data = serialize_card(card)

        self.assertEqual(card_data.card_class, "BiscuitDelivery")
        self.assertEqual(card_data.backside_class, "BiscuitBasket")

    def test_instantiate_basic_card(self):
        """Test instantiating a card from serialized data."""
        original = SitkaDoe()
        original.exhausted = True
        original.progress = 5

        card_data = serialize_card(original)
        card_dict = {
            'card_class': card_data.card_class,
            'id': card_data.id,
            'exhausted': card_data.exhausted,
            'progress': card_data.progress,
            'harm': card_data.harm,
            'unique_tokens': card_data.unique_tokens,
            'modifiers': [],
            'attached_to_id': card_data.attached_to_id,
            'attached_card_ids': card_data.attached_card_ids,
        }

        restored = instantiate_card(card_dict)

        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.title, "Sitka Doe")
        self.assertTrue(restored.exhausted)
        self.assertEqual(restored.progress, 5)

    def test_instantiate_double_sided_card(self):
        """Test instantiating a double-sided card restores backside link."""
        original = BiscuitDelivery()

        card_data = serialize_card(original)
        card_dict = {
            'card_class': card_data.card_class,
            'id': card_data.id,
            'exhausted': card_data.exhausted,
            'progress': card_data.progress,
            'harm': card_data.harm,
            'unique_tokens': card_data.unique_tokens,
            'modifiers': [],
            'attached_to_id': None,
            'attached_card_ids': [],
            'backside_class': card_data.backside_class,
        }

        restored = instantiate_card(card_dict)

        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.title, "Biscuit Delivery")
        self.assertIsNotNone(restored.backside)
        self.assertEqual(restored.backside.title, "Biscuit Basket")
        # Verify mutual linking
        self.assertEqual(restored.backside.backside, restored)

    def test_card_id_preserved(self):
        """Test that card ID is preserved exactly through serialization."""
        original = SitkaDoe()
        original_id = original.id

        card_data = serialize_card(original)
        card_dict = {
            'card_class': 'SitkaDoe',
            'id': original_id,
            'exhausted': False,
            'progress': 0,
            'harm': 0,
            'unique_tokens': {},
            'modifiers': [],
            'attached_to_id': None,
            'attached_card_ids': [],
        }

        restored = instantiate_card(card_dict)

        self.assertEqual(restored.id, original_id)


class CardClassRegistryTests(unittest.TestCase):
    """Tests for the card class registry."""

    def test_get_known_card_class(self):
        """Test looking up known card classes."""
        self.assertEqual(get_card_class("SitkaDoe"), SitkaDoe)
        self.assertEqual(get_card_class("BiscuitDelivery"), BiscuitDelivery)
        self.assertEqual(get_card_class("PeerlessPathfinder"), PeerlessPathfinder)

    def test_get_base_card_class(self):
        """Test looking up base Card class."""
        self.assertEqual(get_card_class("Card"), Card)

    def test_get_unknown_card_class_raises(self):
        """Test that unknown class names raise ValueError."""
        with self.assertRaises(ValueError):
            get_card_class("NonexistentCard")


class SaveLoadRoundTripTests(unittest.TestCase):
    """Tests for complete save/load round trips."""

    def setUp(self):
        """Create a temporary directory for test saves."""
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = os.path.join(self.temp_dir, "test_save.json")

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.save_path):
            os.remove(self.save_path)
        os.rmdir(self.temp_dir)

    def test_basic_save_load(self):
        """Test basic save and load preserves state."""
        state = make_test_state()
        engine = GameEngine(state)

        save_game(engine, self.save_path)

        # Verify file was created
        self.assertTrue(os.path.exists(self.save_path))

        # Load and verify
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.ranger.name, "Test Ranger")
        self.assertEqual(loaded_engine.state.round_number, 1)

    def test_save_file_is_valid_json(self):
        """Test that save file is valid JSON."""
        state = make_test_state()
        engine = GameEngine(state)

        save_game(engine, self.save_path)

        with open(self.save_path, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['version'], SAVE_VERSION)
        self.assertIn('ranger', data)
        self.assertIn('areas', data)

    def test_ranger_state_preserved(self):
        """Test that ranger state is fully preserved."""
        state = make_test_state()
        state.ranger.injury = 2
        state.ranger.energy[Aspect.AWA] = 1  # Spend some energy
        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.ranger.injury, 2)
        self.assertEqual(loaded_engine.state.ranger.energy[Aspect.AWA], 1)

    def test_campaign_tracker_preserved(self):
        """Test that campaign tracker is preserved."""
        state = make_test_state()
        state.campaign_tracker.day_number = 5
        state.campaign_tracker.notable_events.append("Test Event")
        state.campaign_tracker.active_missions.append(Mission("Test Mission"))
        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.campaign_tracker.day_number, 5)
        self.assertIn("Test Event", loaded_engine.state.campaign_tracker.notable_events)
        mission_names = [m.name for m in loaded_engine.state.campaign_tracker.active_missions]
        self.assertIn("Test Mission", mission_names)

    def test_cards_in_areas_preserved(self):
        """Test that cards in play areas are preserved."""
        state = make_test_state()

        # Add a card to an area
        doe = SitkaDoe()
        doe.progress = 3
        state.areas[Area.ALONG_THE_WAY].append(doe)

        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        # Find the doe in the loaded state
        along_the_way = loaded_engine.state.areas[Area.ALONG_THE_WAY]
        doe_cards = [c for c in along_the_way if c.title == "Sitka Doe"]

        self.assertEqual(len(doe_cards), 1)
        self.assertEqual(doe_cards[0].progress, 3)
        self.assertEqual(doe_cards[0].id, doe.id)

    def test_challenge_deck_preserved(self):
        """Test that challenge deck state is preserved."""
        state = make_test_state()
        engine = GameEngine(state)

        # Draw a challenge card to modify deck state
        # Note: Some cards trigger reshuffle, so we check the state AFTER drawing
        engine.state.challenge_deck.draw_challenge_card(engine)

        # Capture state after draw (accounts for potential reshuffle)
        deck_size_after_draw = len(engine.state.challenge_deck.deck)
        discard_size_after_draw = len(engine.state.challenge_deck.discard)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        # Deck and discard sizes should match what we saved
        self.assertEqual(
            len(loaded_engine.state.challenge_deck.deck),
            deck_size_after_draw
        )
        self.assertEqual(
            len(loaded_engine.state.challenge_deck.discard),
            discard_size_after_draw
        )

    def test_round_number_preserved(self):
        """Test that round number is preserved."""
        state = make_test_state()
        state.round_number = 5
        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.round_number, 5)

    def test_ranger_deck_and_hand_preserved(self):
        """Test that ranger deck, hand, and discard are preserved."""
        state = make_test_state()

        # Add cards to ranger's deck and hand
        deck_card = Card(title="Deck Card", id="deck-card-1")
        deck_card.card_types.add(CardType.RANGER)
        hand_card = Card(title="Hand Card", id="hand-card-1")
        hand_card.card_types.add(CardType.RANGER)
        discard_card = Card(title="Discard Card", id="discard-card-1")
        discard_card.card_types.add(CardType.RANGER)

        state.ranger.deck.append(deck_card)
        state.ranger.hand.append(hand_card)
        state.ranger.discard.append(discard_card)

        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        # Check deck
        deck_ids = [c.id for c in loaded_engine.state.ranger.deck]
        self.assertIn("deck-card-1", deck_ids)

        # Check hand
        hand_ids = [c.id for c in loaded_engine.state.ranger.hand]
        self.assertIn("hand-card-1", hand_ids)

        # Check discard
        discard_ids = [c.id for c in loaded_engine.state.ranger.discard]
        self.assertIn("discard-card-1", discard_ids)


class ReconstructSilentTests(unittest.TestCase):
    """Tests for the silent reconstruction method."""

    def test_reconstruct_no_messages(self):
        """Test that reconstruct doesn't add messages."""
        state = make_test_state()
        engine = GameEngine(state, skip_reconstruct=True)

        # Clear any existing messages
        engine.message_queue.clear()

        # Run reconstruction
        engine.reconstruct()

        # Should have no messages
        self.assertEqual(len(engine.message_queue), 0)

    def test_reconstruct_registers_abilities(self):
        """Test that reconstruct properly registers constant abilities."""
        state = make_test_state()

        # Add a card with constant abilities
        doe = SitkaDoe()
        doe.keywords.add(Keyword.OBSTACLE)
        state.areas[Area.ALONG_THE_WAY].append(doe)

        engine = GameEngine(state, skip_reconstruct=True)
        engine.reconstruct()

        # Should have registered the OBSTACLE ability
        self.assertGreater(len(engine.constant_abilities), 0)


class SpecialCardTests(unittest.TestCase):
    """Tests for special card types in save/load."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = os.path.join(self.temp_dir, "test_save.json")

    def tearDown(self):
        if os.path.exists(self.save_path):
            os.remove(self.save_path)
        os.rmdir(self.temp_dir)

    def test_double_sided_card_preserved(self):
        """Test that double-sided cards are properly preserved."""
        state = make_test_state()

        # Add BiscuitDelivery to an area
        delivery = BiscuitDelivery()
        state.areas[Area.SURROUNDINGS].append(delivery)

        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        # Find the delivery card
        surroundings = loaded_engine.state.areas[Area.SURROUNDINGS]
        delivery_cards = [c for c in surroundings if c.title == "Biscuit Delivery"]

        self.assertEqual(len(delivery_cards), 1)
        restored = delivery_cards[0]

        # Verify backside is properly linked
        self.assertIsNotNone(restored.backside)
        self.assertEqual(restored.backside.title, "Biscuit Basket")
        self.assertEqual(restored.backside.backside, restored)

    def test_card_with_unique_tokens_preserved(self):
        """Test that unique tokens are preserved."""
        state = make_test_state()

        # Create a BiscuitBasket with specific token count
        basket = BiscuitBasket()
        basket.unique_tokens["biscuit"] = 3
        state.areas[Area.PLAYER_AREA].append(basket)

        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        # Find the basket
        player_area = loaded_engine.state.areas[Area.PLAYER_AREA]
        basket_cards = [c for c in player_area if c.title == "Biscuit Basket"]

        self.assertEqual(len(basket_cards), 1)
        self.assertEqual(basket_cards[0].unique_tokens["biscuit"], 3)


class RangerTokenLocationTests(unittest.TestCase):
    """Tests for ranger token location preservation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = os.path.join(self.temp_dir, "test_save.json")

    def tearDown(self):
        if os.path.exists(self.save_path):
            os.remove(self.save_path)
        os.rmdir(self.temp_dir)

    def test_ranger_token_on_role_preserved(self):
        """Test that ranger token location on role is preserved."""
        state = make_test_state()
        engine = GameEngine(state)

        # Token starts on role card
        role_id = state.role_card.id

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.ranger.ranger_token_location, role_id)

    def test_ranger_token_on_card_preserved(self):
        """Test that ranger token location on a path card is preserved."""
        state = make_test_state()

        # Add a card and put ranger token on it
        doe = SitkaDoe()
        state.areas[Area.WITHIN_REACH].append(doe)
        state.ranger.ranger_token_location = doe.id

        engine = GameEngine(state)

        save_game(engine, self.save_path)
        loaded_engine = load_game(self.save_path)

        self.assertEqual(loaded_engine.state.ranger.ranger_token_location, doe.id)


if __name__ == '__main__':
    unittest.main()
