"""
Tests for card creation and loading
"""

import unittest
from src.models import *
from src.cards import *


class CardCreationTests(unittest.TestCase):
    def test_dummy_card_defaults(self):
        """Test that dummy cards respect set parameters and use proper defaults"""

        # Minimal moment card
        moment = Card(id="test-1", title="Test Moment", card_types={CardType.RANGER, CardType.MOMENT})
        self.assertEqual(moment.title, "Test Moment")
        self.assertEqual(moment.id, "test-1")
        self.assertIn(CardType.RANGER, moment.card_types)
        self.assertIn(CardType.MOMENT, moment.card_types)
        self.assertEqual(moment.card_set, "")  # Default
        self.assertEqual(moment.exhausted, False)  # Default
        self.assertEqual(moment.energy_cost, None)  # Default
        self.assertEqual(moment.approach_icons, {})  # Default

        # Feature with some fields set
        feature = Card(
            id="test-2",
            title="Test Feature",
            card_types={CardType.PATH, CardType.FEATURE},
            progress_threshold=3,
            presence=2
        )
        self.assertIn(CardType.PATH, feature.card_types)
        self.assertIn(CardType.FEATURE, feature.card_types)
        self.assertEqual(feature.id, "test-2")
        self.assertEqual(feature.title, "Test Feature")
        self.assertEqual(feature.progress_threshold, 3)
        self.assertEqual(feature.presence, 2)
        self.assertEqual(feature.harm_threshold, None)  # Default
        self.assertEqual(feature.progress, 0)  # Default
        self.assertEqual(feature.harm, 0)  # Default
        self.assertEqual(feature.starting_area, None)  # Default

        # Gear with partial energy cost
        gear = Card(
            id="test-3",
            title="Test Gear",
            aspect=Aspect.FIT,
            equip_value=0,
            energy_cost=2
        )
        self.assertEqual(gear.id, "test-3")
        self.assertEqual(gear.title, "Test Gear")
        self.assertEqual(gear.aspect, Aspect.FIT)
        self.assertEqual(gear.energy_cost, 2)
        self.assertEqual(gear.equip_value, 0) 
        self.assertEqual(gear.exhausted, False)  # Default

        # Being with mixed fields
        being = Card(
            id="test-4",
            title="Test Being",
            harm_threshold=5,
            starting_area=Zone.ALONG_THE_WAY,
            presence=3
        )
        self.assertEqual(being.harm_threshold, 5)
        self.assertEqual(being.starting_area, Zone.ALONG_THE_WAY)
        self.assertEqual(being.presence, 3)
        self.assertEqual(being.progress_threshold, None)  # Default
        self.assertEqual(being.harm_forbidden, False)  # Default
        self.assertEqual(being.progress_forbidden, False)  # Default


class CardLoadingTests(unittest.TestCase):
    def test_load_walk_with_me(self):
        """Test loading Walk With Me from JSON"""
        wwm = WalkWithMe()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(wwm.id.startswith("walk-with-me-"))
        self.assertEqual(len(wwm.id), len("walk-with-me-") + 4)  # title + 4-char UUID

        # These should all come from JSON
        self.assertEqual(wwm.title, "Walk With Me")
        self.assertIn(CardType.RANGER, wwm.card_types)
        self.assertIn(CardType.MOMENT, wwm.card_types)
        self.assertEqual(wwm.card_set, "Explorer")
        self.assertIn("Experience", wwm.traits)
        self.assertEqual(wwm.aspect, Aspect.SPI)
        self.assertEqual(wwm.requirement, 1)
        self.assertEqual(wwm.energy_cost, 1)
        self.assertEqual(wwm.flavor_text, "Through practice and intention, you've learned to show others the vastness of possibility before them. There are no limits save the ones we place on ourselves.")

    def test_a_dear_friend(self):
        """Test loading A Dear Friend from JSON"""
        adf = ADearFriend()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(adf.id.startswith("a-dear-friend-"))
        self.assertEqual(len(adf.id), len("a-dear-friend-") + 4)  # title + 4-char UUID

        # These should all come from JSON
        self.assertEqual(adf.title, "A Dear Friend")
        self.assertIn(CardType.RANGER, adf.card_types)
        self.assertIn(CardType.ATTACHMENT, adf.card_types)
        self.assertEqual(adf.card_set, "Conciliator")
        self.assertIn("Experience", adf.traits)
        self.assertIn("Expert", adf.traits)
        self.assertEqual(adf.aspect, Aspect.SPI)
        self.assertEqual(adf.requirement, 3)
        self.assertEqual(adf.energy_cost, 1)
        self.assertEqual(adf.flavor_text, "")
             


if __name__ == '__main__':
    unittest.main()
