"""
Tests for decks.py — travel destinations, pivotal cards, and registry lookups.
"""

import unittest
from ebr.models import Card, CardType, Mission
from ebr.decks import (
    get_available_travel_destinations, get_pivotal_cards,
    get_current_weather, get_current_missions, get_location_by_id
)
from ebr.cards import (
    LoneTreeStation, BoulderField, AncestorsGrove,
    APerfectDay, Downpour, HowlingWinds,
    HyPimpotChef, BiscuitDelivery
)


# ── Theme 1: Travel destination graph ────────────────────────────────────

class TravelDestinationTests(unittest.TestCase):
    """Verify the triangle graph: LTS ↔ BF ↔ AG ↔ LTS."""

    def test_lone_tree_station_returns_two_destinations(self):
        loc = LoneTreeStation()
        destinations = get_available_travel_destinations(loc)
        self.assertEqual(len(destinations), 2)

    def test_boulder_field_returns_two_destinations(self):
        loc = BoulderField()
        destinations = get_available_travel_destinations(loc)
        self.assertEqual(len(destinations), 2)

    def test_ancestors_grove_returns_two_destinations(self):
        loc = AncestorsGrove()
        destinations = get_available_travel_destinations(loc)
        self.assertEqual(len(destinations), 2)

    def test_lone_tree_station_destinations_are_correct(self):
        loc = LoneTreeStation()
        destinations = get_available_travel_destinations(loc)
        titles = {d.title for d in destinations}
        self.assertEqual(titles, {"Boulder Field", "Ancestor's Grove"})

    def test_boulder_field_destinations_are_correct(self):
        loc = BoulderField()
        destinations = get_available_travel_destinations(loc)
        titles = {d.title for d in destinations}
        self.assertEqual(titles, {"Lone Tree Station", "Ancestor's Grove"})

    def test_ancestors_grove_destinations_are_correct(self):
        loc = AncestorsGrove()
        destinations = get_available_travel_destinations(loc)
        titles = {d.title for d in destinations}
        self.assertEqual(titles, {"Lone Tree Station", "Boulder Field"})

    def test_current_location_excluded(self):
        """Current location should never appear in its own destinations."""
        for loc_class in [LoneTreeStation, BoulderField, AncestorsGrove]:
            with self.subTest(location=loc_class.__name__):
                loc = loc_class()
                destinations = get_available_travel_destinations(loc)
                titles = {d.title for d in destinations}
                self.assertNotIn(loc.title, titles)

    def test_destinations_are_location_cards(self):
        loc = LoneTreeStation()
        destinations = get_available_travel_destinations(loc)
        for dest in destinations:
            with self.subTest(dest=dest.title):
                self.assertTrue(dest.has_type(CardType.LOCATION))


# ── Theme 2: Pivotal set lookup ──────────────────────────────────────────

class PivotalCardsTests(unittest.TestCase):

    def test_lone_tree_station_returns_hy_pimpot_chef(self):
        loc = LoneTreeStation()
        cards = get_pivotal_cards(loc)
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], HyPimpotChef)

    def test_unknown_location_raises(self):
        unknown = Card(title="Unknown Place")
        with self.assertRaises(RuntimeError):
            get_pivotal_cards(unknown)


# ── Theme 3: Weather/mission/location registry lookups ───────────────────

class WeatherRegistryTests(unittest.TestCase):

    def test_a_perfect_day(self):
        card = get_current_weather("A Perfect Day")
        self.assertIsInstance(card, APerfectDay)
        self.assertTrue(card.has_type(CardType.WEATHER))

    def test_downpour(self):
        card = get_current_weather("Downpour")
        self.assertIsInstance(card, Downpour)
        self.assertTrue(card.has_type(CardType.WEATHER))

    def test_howling_winds(self):
        card = get_current_weather("Howling Winds")
        self.assertIsInstance(card, HowlingWinds)
        self.assertTrue(card.has_type(CardType.WEATHER))

    def test_unknown_weather_raises(self):
        with self.assertRaises(RuntimeError):
            get_current_weather("Sunny Skies")


class MissionRegistryTests(unittest.TestCase):

    def test_biscuit_delivery(self):
        missions = [Mission(name="Biscuit Delivery")]
        cards = get_current_missions(missions)
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], BiscuitDelivery)

    def test_unknown_mission_raises(self):
        missions = [Mission(name="Nonexistent Quest")]
        with self.assertRaises(RuntimeError):
            get_current_missions(missions)

    def test_empty_missions_returns_empty(self):
        cards = get_current_missions([])
        self.assertEqual(cards, [])


class LocationRegistryTests(unittest.TestCase):

    def test_lone_tree_station(self):
        card = get_location_by_id("Lone Tree Station")
        self.assertIsInstance(card, LoneTreeStation)
        self.assertTrue(card.has_type(CardType.LOCATION))

    def test_boulder_field(self):
        card = get_location_by_id("Boulder Field")
        self.assertIsInstance(card, BoulderField)
        self.assertTrue(card.has_type(CardType.LOCATION))

    def test_ancestors_grove(self):
        card = get_location_by_id("Ancestor's Grove")
        self.assertIsInstance(card, AncestorsGrove)
        self.assertTrue(card.has_type(CardType.LOCATION))

    def test_unknown_location_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_location_by_id("Narnia")
        self.assertIn("Unknown location ID", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
