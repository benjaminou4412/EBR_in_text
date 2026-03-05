"""
Tests for models.py — challenge deck and day registry data integrity.
"""

import unittest
from collections import Counter
from ebr.models import (
    _build_challenge_deck, _default_day_registry,
    ChallengeIcon, Aspect, ChallengeCard, DayContent
)


# ── Theme 1: Challenge deck data integrity ───────────────────────────────

class ChallengeDeckStructureTests(unittest.TestCase):
    """Structural invariants of the 24-card challenge deck."""

    def setUp(self):
        self.deck = _build_challenge_deck()

    def test_exactly_24_cards(self):
        self.assertEqual(len(self.deck), 24)

    def test_all_cards_are_challenge_cards(self):
        for card in self.deck:
            self.assertIsInstance(card, ChallengeCard)

    def test_icon_distribution_8_each(self):
        icons = Counter(c.icon for c in self.deck)
        self.assertEqual(icons[ChallengeIcon.SUN], 8)
        self.assertEqual(icons[ChallengeIcon.MOUNTAIN], 8)
        self.assertEqual(icons[ChallengeIcon.CREST], 8)

    def test_exactly_4_reshuffle_cards(self):
        reshuffle_count = sum(1 for c in self.deck if c.reshuffle)
        self.assertEqual(reshuffle_count, 4)

    def test_every_card_has_all_four_aspects(self):
        for i, card in enumerate(self.deck):
            with self.subTest(card_index=i):
                self.assertEqual(set(card.mods.keys()), {Aspect.AWA, Aspect.FIT, Aspect.SPI, Aspect.FOC})

    def test_mod_values_in_valid_range(self):
        """All modifier values should be between -2 and +1 inclusive."""
        for i, card in enumerate(self.deck):
            for aspect, value in card.mods.items():
                with self.subTest(card_index=i, aspect=aspect):
                    self.assertGreaterEqual(value, -2)
                    self.assertLessEqual(value, 1)

    def test_mod_sums_are_zero_or_negative_two(self):
        """Every card's mods sum to either 0 or -2."""
        for i, card in enumerate(self.deck):
            with self.subTest(card_index=i):
                self.assertIn(sum(card.mods.values()), (0, -2))

    def test_reshuffle_cards_sum_to_zero(self):
        """Reshuffle cards always sum to 0 (they have the -2 balanced out)."""
        for i, card in enumerate(self.deck):
            if card.reshuffle:
                with self.subTest(card_index=i):
                    self.assertEqual(sum(card.mods.values()), 0)

    def test_reshuffle_cards_each_penalize_different_aspect(self):
        """Each reshuffle card has its -2 in a different aspect, covering all four."""
        reshuffle_cards = [c for c in self.deck if c.reshuffle]
        penalized_aspects = set()
        for card in reshuffle_cards:
            neg2_aspects = [a for a, v in card.mods.items() if v == -2]
            self.assertEqual(len(neg2_aspects), 1)
            penalized_aspects.add(neg2_aspects[0])
        self.assertEqual(penalized_aspects, {Aspect.AWA, Aspect.FIT, Aspect.SPI, Aspect.FOC})


class ChallengeDeckSpotCheckTests(unittest.TestCase):
    """Pin specific card values to catch data entry mutations."""

    def setUp(self):
        self.deck = _build_challenge_deck()

    def test_card_0_reshuffle_sun(self):
        c = self.deck[0]
        self.assertEqual(c.icon, ChallengeIcon.SUN)
        self.assertTrue(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], 0)
        self.assertEqual(c.mods[Aspect.FIT], -2)
        self.assertEqual(c.mods[Aspect.SPI], 1)
        self.assertEqual(c.mods[Aspect.FOC], 1)

    def test_card_4_reshuffle_crest(self):
        c = self.deck[4]
        self.assertEqual(c.icon, ChallengeIcon.CREST)
        self.assertTrue(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], 1)
        self.assertEqual(c.mods[Aspect.FIT], 1)
        self.assertEqual(c.mods[Aspect.SPI], -2)
        self.assertEqual(c.mods[Aspect.FOC], 0)

    def test_card_11_reshuffle_crest(self):
        c = self.deck[11]
        self.assertEqual(c.icon, ChallengeIcon.CREST)
        self.assertTrue(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], 1)
        self.assertEqual(c.mods[Aspect.FIT], 0)
        self.assertEqual(c.mods[Aspect.SPI], 1)
        self.assertEqual(c.mods[Aspect.FOC], -2)

    def test_card_13_reshuffle_sun(self):
        c = self.deck[13]
        self.assertEqual(c.icon, ChallengeIcon.SUN)
        self.assertTrue(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], -2)
        self.assertEqual(c.mods[Aspect.FIT], 1)
        self.assertEqual(c.mods[Aspect.SPI], 0)
        self.assertEqual(c.mods[Aspect.FOC], 1)

    def test_card_2_mountain_non_reshuffle(self):
        c = self.deck[2]
        self.assertEqual(c.icon, ChallengeIcon.MOUNTAIN)
        self.assertFalse(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], -1)
        self.assertEqual(c.mods[Aspect.FIT], 0)
        self.assertEqual(c.mods[Aspect.SPI], 0)
        self.assertEqual(c.mods[Aspect.FOC], -1)

    def test_card_9_mountain_non_reshuffle(self):
        c = self.deck[9]
        self.assertEqual(c.icon, ChallengeIcon.MOUNTAIN)
        self.assertFalse(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], -1)
        self.assertEqual(c.mods[Aspect.FIT], 1)
        self.assertEqual(c.mods[Aspect.SPI], 1)
        self.assertEqual(c.mods[Aspect.FOC], -1)

    def test_card_18_crest_non_reshuffle(self):
        c = self.deck[18]
        self.assertEqual(c.icon, ChallengeIcon.CREST)
        self.assertFalse(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], 0)
        self.assertEqual(c.mods[Aspect.FIT], 0)
        self.assertEqual(c.mods[Aspect.SPI], -1)
        self.assertEqual(c.mods[Aspect.FOC], 1)

    def test_card_23_mountain_non_reshuffle(self):
        """Last card in deck."""
        c = self.deck[23]
        self.assertEqual(c.icon, ChallengeIcon.MOUNTAIN)
        self.assertFalse(c.reshuffle)
        self.assertEqual(c.mods[Aspect.AWA], 0)
        self.assertEqual(c.mods[Aspect.FIT], -1)
        self.assertEqual(c.mods[Aspect.SPI], 0)
        self.assertEqual(c.mods[Aspect.FOC], 1)


# ── Theme 2: Day registry data integrity ─────────────────────────────────

class DayRegistryStructureTests(unittest.TestCase):
    """Structural invariants of the 30-day registry."""

    def setUp(self):
        self.registry = _default_day_registry()

    def test_exactly_30_days(self):
        self.assertEqual(len(self.registry), 30)

    def test_days_are_1_through_30(self):
        self.assertEqual(set(self.registry.keys()), set(range(1, 31)))

    def test_all_values_are_day_content(self):
        for day, content in self.registry.items():
            with self.subTest(day=day):
                self.assertIsInstance(content, DayContent)

    def test_all_weather_names_are_valid(self):
        valid_weather = {"A Perfect Day", "Downpour", "Howling Winds"}
        for day, content in self.registry.items():
            with self.subTest(day=day):
                self.assertIn(content.weather, valid_weather)

    def test_weather_distribution(self):
        counts = Counter(c.weather for c in self.registry.values())
        self.assertEqual(counts["A Perfect Day"], 9)
        self.assertEqual(counts["Downpour"], 13)
        self.assertEqual(counts["Howling Winds"], 8)

    def test_only_days_3_and_4_have_entries(self):
        days_with_entries = {k for k, v in self.registry.items() if v.entries}
        self.assertEqual(days_with_entries, {3, 4})

    def test_entries_are_lists(self):
        for day, content in self.registry.items():
            with self.subTest(day=day):
                self.assertIsInstance(content.entries, list)


class DayRegistrySpotCheckTests(unittest.TestCase):
    """Pin specific day→weather mappings and campaign entries."""

    def setUp(self):
        self.registry = _default_day_registry()

    def test_day_1_a_perfect_day(self):
        self.assertEqual(self.registry[1].weather, "A Perfect Day")
        self.assertEqual(self.registry[1].entries, [])

    def test_day_3_a_perfect_day_with_entry(self):
        self.assertEqual(self.registry[3].weather, "A Perfect Day")
        self.assertEqual(self.registry[3].entries, ["94.1"])

    def test_day_4_downpour_with_entry(self):
        self.assertEqual(self.registry[4].weather, "Downpour")
        self.assertEqual(self.registry[4].entries, ["1.04"])

    def test_day_13_howling_winds(self):
        self.assertEqual(self.registry[13].weather, "Howling Winds")
        self.assertEqual(self.registry[13].entries, [])

    def test_day_21_a_perfect_day(self):
        self.assertEqual(self.registry[21].weather, "A Perfect Day")

    def test_day_30_a_perfect_day(self):
        self.assertEqual(self.registry[30].weather, "A Perfect Day")

    def test_day_20_howling_winds(self):
        self.assertEqual(self.registry[20].weather, "Howling Winds")

    def test_day_10_downpour(self):
        self.assertEqual(self.registry[10].weather, "Downpour")


if __name__ == "__main__":
    unittest.main()
