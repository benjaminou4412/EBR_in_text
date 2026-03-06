"""
Themes C, D, E, F: Challenge effects, location arrival setup, weather flip mechanics,
and moment resolve effects.
Source of truth: JSON rules text and game rules for expected behavior.
"""

import unittest
from ebr.models import (
    GameState, RangerState, Card, Area, Aspect, Approach, CardType,
    ChallengeIcon, CampaignTracker, Keyword
)
from ebr.engine import GameEngine
from ebr.cards import (
    # Woods
    SitkaBuck, SitkaDoe, ProwlingWolhund, OvergrownThicket, SunberryBramble, CausticMulcher,
    # Valley
    CalypsaRangerMentor, QuisiVosRascal, TheFundamentalist,
    # Weather
    APerfectDay, MiddaySun,
    # Location
    LoneTreeStation, BoulderField, AncestorsGrove,
    # Explorer moments
    ShareintheValleysSecrets, AffordedByNature, WalkWithMe, CradledbytheEarth,
    # Other
    PeerlessPathfinder, HyPimpotChef
)
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_engine(path_deck=None, extra_cards=None) -> GameEngine:
    """Create a test engine with configurable path deck and cards in play."""
    role = PeerlessPathfinder()
    location = LoneTreeStation()
    weather = APerfectDay()
    ranger = RangerState(
        name="Test Ranger",
        aspects={Aspect.AWA: 3, Aspect.FIT: 3, Aspect.SPI: 3, Aspect.FOC: 3},
        deck=[Card(id=f"deck-{i}", title=f"Deck Card {i}") for i in range(10)]
    )
    state = GameState(
        ranger=ranger, role_card=role, location=location, weather=weather,
        campaign_tracker=CampaignTracker(day_number=1)
    )
    state.areas[Area.SURROUNDINGS].append(location)
    state.areas[Area.SURROUNDINGS].append(weather)
    if path_deck is not None:
        state.path_deck = path_deck
    if extra_cards:
        for card, area in extra_cards:
            state.areas[area].append(card)
    eng = GameEngine(
        state,
        card_chooser=lambda _e, cards: cards[0],
        response_decider=lambda _e, _p: True,
        order_decider=lambda _e, items, _p: items,
        option_chooser=lambda _e, opts, _p: opts[0],
        amount_chooser=lambda _e, lo, hi, _p: lo
    )
    return eng


# ── Theme C: Challenge effect outcome tests ──────────────────────────────

class APerfectDayMountainEffectTests(unittest.TestCase):
    """JSON: Mountain — if this test added progress, add 1 additional progress."""

    def test_mountain_adds_progress_when_test_added_progress(self):
        target = OvergrownThicket()
        eng = make_engine(extra_cards=[(target, Area.ALONG_THE_WAY)])
        eng.last_test_added_progress = True
        eng.last_test_target = target
        weather = eng.state.weather
        handlers = weather.get_challenge_handlers()
        result = handlers[ChallengeIcon.MOUNTAIN](eng)
        self.assertTrue(result)
        self.assertEqual(target.progress, 1)

    def test_mountain_does_nothing_when_no_progress(self):
        eng = make_engine()
        eng.last_test_added_progress = False
        eng.last_test_target = None
        weather = eng.state.weather
        handlers = weather.get_challenge_handlers()
        result = handlers[ChallengeIcon.MOUNTAIN](eng)
        self.assertFalse(result)


class MiddaySunSunEffectTests(unittest.TestCase):
    """JSON: Sun — suffer 1 fatigue."""

    def test_sun_fatigues_ranger(self):
        card = MiddaySun()
        eng = make_engine(extra_cards=[(card, Area.SURROUNDINGS)])
        initial_deck = len(eng.state.ranger.deck)
        handlers = card.get_challenge_handlers()
        handlers[ChallengeIcon.SUN](eng)
        self.assertEqual(len(eng.state.ranger.deck), initial_deck - 1)


class ProwlingWolhundChallengeEffectTests(unittest.TestCase):
    """JSON: Sun — ready another Prowling Wolhund.
    Crest — if 3+ fatigue, exhaust this being, suffer 1 injury."""

    def test_sun_readies_exhausted_wolhund(self):
        wolhund1 = ProwlingWolhund()
        wolhund2 = ProwlingWolhund()
        wolhund2.exhausted = True
        eng = make_engine(extra_cards=[
            (wolhund1, Area.WITHIN_REACH),
            (wolhund2, Area.WITHIN_REACH)
        ])
        handlers = wolhund1.get_challenge_handlers()
        result = handlers[ChallengeIcon.SUN](eng)
        self.assertTrue(result)
        self.assertFalse(wolhund2.exhausted)

    def test_crest_injures_ranger_at_3_plus_fatigue(self):
        wolhund = ProwlingWolhund()
        eng = make_engine(extra_cards=[(wolhund, Area.WITHIN_REACH)])
        # Give ranger 3+ fatigue
        for i in range(3):
            eng.state.ranger.fatigue_stack.append(Card(id=f"fat-{i}", title=f"F{i}"))
        handlers = wolhund.get_challenge_handlers()
        result = handlers[ChallengeIcon.CREST](eng)
        self.assertTrue(result)
        self.assertTrue(wolhund.exhausted)
        self.assertEqual(eng.state.ranger.injury, 1)

    def test_crest_does_nothing_below_3_fatigue(self):
        wolhund = ProwlingWolhund()
        eng = make_engine(extra_cards=[(wolhund, Area.WITHIN_REACH)])
        # Only 2 fatigue
        for i in range(2):
            eng.state.ranger.fatigue_stack.append(Card(id=f"fat-{i}", title=f"F{i}"))
        handlers = wolhund.get_challenge_handlers()
        result = handlers[ChallengeIcon.CREST](eng)
        self.assertFalse(result)
        self.assertFalse(wolhund.exhausted)


class OvergrownThicketMountainEffectTests(unittest.TestCase):
    """JSON: Mountain — if this feature has 1+ progress, remove 1 progress,
    then suffer fatigue equal to this feature's presence."""

    def test_mountain_removes_progress_and_fatigues(self):
        thicket = OvergrownThicket()
        thicket.progress = 2
        eng = make_engine(extra_cards=[(thicket, Area.ALONG_THE_WAY)])
        initial_deck = len(eng.state.ranger.deck)
        handlers = thicket.get_challenge_handlers()
        result = handlers[ChallengeIcon.MOUNTAIN](eng)
        self.assertTrue(result)
        self.assertEqual(thicket.progress, 1)  # removed 1
        presence = thicket.get_current_presence(eng)
        self.assertEqual(len(eng.state.ranger.deck), initial_deck - presence)

    def test_mountain_does_nothing_at_zero_progress(self):
        thicket = OvergrownThicket()
        eng = make_engine(extra_cards=[(thicket, Area.ALONG_THE_WAY)])
        handlers = thicket.get_challenge_handlers()
        result = handlers[ChallengeIcon.MOUNTAIN](eng)
        self.assertFalse(result)


class AncestorsGroveSunEffectTests(unittest.TestCase):
    """JSON: Sun — choose a card from ranger discard, place on top of fatigue stack."""

    def test_sun_moves_card_from_discard_to_fatigue(self):
        grove = AncestorsGrove()
        eng = make_engine(extra_cards=[(grove, Area.SURROUNDINGS)])
        discard_card = Card(id="disc-1", title="Discarded Card")
        eng.state.ranger.discard.append(discard_card)
        handlers = grove.get_challenge_handlers()
        result = handlers[ChallengeIcon.SUN](eng)
        self.assertTrue(result)
        self.assertNotIn(discard_card, eng.state.ranger.discard)
        self.assertEqual(eng.state.ranger.fatigue_stack[0], discard_card)

    def test_sun_does_nothing_with_empty_discard(self):
        grove = AncestorsGrove()
        eng = make_engine(extra_cards=[(grove, Area.SURROUNDINGS)])
        handlers = grove.get_challenge_handlers()
        result = handlers[ChallengeIcon.SUN](eng)
        self.assertFalse(result)


# ── Theme D: Location arrival setup ──────────────────────────────────────

class LoneTreeStationArrivalTests(unittest.TestCase):
    """JSON: Search path deck for next Predator, discard it. Then draw 1 path card."""

    def test_discards_first_predator(self):
        predator = ProwlingWolhund()
        non_predator = SitkaBuck()
        path_deck = [non_predator, predator]
        eng = make_engine(path_deck=path_deck)
        station = eng.state.location
        station.do_arrival_setup(eng)
        self.assertNotIn(predator, eng.state.path_deck)
        self.assertIn(predator, eng.state.path_discard)

    def test_draws_one_path_card_after_discard(self):
        predator = ProwlingWolhund()
        drawable = SitkaBuck()
        path_deck = [predator, drawable]
        eng = make_engine(path_deck=path_deck)
        station = eng.state.location
        station.do_arrival_setup(eng)
        # Predator discarded, drawable should have been drawn into play
        self.assertNotIn(drawable, eng.state.path_deck)

    def test_no_predator_still_draws(self):
        drawable = SitkaBuck()
        path_deck = [drawable]
        eng = make_engine(path_deck=path_deck)
        station = eng.state.location
        station.do_arrival_setup(eng)
        self.assertNotIn(drawable, eng.state.path_deck)


class AncestorsGroveArrivalTests(unittest.TestCase):
    """JSON: Discard next presence-3 card, then put next Prey into play."""

    def test_discards_presence_3_card(self):
        # Prowling Wolhund has presence 2, not 3. Need a presence-3 card.
        presence_3 = Card(id="p3", title="Presence 3 Card",
                          card_types={CardType.PATH, CardType.BEING}, presence=3,
                          starting_area=Area.WITHIN_REACH)
        prey = SitkaBuck()  # presence 1, is Prey
        path_deck = [presence_3, prey]
        eng = make_engine(path_deck=path_deck)
        grove = AncestorsGrove()
        grove.do_arrival_setup(eng)
        self.assertIn(presence_3, eng.state.path_discard)
        self.assertNotIn(presence_3, eng.state.path_deck)

    def test_puts_prey_into_play(self):
        prey = SitkaBuck()
        path_deck = [prey]
        eng = make_engine(path_deck=path_deck)
        grove = AncestorsGrove()
        grove.do_arrival_setup(eng)
        # Prey should be in play now, not in path deck
        self.assertNotIn(prey, eng.state.path_deck)
        all_in_play = eng.state.all_cards_in_play()
        self.assertIn(prey, all_in_play)


class BoulderFieldArrivalTests(unittest.TestCase):
    """JSON: Draw challenge card. Sun: scout 2+draw 1. Mountain: draw 1. Crest: scout 3+draw 2."""

    def _make_engine_with_challenge(self, icon: ChallengeIcon):
        path_deck = [Card(id=f"path-{i}", title=f"Path {i}",
                          card_types={CardType.PATH, CardType.FEATURE},
                          starting_area=Area.ALONG_THE_WAY)
                     for i in range(5)]
        eng = make_engine(path_deck=path_deck)
        eng.state.challenge_deck = MockChallengeDeck([make_challenge_card(icon)])
        return eng

    def test_mountain_draws_one_path_card(self):
        eng = self._make_engine_with_challenge(ChallengeIcon.MOUNTAIN)
        initial_deck = len(eng.state.path_deck)
        bf = BoulderField()
        bf.do_arrival_setup(eng)
        # Mountain: just draw 1
        self.assertEqual(len(eng.state.path_deck), initial_deck - 1)

    def test_sun_draws_one_path_card(self):
        """Sun: scout 2 then draw 1 — net path deck shrinks by 1 drawn card."""
        eng = self._make_engine_with_challenge(ChallengeIcon.SUN)
        initial_deck = len(eng.state.path_deck)
        bf = BoulderField()
        bf.do_arrival_setup(eng)
        self.assertEqual(len(eng.state.path_deck), initial_deck - 1)

    def test_crest_draws_two_path_cards(self):
        """Crest: scout 3 then draw 2."""
        eng = self._make_engine_with_challenge(ChallengeIcon.CREST)
        initial_deck = len(eng.state.path_deck)
        bf = BoulderField()
        bf.do_arrival_setup(eng)
        self.assertEqual(len(eng.state.path_deck), initial_deck - 2)


class BoulderFieldConstantAbilityTests(unittest.TestCase):
    """JSON: Reduces presence of all beings by 1."""

    def test_reduces_being_presence(self):
        buck = SitkaBuck()  # presence 1
        eng = make_engine(extra_cards=[(buck, Area.WITHIN_REACH)])
        bf = eng.state.location  # LoneTreeStation by default, but let's add BoulderField's ability
        boulder = BoulderField()
        abilities = boulder.get_constant_abilities()
        eng.register_constant_abilities(abilities)
        # SitkaBuck presence=1, minus 1 from BoulderField = max(0, 0)
        effective_presence = buck.get_current_presence(eng)
        self.assertEqual(effective_presence, 0)

    def test_does_not_affect_features(self):
        thicket = OvergrownThicket()  # is a Feature, not a Being
        eng = make_engine(extra_cards=[(thicket, Area.ALONG_THE_WAY)])
        boulder = BoulderField()
        abilities = boulder.get_constant_abilities()
        eng.register_constant_abilities(abilities)
        # Feature should not be affected
        base_presence = thicket.presence
        effective_presence = thicket.get_current_presence(eng)
        self.assertEqual(effective_presence, base_presence)


# ── Theme E: Weather flip mechanics ──────────────────────────────────────

class WeatherFlipTests(unittest.TestCase):
    """Verify weather flips update engine.state.weather correctly."""

    def test_a_perfect_day_flip_updates_state_weather(self):
        eng = make_engine()
        weather = eng.state.weather
        self.assertIsInstance(weather, APerfectDay)
        weather.flip(eng)
        self.assertIsInstance(eng.state.weather, MiddaySun)

    def test_midday_sun_flip_updates_state_weather(self):
        card = MiddaySun()
        eng = make_engine()
        eng.state.weather = card
        eng.state.areas[Area.SURROUNDINGS].append(card)
        card.flip(eng)
        self.assertIsInstance(eng.state.weather, APerfectDay)

    def test_a_perfect_day_refresh_removes_cloud(self):
        """On refresh, A Perfect Day removes 1 cloud."""
        eng = make_engine()
        weather = eng.state.weather
        self.assertIsInstance(weather, APerfectDay)
        initial_clouds = weather.get_unique_token_count("cloud")
        listeners = weather.get_listeners()
        eng.register_listeners(listeners)
        # Simulate refresh tick
        listeners[0].effect_fn(eng, 0)
        self.assertEqual(weather.get_unique_token_count("cloud"), initial_clouds - 1)

    def test_a_perfect_day_flips_at_zero_clouds(self):
        """A Perfect Day flips to Midday Sun when clouds reach 0."""
        eng = make_engine()
        weather = eng.state.weather
        # Set clouds to 1 so next tick reaches 0
        weather.unique_tokens["cloud"] = 1
        listeners = weather.get_listeners()
        listeners[0].effect_fn(eng, 0)
        self.assertIsInstance(eng.state.weather, MiddaySun)

    def test_midday_sun_refresh_adds_cloud(self):
        """On refresh, Midday Sun adds 1 cloud."""
        card = MiddaySun()
        eng = make_engine()
        eng.state.weather = card
        eng.state.areas[Area.SURROUNDINGS].append(card)
        listeners = card.get_listeners()
        initial_clouds = card.get_unique_token_count("cloud")
        listeners[0].effect_fn(eng, 0)
        self.assertEqual(card.get_unique_token_count("cloud"), initial_clouds + 1)

    def test_midday_sun_flips_at_3_clouds(self):
        """Midday Sun flips to A Perfect Day at 3+ clouds."""
        card = MiddaySun()
        eng = make_engine()
        eng.state.weather = card
        eng.state.areas[Area.SURROUNDINGS].append(card)
        # Set to 2 so next tick reaches 3
        card.unique_tokens["cloud"] = 2
        listeners = card.get_listeners()
        listeners[0].effect_fn(eng, 0)
        self.assertIsInstance(eng.state.weather, APerfectDay)


# ── Theme F: Moment resolve effects ───────────────────────────────────

class ShareInTheValleysSecretsMomentTests(unittest.TestCase):
    """JSON: Exhaust each obstacle. Suffer fatigue equal to the number of obstacles exhausted."""

    def test_exhausts_all_obstacles(self):
        card = ShareintheValleysSecrets()
        obstacle1 = OvergrownThicket()  # has Keyword.OBSTACLE
        obstacle2 = OvergrownThicket()
        eng = make_engine(extra_cards=[
            (obstacle1, Area.ALONG_THE_WAY),
            (obstacle2, Area.ALONG_THE_WAY)
        ])
        card.resolve_moment_effect(eng, effort=0, target=None)
        self.assertTrue(obstacle1.is_exhausted())
        self.assertTrue(obstacle2.is_exhausted())

    def test_fatigues_ranger_equal_to_obstacles_exhausted(self):
        card = ShareintheValleysSecrets()
        obstacle1 = OvergrownThicket()
        obstacle2 = OvergrownThicket()
        eng = make_engine(extra_cards=[
            (obstacle1, Area.ALONG_THE_WAY),
            (obstacle2, Area.ALONG_THE_WAY)
        ])
        initial_deck = len(eng.state.ranger.deck)
        card.resolve_moment_effect(eng, effort=0, target=None)
        self.assertEqual(len(eng.state.ranger.deck), initial_deck - 2)

    def test_skips_already_exhausted_obstacles(self):
        card = ShareintheValleysSecrets()
        obstacle = OvergrownThicket()
        obstacle.exhausted = True
        eng = make_engine(extra_cards=[(obstacle, Area.ALONG_THE_WAY)])
        initial_deck = len(eng.state.ranger.deck)
        card.resolve_moment_effect(eng, effort=0, target=None)
        # Already exhausted, so 0 newly exhausted, 0 fatigue
        self.assertEqual(len(eng.state.ranger.deck), initial_deck)

    def test_no_obstacles_means_no_fatigue(self):
        card = ShareintheValleysSecrets()
        eng = make_engine()
        initial_deck = len(eng.state.ranger.deck)
        card.resolve_moment_effect(eng, effort=0, target=None)
        self.assertEqual(len(eng.state.ranger.deck), initial_deck)


class AffordedByNatureMomentTests(unittest.TestCase):
    """JSON: Discard any number of progress from a trail to add equal harm to a being."""

    def test_transfers_progress_to_harm(self):
        card = AffordedByNature()
        trail = OvergrownThicket()  # has trait "trail"
        trail.progress = 3
        being = SitkaBuck()
        eng = make_engine(extra_cards=[
            (trail, Area.ALONG_THE_WAY),
            (being, Area.WITHIN_REACH)
        ])
        # amount_chooser returns lo (0) by default; override to pick all progress
        eng.amount_chooser = lambda _e, lo, hi, _p: hi
        card.resolve_moment_effect(eng, effort=0, target=trail)
        self.assertEqual(trail.progress, 0)
        self.assertEqual(being.harm, 3)

    def test_no_beings_does_not_crash(self):
        card = AffordedByNature()
        trail = OvergrownThicket()
        trail.progress = 2
        eng = make_engine(extra_cards=[(trail, Area.ALONG_THE_WAY)])
        # No beings in play
        card.resolve_moment_effect(eng, effort=0, target=trail)
        # Progress should remain unchanged
        self.assertEqual(trail.progress, 2)

    def test_no_target_does_not_crash(self):
        card = AffordedByNature()
        eng = make_engine()
        card.resolve_moment_effect(eng, effort=0, target=None)


class WalkWithMeMomentTests(unittest.TestCase):
    """JSON: After Traverse success, add progress to a being equal to your effort."""

    def test_adds_progress_equal_to_effort(self):
        card = WalkWithMe()
        being = SitkaBuck()
        eng = make_engine(extra_cards=[(being, Area.WITHIN_REACH)])
        card.resolve_moment_effect(eng, effort=3, target=being)
        self.assertEqual(being.progress, 3)

    def test_no_target_does_not_crash(self):
        card = WalkWithMe()
        eng = make_engine()
        card.resolve_moment_effect(eng, effort=2, target=None)

    def test_zero_effort_adds_no_progress(self):
        card = WalkWithMe()
        being = SitkaBuck()
        eng = make_engine(extra_cards=[(being, Area.WITHIN_REACH)])
        card.resolve_moment_effect(eng, effort=0, target=being)
        self.assertEqual(being.progress, 0)


class CradledByTheEarthMomentTests(unittest.TestCase):
    """JSON: Choose a trail. Soothe fatigue equal to progress on that trail."""

    def test_soothes_fatigue_equal_to_trail_progress(self):
        card = CradledbytheEarth()
        trail = OvergrownThicket()
        trail.progress = 2
        eng = make_engine(extra_cards=[(trail, Area.ALONG_THE_WAY)])
        # Put cards in fatigue stack to be soothed
        for i in range(3):
            eng.state.ranger.fatigue_stack.append(Card(id=f"fat-{i}", title=f"F{i}"))
        initial_hand = len(eng.state.ranger.hand)
        card.resolve_moment_effect(eng, effort=0, target=trail)
        # 2 cards should move from fatigue to hand
        self.assertEqual(len(eng.state.ranger.fatigue_stack), 1)
        self.assertEqual(len(eng.state.ranger.hand), initial_hand + 2)

    def test_no_target_does_not_crash(self):
        card = CradledbytheEarth()
        eng = make_engine()
        card.resolve_moment_effect(eng, effort=0, target=None)

    def test_zero_progress_soothes_nothing(self):
        card = CradledbytheEarth()
        trail = OvergrownThicket()
        trail.progress = 0
        eng = make_engine(extra_cards=[(trail, Area.ALONG_THE_WAY)])
        eng.state.ranger.fatigue_stack.append(Card(id="fat-0", title="F0"))
        card.resolve_moment_effect(eng, effort=0, target=trail)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), 1)


if __name__ == "__main__":
    unittest.main()
