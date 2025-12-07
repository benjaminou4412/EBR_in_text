#type: ignore
"""Tests for Mission cards, starting with Biscuit Delivery."""

import unittest
from src.models import (
    Card, RangerState, GameState, Aspect, Area, CardType,
    EventType, TimingType, Keyword, Mission, DayEndException
)
from src.engine import GameEngine
from src.cards import BiscuitDelivery, BiscuitBasket, HyPimpotChef, QuisiVosRascal, PeerlessPathfinder


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(20)],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
    )


def make_test_state_with_mission(include_hy: bool = False) -> tuple[GameState, BiscuitDelivery]:
    """Create a test game state with Biscuit Delivery in Surroundings.

    Args:
        include_hy: If True, also add Hy Pimpot to the play area

    Returns:
        Tuple of (GameState, BiscuitDelivery card)
    """
    ranger = make_test_ranger()
    role_card = PeerlessPathfinder()
    biscuit_delivery = BiscuitDelivery()

    # Build location card
    location = Card(
        id="test-location",
        title="Test Location",
        card_types={CardType.LOCATION}
    )

    surroundings = [location, biscuit_delivery]
    along_the_way = []

    if include_hy:
        hy = HyPimpotChef()
        along_the_way.append(hy)

    state = GameState(
        ranger=ranger,
        role_card=role_card,
        location=location,
        areas={
            Area.SURROUNDINGS: surroundings,
            Area.ALONG_THE_WAY: along_the_way,
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [role_card],
        }
    )

    return state, biscuit_delivery


class BiscuitDeliveryListenerTests(unittest.TestCase):
    """Tests for Biscuit Delivery's travel listener setup and triggering."""

    def test_biscuit_delivery_has_travel_listener(self):
        """Test that Biscuit Delivery defines a TRAVEL listener."""
        biscuit = BiscuitDelivery()
        listeners = biscuit.get_listeners()

        self.assertIsNotNone(listeners, "Biscuit Delivery should have listeners")
        self.assertEqual(len(listeners), 1, "Should have exactly one listener")
        self.assertEqual(listeners[0].event_type, EventType.TRAVEL,
                        "Listener should be for TRAVEL event")
        self.assertEqual(listeners[0].timing_type, TimingType.BEFORE,
                        "Listener should trigger BEFORE travel")

    def test_biscuit_delivery_registers_listener_on_enter_play(self):
        """Test that the TRAVEL listener is registered when Biscuit Delivery enters play."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Count listeners before entering play
        initial_listener_count = len(engine.listeners)

        # Enter play
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Should have one more listener
        self.assertEqual(len(engine.listeners), initial_listener_count + 1,
                        "Should register one new listener on enter play")

        # The new listener should be for TRAVEL
        travel_listeners = [l for l in engine.listeners if l.event_type == EventType.TRAVEL]
        self.assertTrue(any(l.source_card_id == biscuit.id for l in travel_listeners),
                       "Should have a TRAVEL listener from Biscuit Delivery")

    def test_biscuit_delivery_listener_active_when_hy_pimpot_in_play(self):
        """Test that the listener's active condition is true when Hy Pimpot is in play
        and the current location is Lone Tree Station."""
        state, biscuit = make_test_state_with_mission(include_hy=True)
        # The listener only fires when traveling from Lone Tree Station
        state.location.title = "Lone Tree Station"
        engine = GameEngine(state)

        listeners = biscuit.get_listeners()
        listener = listeners[0]

        # Check the active condition
        is_active = listener.active(engine, None)
        self.assertTrue(is_active,
                       "Listener should be active when Hy Pimpot is in play and at Lone Tree Station")

    def test_biscuit_delivery_listener_inactive_when_hy_pimpot_not_in_play(self):
        """Test that the listener's active condition is false when Hy Pimpot is NOT in play."""
        state, biscuit = make_test_state_with_mission(include_hy=False)
        state.location.title = "Lone Tree Station"  # Even at correct location
        engine = GameEngine(state)

        listeners = biscuit.get_listeners()
        listener = listeners[0]

        # Check the active condition
        is_active = listener.active(engine, None)
        self.assertFalse(is_active, "Listener should be inactive when Hy Pimpot is not in play")

    def test_biscuit_delivery_listener_inactive_when_not_at_lone_tree_station(self):
        """Test that the listener's active condition is false when NOT at Lone Tree Station,
        even if Hy Pimpot is in play."""
        state, biscuit = make_test_state_with_mission(include_hy=True)
        # Location is "Test Location" by default, not Lone Tree Station
        engine = GameEngine(state)

        listeners = biscuit.get_listeners()
        listener = listeners[0]

        # Check the active condition - should be false because we're not at Lone Tree Station
        is_active = listener.active(engine, None)
        self.assertFalse(is_active,
                        "Listener should be inactive when not at Lone Tree Station")

    def test_biscuit_delivery_listener_cleaned_up_on_discard(self):
        """Test that the listener is removed when Biscuit Delivery is discarded."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Enter play to register listener
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Verify listener exists
        biscuit_listeners = [l for l in engine.listeners if l.source_card_id == biscuit.id]
        self.assertEqual(len(biscuit_listeners), 1, "Should have listener registered")

        # Discard the card
        biscuit.discard_from_play(engine)

        # Verify listener removed
        biscuit_listeners_after = [l for l in engine.listeners if l.source_card_id == biscuit.id]
        self.assertEqual(len(biscuit_listeners_after), 0,
                        "Listener should be removed when card is discarded")

    def test_biscuit_delivery_listener_cleaned_up_on_flip(self):
        """Test that the listener is removed when Biscuit Delivery flips to Biscuit Basket."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Enter play to register listener
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Verify listener exists
        biscuit_listeners = [l for l in engine.listeners if l.source_card_id == biscuit.id]
        self.assertEqual(len(biscuit_listeners), 1, "Should have listener registered")

        # Flip the card
        basket = biscuit.flip(engine)

        # Verify original listener removed (by checking for Biscuit Delivery's ID)
        biscuit_listeners_after = [l for l in engine.listeners if l.source_card_id == biscuit.id]
        self.assertEqual(len(biscuit_listeners_after), 0,
                        "Biscuit Delivery listener should be removed on flip")


class BiscuitDeliveryFlipTests(unittest.TestCase):
    """Tests for Biscuit Delivery flipping to Biscuit Basket."""

    def test_biscuit_delivery_has_biscuit_basket_as_backside(self):
        """Test that Biscuit Delivery is correctly linked to Biscuit Basket."""
        biscuit = BiscuitDelivery()

        self.assertIsNotNone(biscuit.backside, "Should have a backside")
        self.assertEqual(biscuit.backside.title, "Biscuit Basket",
                        "Backside should be Biscuit Basket")

    def test_biscuit_basket_has_biscuit_delivery_as_backside(self):
        """Test that Biscuit Basket is correctly linked back to Biscuit Delivery."""
        biscuit = BiscuitDelivery()
        basket = biscuit.backside

        self.assertIsNotNone(basket.backside, "Basket should have a backside")
        self.assertEqual(basket.backside.title, "Biscuit Delivery",
                        "Basket's backside should be Biscuit Delivery")

    def test_flip_replaces_biscuit_delivery_with_basket_in_area(self):
        """Test that flipping replaces Biscuit Delivery with Biscuit Basket in the area."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Verify Biscuit Delivery is in Surroundings
        self.assertIn(biscuit, state.areas[Area.SURROUNDINGS])

        # Flip
        basket = biscuit.flip(engine)

        # Biscuit Delivery should be gone, Biscuit Basket should be there
        self.assertNotIn(biscuit, state.areas[Area.SURROUNDINGS],
                        "Biscuit Delivery should be removed from area")
        self.assertIn(basket, state.areas[Area.SURROUNDINGS],
                     "Biscuit Basket should be in the area")

    def test_campaign_entry_1_01_flips_and_equips_basket(self):
        """Test that resolving campaign entry 1.01 flips Biscuit Delivery and equips the basket."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Put Biscuit Delivery in play properly
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Resolve entry 1.01 (the objective completion entry)
        result = engine.campaign_guide.resolve_entry("1.01", biscuit, engine, None)

        # Biscuit Basket should now be in Player Area
        basket_in_player_area = [c for c in state.areas[Area.PLAYER_AREA]
                                  if c.title == "Biscuit Basket"]
        self.assertEqual(len(basket_in_player_area), 1,
                        "Biscuit Basket should be equipped in Player Area")

        # Original Biscuit Delivery should not be in any play area
        for area in [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH]:
            biscuit_in_area = [c for c in state.areas[area] if c.title == "Biscuit Delivery"]
            self.assertEqual(len(biscuit_in_area), 0,
                            f"Biscuit Delivery should not be in {area.value}")


class BiscuitDeliveryCampaignOverrideTests(unittest.TestCase):
    """Tests for Biscuit Delivery's campaign guide entry override ability."""

    def test_biscuit_delivery_has_override_constant_ability(self):
        """Test that Biscuit Delivery defines an OVERRIDE_CAMPAIGN_ENTRY constant ability."""
        from src.models import ConstantAbilityType

        biscuit = BiscuitDelivery()
        abilities = biscuit.get_constant_abilities()

        self.assertIsNotNone(abilities, "Should have constant abilities")
        self.assertEqual(len(abilities), 1, "Should have exactly one constant ability")
        self.assertEqual(abilities[0].ability_type, ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY,
                        "Ability should be OVERRIDE_CAMPAIGN_ENTRY type")
        self.assertEqual(abilities[0].override_entry, "91",
                        "Should override to entry 91")

    def test_override_condition_matches_hy_pimpot(self):
        """Test that the override condition matches Hy Pimpot."""
        biscuit = BiscuitDelivery()
        abilities = biscuit.get_constant_abilities()
        condition = abilities[0].condition_fn

        hy = HyPimpotChef()
        state = GameState(ranger=make_test_ranger())

        self.assertTrue(condition(state, hy),
                       "Override condition should match Hy Pimpot")

    def test_override_condition_matches_quisi(self):
        """Test that the override condition matches Quisi Vos."""
        biscuit = BiscuitDelivery()
        abilities = biscuit.get_constant_abilities()
        condition = abilities[0].condition_fn

        quisi = QuisiVosRascal()
        state = GameState(ranger=make_test_ranger())

        self.assertTrue(condition(state, quisi),
                       "Override condition should match Quisi Vos")

    def test_override_condition_does_not_match_other_cards(self):
        """Test that the override condition doesn't match unrelated cards."""
        biscuit = BiscuitDelivery()
        abilities = biscuit.get_constant_abilities()
        condition = abilities[0].condition_fn

        other_card = Card(id="other", title="Some Other Card")
        state = GameState(ranger=make_test_ranger())

        self.assertFalse(condition(state, other_card),
                        "Override condition should not match unrelated cards")

    def test_hy_pimpot_entry_not_overridden_before_biscuit_delivery_in_play(self):
        """Test that Hy Pimpot's entry is NOT overridden when Biscuit Delivery is not in play."""
        ranger = make_test_ranger()
        hy = HyPimpotChef()

        # State WITHOUT Biscuit Delivery
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [hy],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        engine = GameEngine(state)

        # Clear messages
        engine.clear_messages()

        # Resolve Hy Pimpot's entry
        engine.campaign_guide.resolve_entry("47", hy, engine, None)

        # Should see entry 47 text, not entry 91
        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("47", message_text,
                     "Should resolve entry 47 when Biscuit Delivery not in play")
        self.assertNotIn("91", message_text,
                        "Should NOT resolve entry 91 when Biscuit Delivery not in play")

    def test_hy_pimpot_entry_overridden_while_biscuit_delivery_in_play(self):
        """Test that Hy Pimpot's entry IS overridden to 91 when Biscuit Delivery is in play."""
        state, biscuit = make_test_state_with_mission(include_hy=True)
        engine = GameEngine(state)

        # Enter play to register constant ability
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Get Hy from the state
        hy = state.get_in_play_cards_by_title("Hy Pimpot, Chef")[0]

        # Clear messages
        engine.clear_messages()

        # Resolve what would be Hy's normal entry
        engine.campaign_guide.resolve_entry("47", hy, engine, None)

        # Should see entry 91 text (overridden)
        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91", message_text,
                     "Should resolve entry 91 (override) when Biscuit Delivery is in play")
        self.assertIn("91.3", message_text,
                     "Should route to entry 91.3 for Hy Pimpot specifically")

    def test_quisi_entry_overridden_while_biscuit_delivery_in_play(self):
        """Test that Quisi's entry IS overridden to 91 when Biscuit Delivery is in play."""
        state, biscuit = make_test_state_with_mission()
        quisi = QuisiVosRascal()
        state.areas[Area.WITHIN_REACH].append(quisi)

        engine = GameEngine(state)

        # Enter play to register constant ability
        biscuit.enters_play(engine, Area.SURROUNDINGS, None)

        # Clear messages
        engine.clear_messages()

        # Resolve what would be Quisi's normal entry
        engine.campaign_guide.resolve_entry("80", quisi, engine, None)

        # Should see entry 91 text (overridden)
        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91", message_text,
                     "Should resolve entry 91 (override) when Biscuit Delivery is in play")
        self.assertIn("91.4", message_text,
                     "Should route to entry 91.4 for Quisi specifically")

    def test_entries_not_overridden_after_biscuit_delivery_discarded(self):
        """Test that entries are NOT overridden after Biscuit Delivery leaves play."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Card is already in surroundings and reconstruct() registered its constant abilities
        # Verify override is active (registered by reconstruct() during engine init)
        from src.models import ConstantAbilityType
        override_abilities = engine.get_constant_abilities_by_type(
            ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY
        )
        self.assertEqual(len(override_abilities), 1, "Override should be active")

        # Discard Biscuit Delivery
        biscuit.discard_from_play(engine)

        # Verify override is no longer active
        override_abilities_after = engine.get_constant_abilities_by_type(
            ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY
        )
        self.assertEqual(len(override_abilities_after), 0,
                        "Override should be removed after discard")

        # Now add Hy and check that his entry is NOT overridden
        hy = HyPimpotChef()
        state.areas[Area.ALONG_THE_WAY].append(hy)

        engine.clear_messages()
        engine.campaign_guide.resolve_entry("47", hy, engine, None)

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("47", message_text,
                     "Should resolve entry 47 after Biscuit Delivery discarded")
        self.assertNotIn("Entry 91", message_text,
                        "Should NOT resolve entry 91 after Biscuit Delivery discarded")

    def test_entries_not_overridden_after_biscuit_delivery_flips(self):
        """Test that entries are NOT overridden after Biscuit Delivery flips to Biscuit Basket."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Card is already in surroundings and reconstruct() registered its constant abilities
        # Verify override is active (registered by reconstruct() during engine init)
        from src.models import ConstantAbilityType
        override_abilities = engine.get_constant_abilities_by_type(
            ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY
        )
        self.assertEqual(len(override_abilities), 1, "Override should be active")

        # Flip Biscuit Delivery to Biscuit Basket
        basket = biscuit.flip(engine)

        # Verify override is no longer active (Biscuit Basket doesn't have the override)
        override_abilities_after = engine.get_constant_abilities_by_type(
            ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY
        )
        self.assertEqual(len(override_abilities_after), 0,
                        "Override should be removed after flip")

        # Now add Hy and check that his entry is NOT overridden
        hy = HyPimpotChef()
        state.areas[Area.ALONG_THE_WAY].append(hy)

        engine.clear_messages()
        engine.campaign_guide.resolve_entry("47", hy, engine, None)

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("47", message_text,
                     "Should resolve entry 47 after Biscuit Delivery flips")
        self.assertNotIn("Entry 91", message_text,
                        "Should NOT resolve entry 91 after Biscuit Delivery flips")


class BiscuitBasketTests(unittest.TestCase):
    """Basic tests for Biscuit Basket card."""

    def test_biscuit_basket_is_gear_not_mission(self):
        """Test that Biscuit Basket is a Gear card (not Mission type)."""
        basket = BiscuitBasket()
        self.assertTrue(basket.has_type(CardType.GEAR),
                       "Biscuit Basket should be Gear type")
        self.assertFalse(basket.has_type(CardType.MISSION),
                        "Biscuit Basket should NOT have Mission type")

    def test_biscuit_basket_does_not_have_override_ability(self):
        """Test that Biscuit Basket does NOT have the campaign entry override."""
        basket = BiscuitBasket()
        abilities = basket.get_constant_abilities()

        # Should be None or empty
        self.assertTrue(abilities is None or len(abilities) == 0,
                       "Biscuit Basket should not have the override ability")


class Entry91RoutingTests(unittest.TestCase):
    """Tests for entry 91's routing to sub-entries based on which card triggers it."""

    def test_entry_91_routes_to_91_3_for_hy_entering_play(self):
        """Test that entry 91 routes to 91.3 when Hy Pimpot enters play."""
        state, biscuit = make_test_state_with_mission()
        hy = HyPimpotChef()
        engine = GameEngine(state)

        engine.clear_messages()

        # Directly call entry 91 with Hy as source and no clear_type (entering play)
        engine.campaign_guide.entries["91"](hy, engine, None)

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91.3", message_text,
                     "Entry 91 should route to 91.3 for Hy entering play")
        self.assertIn("biscuits", message_text.lower(),
                     "Should show Hy's story about biscuits")

    def test_entry_91_routes_to_91_4_for_quisi_entering_play(self):
        """Test that entry 91 routes to 91.4 when Quisi enters play."""
        state, biscuit = make_test_state_with_mission()
        quisi = QuisiVosRascal()
        engine = GameEngine(state)

        engine.clear_messages()

        # Directly call entry 91 with Quisi as source and no clear_type (entering play)
        engine.campaign_guide.entries["91"](quisi, engine, None)

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91.4", message_text,
                     "Entry 91 should route to 91.4 for Quisi entering play")
        self.assertIn("kitchen", message_text.lower(),
                     "Should show Quisi's story about finding the kitchen")

    def test_entry_91_routes_to_91_7_for_hy_cleared_by_progress(self):
        """Test that entry 91 routes to 91.7 when Hy is cleared by progress."""
        state, biscuit = make_test_state_with_mission()
        hy = HyPimpotChef()
        hy.progress = 5  # Give him some progress to remove
        state.areas[Area.ALONG_THE_WAY].append(hy)
        engine = GameEngine(state)

        engine.clear_messages()

        # Directly call entry 91 with progress clear_type
        engine.campaign_guide.entries["91"](hy, engine, "progress")

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91.7", message_text,
                     "Entry 91 should route to 91.7 for Hy cleared by progress")
        # Hy's progress should be removed but he stays in play
        self.assertEqual(hy.progress, 0, "Hy's progress should be removed")

    def test_entry_91_routes_to_91_8_for_quisi_cleared_by_progress(self):
        """Test that entry 91 routes to 91.8 when Quisi is cleared by progress."""
        state, biscuit = make_test_state_with_mission()
        quisi = QuisiVosRascal()
        state.areas[Area.WITHIN_REACH].append(quisi)
        engine = GameEngine(state)

        engine.clear_messages()

        # Directly call entry 91 with progress clear_type
        result = engine.campaign_guide.entries["91"](quisi, engine, "progress")

        messages = [m.message for m in engine.message_queue]
        message_text = " ".join(messages)

        self.assertIn("91.8", message_text,
                     "Entry 91 should route to 91.8 for Quisi cleared by progress")
        self.assertTrue(result, "Entry 91.8 should return True (Quisi discarded)")


class BiscuitDeliverySunEffectTests(unittest.TestCase):
    """Tests for Biscuit Delivery's Sun challenge effect that searches for Quisi."""

    def test_sun_effect_does_not_fire_when_quisi_in_path_discard(self):
        """Sun effect should NOT resolve if Quisi is in the path discard."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Put Quisi in the path discard
        quisi = QuisiVosRascal()
        state.path_discard.append(quisi)

        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertFalse(result, "Sun effect should not resolve when Quisi is in path discard")
        messages = " ".join([m.message for m in engine.message_queue])
        self.assertIn("path discard", messages.lower(),
                     "Should mention Quisi was found in path discard")

    def test_sun_effect_fires_when_quisi_in_valley_set(self):
        """Sun effect SHOULD resolve if Quisi is not in any game zone (in Valley set)."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Don't add Quisi anywhere - she's in the "Valley set"
        # Verify she's not in any zone
        self.assertIsNone(state.get_card_by_title("Quisi Vos, Rascal"),
                         "Quisi should not be in any game zone initially")

        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertTrue(result, "Sun effect should resolve when Quisi is in Valley set")

        # Quisi should now be in play
        quisi_in_play = state.get_in_play_cards_by_title("Quisi Vos, Rascal")
        self.assertIsNotNone(quisi_in_play, "Quisi should now be in play")
        self.assertEqual(len(quisi_in_play), 1, "Should be exactly one Quisi in play")

        messages = " ".join([m.message for m in engine.message_queue])
        self.assertIn("valley set", messages.lower(),
                     "Should mention searching Valley set")
        self.assertIn("putting her into play", messages.lower(),
                     "Should mention putting Quisi into play")

    def test_sun_effect_does_not_fire_when_quisi_already_in_play(self):
        """Sun effect should NOT resolve if Quisi is already in play."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Put Quisi in play
        quisi = QuisiVosRascal()
        state.areas[Area.ALONG_THE_WAY].append(quisi)

        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertFalse(result, "Sun effect should not resolve when Quisi is already in play")
        messages = " ".join([m.message for m in engine.message_queue])
        self.assertIn("does not resolve", messages.lower(),
                     "Should indicate effect does not resolve")

    def test_sun_effect_does_not_fire_when_quisi_in_path_deck(self):
        """Sun effect should NOT resolve if Quisi is in the path deck."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Put Quisi in the path deck
        quisi = QuisiVosRascal()
        state.path_deck.append(quisi)

        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertFalse(result, "Sun effect should not resolve when Quisi is in path deck")

    def test_sun_effect_does_not_fire_when_quisi_in_ranger_hand(self):
        """Sun effect should NOT resolve if Quisi is in the ranger's hand."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Put Quisi in ranger's hand
        quisi = QuisiVosRascal()
        state.ranger.hand.append(quisi)

        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertFalse(result, "Sun effect should not resolve when Quisi is in ranger's hand")

    def test_sun_effect_quisi_enters_play_correctly(self):
        """When Sun effect fires, Quisi should enter play via draw_path_card."""
        state, biscuit = make_test_state_with_mission()
        engine = GameEngine(state)

        # Quisi not in any zone - she's in Valley set
        engine.clear_messages()
        result = biscuit._sun_effect(engine)

        self.assertTrue(result)

        # Find Quisi in play
        quisi_cards = state.get_in_play_cards_by_title("Quisi Vos, Rascal")
        self.assertIsNotNone(quisi_cards)
        quisi = quisi_cards[0]

        # Verify she entered play properly (should be in an area)
        quisi_area = state.get_card_area_by_id(quisi.id)
        self.assertIsNotNone(quisi_area, "Quisi should be in a play area")


class BiscuitBasketListenerTests(unittest.TestCase):
    """Tests for Biscuit Basket's HAVE_X_TOKENS listener."""

    def test_biscuit_basket_listener_triggers_when_biscuits_reach_zero(self):
        """Moving the last biscuit off Biscuit Basket should trigger its listener.

        Expected: Listener fires and attempts to resolve campaign entry 1.02,
        which doesn't exist yet, causing a KeyError.
        """
        state, biscuit_delivery = make_test_state_with_mission()
        engine = GameEngine(state)
        engine.state.campaign_tracker.active_missions.append(Mission("Biscuit Delivery"))

        # Flip Biscuit Delivery to get Biscuit Basket
        # First need to put it in play properly
        biscuit_delivery.enters_play(engine, Area.SURROUNDINGS, None)
        basket = biscuit_delivery.flip(engine)

        # Verify the listener was registered
        have_x_listeners = [l for l in engine.listeners if l.event_type == EventType.HAVE_X_TOKENS]
        self.assertEqual(len(have_x_listeners), 1, "Should have one HAVE_X_TOKENS listener registered")
        self.assertEqual(have_x_listeners[0].source_card_id, basket.id,
                        "Listener should be from Biscuit Basket")

        # Basket should start with 3 biscuits
        self.assertEqual(basket.unique_tokens.get("biscuit", 0), 3,
                        "Biscuit Basket should start with 3 biscuits")

        # Add a human to receive biscuits
        hy = HyPimpotChef()
        state.areas[Area.ALONG_THE_WAY].append(hy)

        # Move biscuits off one at a time - last one should trigger listener
        engine.move_token(basket.id, hy.id, "biscuit", 1)
        self.assertEqual(basket.unique_tokens["biscuit"], 2)

        engine.move_token(basket.id, hy.id, "biscuit", 1)
        self.assertEqual(basket.unique_tokens["biscuit"], 1)

        # This should trigger the listener and cause the day to end
        with self.assertRaises(DayEndException, msg="Should raise DayEndException for completing entry 1.03"):
            engine.move_token(basket.id, hy.id, "biscuit", 1)


if __name__ == '__main__':
    unittest.main()
