"""
Theme A: Card constructor wiring tests.
Verifies keywords, traits, and backside wiring against JSON reference data.
"""

import unittest
from ebr.models import Keyword, CardType
from ebr.cards import (
    # Woods
    SitkaBuck, SitkaDoe, ProwlingWolhund, OvergrownThicket, SunberryBramble, CausticMulcher,
    # Valley
    CalypsaRangerMentor, QuisiVosRascal, TheFundamentalist,
    # Explorer
    WalkWithMe, PeerlessPathfinder, BoundarySensor, ShareintheValleysSecrets,
    CradledbytheEarth, AffordedByNature, Passionate, ADearFriend,
    # Location
    LoneTreeStation, BoulderField, AncestorsGrove,
    # Weather
    APerfectDay, MiddaySun, Downpour, GatheringStorm, HowlingWinds, Thunderhead,
    # Mission
    BiscuitBasket, BiscuitDelivery, HelpingHand, HyPimpotChef
)


class CardKeywordTests(unittest.TestCase):
    """Verify keyword sets match JSON reference data.
    Source of truth: JSON 'keywords' fields in reference files."""

    # Cards WITH keywords (per JSON)
    def test_overgrown_thicket_has_obstacle(self):
        card = OvergrownThicket()
        self.assertIn(Keyword.OBSTACLE, card.keywords)

    def test_calypsa_has_friendly(self):
        card = CalypsaRangerMentor()
        self.assertIn(Keyword.FRIENDLY, card.keywords)

    def test_quisi_vos_has_fatiguing_friendly_persistent(self):
        card = QuisiVosRascal()
        self.assertIn(Keyword.FATIGUING, card.keywords)
        self.assertIn(Keyword.FRIENDLY, card.keywords)
        self.assertIn(Keyword.PERSISTENT, card.keywords)

    def test_the_fundamentalist_has_friendly(self):
        card = TheFundamentalist()
        self.assertIn(Keyword.FRIENDLY, card.keywords)

    def test_hy_pimpot_has_friendly(self):
        card = HyPimpotChef()
        self.assertIn(Keyword.FRIENDLY, card.keywords)

    # Cards WITHOUT keywords (per JSON) — spot check that no spurious keywords crept in
    def test_sitka_buck_no_keywords(self):
        self.assertEqual(SitkaBuck().keywords, set())

    def test_prowling_wolhund_no_keywords(self):
        self.assertEqual(ProwlingWolhund().keywords, set())

    def test_caustic_mulcher_no_keywords(self):
        self.assertEqual(CausticMulcher().keywords, set())

    def test_sunberry_bramble_no_keywords(self):
        self.assertEqual(SunberryBramble().keywords, set())

    def test_a_perfect_day_no_keywords(self):
        self.assertEqual(APerfectDay().keywords, set())

    def test_boundary_sensor_no_keywords(self):
        self.assertEqual(BoundarySensor().keywords, set())


class CardTraitTests(unittest.TestCase):
    """Verify traits match JSON reference data.
    Source of truth: JSON 'traits' fields in reference files."""

    def test_sitka_buck_traits(self):
        """JSON: ["Prey", "Mammal"]"""
        card = SitkaBuck()
        self.assertTrue(card.has_trait("Prey"))
        self.assertTrue(card.has_trait("Mammal"))

    def test_prowling_wolhund_traits(self):
        """JSON: ["Predator", "Mammal"]"""
        card = ProwlingWolhund()
        self.assertTrue(card.has_trait("Predator"))
        self.assertTrue(card.has_trait("Mammal"))

    def test_sitka_doe_traits(self):
        """JSON: ["Prey", "Mammal"]"""
        card = SitkaDoe()
        self.assertTrue(card.has_trait("Prey"))
        self.assertTrue(card.has_trait("Mammal"))

    def test_overgrown_thicket_traits(self):
        """JSON: ["Flora", "Obstacle"]"""
        card = OvergrownThicket()
        self.assertTrue(card.has_trait("Flora"))
        self.assertTrue(card.has_trait("Obstacle"))

    def test_sunberry_bramble_traits(self):
        """JSON: ["Flora", "Food"]"""
        card = SunberryBramble()
        self.assertTrue(card.has_trait("Flora"))
        self.assertTrue(card.has_trait("Food"))

    def test_caustic_mulcher_traits(self):
        """JSON: ["Biomeld"]"""
        card = CausticMulcher()
        self.assertTrue(card.has_trait("Biomeld"))

    def test_calypsa_traits(self):
        """JSON: ["Human", "Ranger"]"""
        card = CalypsaRangerMentor()
        self.assertTrue(card.has_trait("Human"))
        self.assertTrue(card.has_trait("Ranger"))

    def test_quisi_vos_traits(self):
        """JSON: ["Human", "Villager"]"""
        card = QuisiVosRascal()
        self.assertTrue(card.has_trait("Human"))
        self.assertTrue(card.has_trait("Villager"))

    def test_the_fundamentalist_traits(self):
        """JSON: ["Human", "Villager"]"""
        card = TheFundamentalist()
        self.assertTrue(card.has_trait("Human"))
        self.assertTrue(card.has_trait("Villager"))

    def test_hy_pimpot_traits(self):
        """JSON: ["Human", "Ranger"]"""
        card = HyPimpotChef()
        self.assertTrue(card.has_trait("Human"))
        self.assertTrue(card.has_trait("Ranger"))

    def test_walk_with_me_traits(self):
        """JSON: ["Experience"]"""
        card = WalkWithMe()
        self.assertTrue(card.has_trait("Experience"))

    def test_afforded_by_nature_traits(self):
        """JSON: ["Experience", "Weapon"]"""
        card = AffordedByNature()
        self.assertTrue(card.has_trait("Experience"))
        self.assertTrue(card.has_trait("Weapon"))

    def test_a_dear_friend_traits(self):
        """JSON: ["Experience", "Expert"]"""
        card = ADearFriend()
        self.assertTrue(card.has_trait("Experience"))
        self.assertTrue(card.has_trait("Expert"))

    def test_passionate_traits(self):
        """JSON: ["Innate"]"""
        card = Passionate()
        self.assertTrue(card.has_trait("Innate"))

    def test_lone_tree_station_traits(self):
        """JSON: ["Pivotal", "Forest", "Ranger Station"]"""
        card = LoneTreeStation()
        self.assertTrue(card.has_trait("Pivotal"))
        self.assertTrue(card.has_trait("Forest"))
        self.assertTrue(card.has_trait("Ranger Station"))

    def test_boulder_field_traits(self):
        """JSON: ["Field", "Trail"]"""
        card = BoulderField()
        self.assertTrue(card.has_trait("Field"))
        self.assertTrue(card.has_trait("Trail"))

    def test_ancestors_grove_traits(self):
        """JSON: ["Forest", "Trail"]"""
        card = AncestorsGrove()
        self.assertTrue(card.has_trait("Forest"))
        self.assertTrue(card.has_trait("Trail"))

    def test_midday_sun_traits(self):
        """JSON: ["Hot"]"""
        card = MiddaySun()
        self.assertTrue(card.has_trait("Hot"))


class WeatherBacksideWiringTests(unittest.TestCase):
    """Verify weather A↔B pairings match JSON reference data.
    Source of truth: JSON 'flip_to' fields in weather.json."""

    def test_a_perfect_day_backside_is_midday_sun(self):
        card = APerfectDay()
        self.assertIsInstance(card.backside, MiddaySun)

    def test_midday_sun_backside_is_a_perfect_day(self):
        card = MiddaySun()
        self.assertIsInstance(card.backside, APerfectDay)

    def test_downpour_backside_is_gathering_storm(self):
        card = Downpour()
        self.assertIsInstance(card.backside, GatheringStorm)

    def test_gathering_storm_backside_is_downpour(self):
        card = GatheringStorm()
        self.assertIsInstance(card.backside, Downpour)

    def test_howling_winds_backside_is_thunderhead(self):
        card = HowlingWinds()
        self.assertIsInstance(card.backside, Thunderhead)

    def test_thunderhead_backside_is_howling_winds(self):
        card = Thunderhead()
        self.assertIsInstance(card.backside, HowlingWinds)

    def test_biscuit_basket_backside_is_biscuit_delivery(self):
        card = BiscuitBasket()
        self.assertIsInstance(card.backside, BiscuitDelivery)

    def test_biscuit_delivery_backside_is_biscuit_basket(self):
        card = BiscuitDelivery()
        self.assertIsInstance(card.backside, BiscuitBasket)


if __name__ == "__main__":
    unittest.main()
