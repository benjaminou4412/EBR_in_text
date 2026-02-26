#type:ignore
"""
Tests for Location cards
"""
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import AncestorsGrove, BoulderField


def make_test_ranger():
    """Helper to create a basic test ranger"""
    return RangerState(
        name="Test Ranger",
        aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
    )


class AncestorsGroveTests(unittest.TestCase):
    """Tests for Ancestor's Grove location card"""

    def test_sun_effect_moves_card_from_discard_to_fatigue_stack(self):
        """Test that Sun effect moves a card from discard to top of fatigue stack"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        grove = AncestorsGrove()
        state.areas[Area.SURROUNDINGS].append(grove)

        # Add some cards to discard pile
        card1 = Card(id="card_1", title="Card 1", card_types={CardType.RANGER})
        card2 = Card(id="card_2", title="Card 2", card_types={CardType.RANGER})
        card3 = Card(id="card_3", title="Card 3", card_types={CardType.RANGER})
        ranger.discard.extend([card1, card2, card3])

        # Add some cards to fatigue stack
        fatigue_card = Card(id="fatigue_1", title="Fatigue Card", card_types={CardType.RANGER})
        ranger.fatigue_stack.append(fatigue_card)

        # Execute Sun effect
        cleared = grove._sun_effect(engine)

        # Should return True (effect resolved)
        self.assertTrue(cleared)

        # One card should be moved from discard to top of fatigue stack
        self.assertEqual(len(ranger.discard), 2)
        self.assertEqual(len(ranger.fatigue_stack), 2)

        # The moved card should be on top of fatigue stack (index 0)
        moved_card = ranger.fatigue_stack[0]
        self.assertIn(moved_card, [card1, card2, card3])
        self.assertNotIn(moved_card, ranger.discard)

        # Original fatigue card should still be in stack
        self.assertIn(fatigue_card, ranger.fatigue_stack)

    def test_sun_effect_with_empty_discard(self):
        """Test that Sun effect handles empty discard pile gracefully"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        grove = AncestorsGrove()
        state.areas[Area.SURROUNDINGS].append(grove)

        # Discard pile is empty
        self.assertEqual(len(ranger.discard), 0)

        # Execute Sun effect
        cleared = grove._sun_effect(engine)

        # Should return False (effect could not resolve)
        self.assertFalse(cleared)

        # Nothing should change
        self.assertEqual(len(ranger.discard), 0)
        self.assertEqual(len(ranger.fatigue_stack), 0)

    def test_sun_effect_with_one_card_in_discard(self):
        """Test that Sun effect auto-selects when only one card in discard"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        grove = AncestorsGrove()
        state.areas[Area.SURROUNDINGS].append(grove)

        # Add one card to discard
        only_card = Card(id="only_card", title="Only Card", card_types={CardType.RANGER})
        ranger.discard.append(only_card)

        # Execute Sun effect
        cleared = grove._sun_effect(engine)

        # Should return True
        self.assertTrue(cleared)

        # Card should be moved to fatigue stack
        self.assertEqual(len(ranger.discard), 0)
        self.assertEqual(len(ranger.fatigue_stack), 1)
        self.assertEqual(ranger.fatigue_stack[0], only_card)


class BoulderFieldTests(unittest.TestCase):
    """Tests for Boulder Field location card"""

    def test_reduces_presence_of_beings_by_one(self):
        """Test that Boulder Field reduces presence of all beings by 1"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        # Create beings with different presence values
        being1 = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING},
            presence=3
        )
        being2 = Card(
            id="being_2",
            title="Being 2",
            card_types={CardType.BEING},
            presence=5
        )
        being3 = Card(
            id="being_3",
            title="Being 3",
            card_types={CardType.BEING},
            presence=1
        )

        state.areas[Area.ALONG_THE_WAY].extend([being1, being2, being3])

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Check current presence values
        self.assertEqual(being1.get_current_presence(engine), 2)  # 3 - 1 = 2
        self.assertEqual(being2.get_current_presence(engine), 4)  # 5 - 1 = 4
        self.assertEqual(being3.get_current_presence(engine), 0)  # 1 - 1 = 0

    def test_does_not_reduce_presence_of_features(self):
        """Test that Boulder Field only affects beings, not features"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        # Create a feature with presence
        feature = Card(
            id="feature_1",
            title="Feature 1",
            card_types={CardType.FEATURE},
            presence=3
        )

        state.areas[Area.ALONG_THE_WAY].append(feature)

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Feature presence should be unaffected
        self.assertEqual(feature.get_current_presence(engine), 3)

    def test_presence_reduction_applies_to_new_beings(self):
        """Test that Boulder Field's effect applies to beings that enter play after it"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Now add a new being
        new_being = Card(
            id="new_being",
            title="New Being",
            card_types={CardType.BEING},
            presence=4
        )
        state.areas[Area.WITHIN_REACH].append(new_being)

        # New being should immediately have reduced presence
        self.assertEqual(new_being.get_current_presence(engine), 3)  # 4 - 1 = 3

    def test_presence_reduction_stops_when_boulder_field_removed(self):
        """Test that presence returns to normal when Boulder Field leaves play"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING},
            presence=3
        )
        state.areas[Area.ALONG_THE_WAY].append(being)

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Presence should be reduced
        self.assertEqual(being.get_current_presence(engine), 2)

        # Remove Boulder Field from play
        boulder_field.discard_from_play(engine)

        # Presence should return to normal
        self.assertEqual(being.get_current_presence(engine), 3)

    def test_presence_reduction_stacks_with_card_modifiers(self):
        """Test that Boulder Field's reduction stacks with card-specific modifiers"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING},
            presence=5
        )
        state.areas[Area.ALONG_THE_WAY].append(being)

        # Add a card-specific modifier to the being
        being.modifiers.append(ValueModifier(
            target="presence",
            amount=-2,
            source_id="some_effect"
        ))

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Both modifiers should apply: 5 - 2 (card modifier) - 1 (Boulder Field) = 2
        self.assertEqual(being.get_current_presence(engine), 2)

    def test_presence_cannot_go_below_zero(self):
        """Test that presence reduction respects minimum of 0"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        # Being with presence 1
        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING},
            presence=1
        )
        state.areas[Area.ALONG_THE_WAY].append(being)

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Presence should be 0, not negative
        self.assertEqual(being.get_current_presence(engine), 0)

    def test_multiple_beings_affected_independently(self):
        """Test that Boulder Field affects multiple beings independently"""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        boulder_field = BoulderField()
        state.areas[Area.SURROUNDINGS].append(boulder_field)

        # Create multiple beings in different areas
        being1 = Card(id="being_1", title="Being 1", card_types={CardType.BEING}, presence=2)
        being2 = Card(id="being_2", title="Being 2", card_types={CardType.BEING}, presence=4)
        being3 = Card(id="being_3", title="Being 3", card_types={CardType.BEING}, presence=6)

        state.areas[Area.SURROUNDINGS].append(being1)
        state.areas[Area.ALONG_THE_WAY].append(being2)
        state.areas[Area.WITHIN_REACH].append(being3)

        # Reconstruct to register Boulder Field's constant ability
        engine.reconstruct()

        # Each being's presence should be independently reduced
        self.assertEqual(being1.get_current_presence(engine), 1)
        self.assertEqual(being2.get_current_presence(engine), 3)
        self.assertEqual(being3.get_current_presence(engine), 5)


if __name__ == "__main__":
    unittest.main()
