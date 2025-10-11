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
        """Test loading Walk With Me from JSON - comprehensive field check"""
        wwm = WalkWithMe()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(wwm.id.startswith("walk-with-me-"))
        self.assertEqual(len(wwm.id), len("walk-with-me-") + 4)  # title + 4-char UUID

        # Fields from JSON
        self.assertEqual(wwm.title, "Walk With Me")
        self.assertEqual(wwm.card_set, "Explorer")
        self.assertIn(CardType.RANGER, wwm.card_types)
        self.assertIn(CardType.MOMENT, wwm.card_types)
        self.assertEqual(len(wwm.traits), 1)
        self.assertIn("Experience", wwm.traits)
        self.assertEqual(wwm.aspect, Aspect.SPI)
        self.assertEqual(wwm.requirement, 1)
        self.assertEqual(wwm.energy_cost, 1)
        self.assertEqual(len(wwm.approach_icons), 1)
        self.assertEqual(wwm.approach_icons[Approach.CONNECTION], 1)
        self.assertEqual(wwm.flavor_text, "Through practice and intention, you've learned to show others the vastness of possibility before them. There are no limits save the ones we place on ourselves.")
        self.assertEqual(len(wwm.abilities_text), 1)
        self.assertIn("Response: After you succeed at a Traverse test", wwm.abilities_text[0])
        self.assertIsNone(wwm.starting_area)  # Moments don't enter play

        # Fields that should be null/default for ranger cards
        self.assertIsNone(wwm.presence)
        self.assertIsNone(wwm.harm_threshold)
        self.assertIsNone(wwm.progress_threshold)
        self.assertFalse(wwm.harm_forbidden)
        self.assertFalse(wwm.progress_forbidden)
        self.assertEqual(wwm.progress, 0)
        self.assertEqual(wwm.harm, 0)
        self.assertIsNone(wwm.equip_value)

        # Mutable state defaults
        self.assertFalse(wwm.exhausted)
        self.assertEqual(len(wwm.modifiers), 0)

    def test_a_dear_friend(self):
        """Test loading A Dear Friend from JSON - comprehensive field check"""
        adf = ADearFriend()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(adf.id.startswith("a-dear-friend-"))
        self.assertEqual(len(adf.id), len("a-dear-friend-") + 4)  # title + 4-char UUID

        # Fields from JSON
        self.assertEqual(adf.title, "A Dear Friend")
        self.assertEqual(adf.card_set, "Conciliator")
        self.assertIn(CardType.RANGER, adf.card_types)
        self.assertIn(CardType.ATTACHMENT, adf.card_types)
        self.assertEqual(len(adf.traits), 2)
        self.assertIn("Experience", adf.traits)
        self.assertIn("Expert", adf.traits)
        self.assertEqual(adf.aspect, Aspect.SPI)
        self.assertEqual(adf.requirement, 3)
        self.assertEqual(adf.energy_cost, 1)
        self.assertEqual(len(adf.approach_icons), 1)
        self.assertEqual(adf.approach_icons[Approach.CONNECTION], 1)
        self.assertEqual(adf.flavor_text, "")
        self.assertEqual(len(adf.abilities_text), 2)
        self.assertIn("Search the path deck", adf.abilities_text[0])
        self.assertIn("Response: After the attached human is cleared", adf.abilities_text[1])
        self.assertIsNone(adf.starting_area)  # Attachments don't have default zone

        # Fields that should be null/default for ranger cards
        self.assertIsNone(adf.presence)
        self.assertIsNone(adf.harm_threshold)
        self.assertIsNone(adf.progress_threshold)
        self.assertFalse(adf.harm_forbidden)
        self.assertFalse(adf.progress_forbidden)
        self.assertEqual(adf.progress, 0)
        self.assertEqual(adf.harm, 0)
        self.assertIsNone(adf.equip_value)

        # Mutable state defaults
        self.assertFalse(adf.exhausted)
        self.assertEqual(len(adf.modifiers), 0)

    def test_load_overgrown_thicket(self):
        """Test loading Overgrown Thicket from JSON - comprehensive field check"""
        ot = OvergrownThicket()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(ot.id.startswith("overgrown-thicket-"))
        self.assertEqual(len(ot.id), len("overgrown-thicket-") + 4)

        # Fields from JSON
        self.assertEqual(ot.title, "Overgrown Thicket")
        self.assertEqual(ot.card_set, "woods")
        self.assertIn(CardType.PATH, ot.card_types)
        self.assertIn(CardType.FEATURE, ot.card_types)
        self.assertEqual(len(ot.traits), 2)
        self.assertIn("Flora", ot.traits)
        self.assertIn("Obstacle", ot.traits)
        self.assertEqual(ot.presence, 1)
        self.assertEqual(ot.harm_threshold, 3)
        self.assertEqual(ot.progress_threshold, 2)  # "2R" parsed to 2 for solo
        self.assertFalse(ot.harm_forbidden)
        self.assertFalse(ot.progress_forbidden)
        self.assertEqual(ot.starting_area, Zone.ALONG_THE_WAY)
        self.assertEqual(len(ot.abilities_text), 3)
        self.assertIn("Obstacle", ot.abilities_text[0])
        self.assertIn("AWA + [exploration]", ot.abilities_text[1])
        self.assertIn("mountain: Discard 1[progress]", ot.abilities_text[2])
        self.assertEqual(ot.flavor_text, "")

        # Fields that should be null/default for path cards
        self.assertIsNone(ot.aspect)
        self.assertEqual(ot.requirement, 0)
        self.assertIsNone(ot.energy_cost)
        self.assertEqual(len(ot.approach_icons), 0)
        self.assertIsNone(ot.equip_value)

        # Mutable state defaults
        self.assertEqual(ot.progress, 0)
        self.assertEqual(ot.harm, 0)
        self.assertFalse(ot.exhausted)
        self.assertEqual(len(ot.modifiers), 0)

    def test_load_sitka_buck(self):
        """Test loading Sitka Buck from JSON - comprehensive field check"""
        sb = SitkaBuck()

        # Test ID format: title-uuid (readable and unique)
        self.assertTrue(sb.id.startswith("sitka-buck-"))
        self.assertEqual(len(sb.id), len("sitka-buck-") + 4)

        # Fields from JSON
        self.assertEqual(sb.title, "Sitka Buck")
        self.assertEqual(sb.card_set, "woods")
        self.assertIn(CardType.PATH, sb.card_types)
        self.assertIn(CardType.BEING, sb.card_types)
        self.assertEqual(len(sb.traits), 2)
        self.assertIn("Prey", sb.traits)
        self.assertIn("Mammal", sb.traits)
        self.assertEqual(sb.presence, 1)
        self.assertEqual(sb.harm_threshold, 3)
        self.assertEqual(sb.progress_threshold, 5)
        self.assertFalse(sb.harm_forbidden)
        self.assertFalse(sb.progress_forbidden)
        self.assertEqual(sb.starting_area, Zone.WITHIN_REACH)
        self.assertEqual(len(sb.abilities_text), 3)  # 3 challenge effects
        self.assertIn("sun:", sb.abilities_text[0])
        self.assertIn("mountain:", sb.abilities_text[1])
        self.assertIn("crest:", sb.abilities_text[2])
        self.assertEqual(sb.flavor_text, "")

        # Fields that should be null/default for path cards
        self.assertIsNone(sb.aspect)
        self.assertEqual(sb.requirement, 0)
        self.assertIsNone(sb.energy_cost)
        self.assertEqual(len(sb.approach_icons), 0)
        self.assertIsNone(sb.equip_value)

        # Mutable state defaults
        self.assertEqual(sb.progress, 0)
        self.assertEqual(sb.harm, 0)
        self.assertFalse(sb.exhausted)
        self.assertEqual(len(sb.modifiers), 0)


if __name__ == '__main__':
    unittest.main()
