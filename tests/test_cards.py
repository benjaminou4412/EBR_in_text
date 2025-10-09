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
        moment = MomentCard(id="test-1", title="Test Moment")
        self.assertEqual(moment.title, "Test Moment")
        self.assertEqual(moment.id, "test-1")
        self.assertEqual(moment.card_set, "")  # Default
        self.assertEqual(moment.exhausted, False)  # Default
        self.assertEqual(moment.energy_cost, {})  # Default
        self.assertEqual(moment.approach_icons, {})  # Default

        # Feature with some fields set
        feature = FeatureCard(
            id="test-2",
            title="Test Feature",
            progress_threshold=3,
            presence=2
        )
        self.assertEqual(feature.id, "test-2")
        self.assertEqual(feature.title, "Test Feature")
        self.assertEqual(feature.progress_threshold, 3)
        self.assertEqual(feature.presence, 2)
        self.assertEqual(feature.harm_threshold, None)  # Default
        self.assertEqual(feature.progress, 0)  # Default
        self.assertEqual(feature.harm, 0)  # Default
        self.assertEqual(feature.area, Zone.WITHIN_REACH)  # Default

        # Gear with partial energy cost
        gear = GearCard(
            id="test-3",
            title="Test Gear",
            energy_cost={Aspect.FIT: 2}
        )
        self.assertEqual(gear.id, "test-3")
        self.assertEqual(gear.title, "Test Gear")
        self.assertEqual(gear.energy_cost[Aspect.FIT], 2)
        self.assertEqual(gear.equip_slots, 0)  # Default
        self.assertEqual(gear.exhausted, False)  # Default

        # Being with mixed fields
        being = BeingCard(
            id="test-4",
            title="Test Being",
            harm_threshold=5,
            area=Zone.ALONG_THE_WAY,
            presence=3
        )
        self.assertEqual(being.harm_threshold, 5)
        self.assertEqual(being.area, Zone.ALONG_THE_WAY)
        self.assertEqual(being.presence, 3)
        self.assertEqual(being.progress_threshold, None)  # Default
        self.assertEqual(being.harm_nulled, False)  # Default
        self.assertEqual(being.progress_nulled, False)  # Default


class CardLoadingTests(unittest.TestCase):
    def test_load_walk_with_me(self):
        """Test loading Walk With Me from JSON"""
        wwm = WalkWithMe()

        # These should all come from JSON
        self.assertEqual(wwm.id, "explorer-12-walk-with-me")
        self.assertEqual(wwm.title, "Walk With Me")
        self.assertIsInstance(wwm, MomentCard)
        self.assertEqual(wwm.card_set, "Explorer")
        self.assertIn("Experience", wwm.traits)
        self.assertEqual(wwm.aspect, Aspect.SPI)
        self.assertEqual(wwm.requirement, 1)
        self.assertEqual(wwm.energy_cost.get(Aspect.SPI), 1)
        self.assertEqual(wwm.flavor_text, "Through practice and intention, you've learned to show others the vastness of possibility before them. There are no limits save the ones we place on ourselves.")
        

    def test_a_dear_friend(self):
        """Test loading A Dear Friend from JSON"""
        adf = ADearFriend()

        # These should all come from JSON
        self.assertEqual(adf.id, "conciliator-14-a-dear-friend")
        self.assertEqual(adf.title, "A Dear Friend")
        self.assertIsInstance(adf, AttachmentCard)
        self.assertEqual(adf.card_set, "Conciliator")
        self.assertIn("Experience", adf.traits)
        self.assertIn("Expert", adf.traits)   
        self.assertEqual(adf.aspect, Aspect.SPI)
        self.assertEqual(adf.requirement, 3)
        self.assertEqual(adf.energy_cost.get(Aspect.SPI), 1)
        self.assertEqual(adf.flavor_text, "")
             


if __name__ == '__main__':
    unittest.main()
