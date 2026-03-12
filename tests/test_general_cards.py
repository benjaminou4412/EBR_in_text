#type: ignore
"""Tests for General set cards: Cerberusian Cyclone and Ball Lightning."""
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import CerberusianCyclone, BallLightning, LoneTreeStation, APerfectDay
from ebr.cards.explorer_cards import PeerlessPathfinder
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_test_ranger() -> RangerState:
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(10)],
        aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
    )


def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    awa_mod = mod if aspect == Aspect.AWA else 0
    fit_mod = mod if aspect == Aspect.FIT else 0
    spi_mod = mod if aspect == Aspect.SPI else 0
    foc_mod = mod if aspect == Aspect.FOC else 0
    state.challenge_deck = MockChallengeDeck([make_challenge_card(
        icon=symbol, awa=awa_mod, fit=fit_mod, spi=spi_mod, foc=foc_mod
    )])


def make_engine(card: Card, area: Area = Area.ALONG_THE_WAY, **engine_kwargs) -> GameEngine:
    """Build an engine with the given card in play."""
    location = LoneTreeStation()
    weather = APerfectDay()
    role = PeerlessPathfinder()
    ranger = make_test_ranger()
    state = GameState(
        ranger=ranger, role_card=role, location=location, weather=weather,
        campaign_tracker=CampaignTracker(day_number=1),
        areas={
            Area.SURROUNDINGS: [location, weather],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        }
    )
    state.areas[area].append(card)
    defaults = dict(
        card_chooser=lambda _e, cards: cards[0],
        response_decider=lambda _e, _p: True,
        order_decider=lambda _e, items, _p: items,
        option_chooser=lambda _e, opts, _p: opts[0],
        amount_chooser=lambda _e, lo, hi, _p: lo,
    )
    defaults.update(engine_kwargs)
    return GameEngine(state, **defaults)


# ─── Cerberusian Cyclone ───────────────────────────────────────────


class TestCycloneEntersPlay(unittest.TestCase):
    """Cyclone enters along the way with 3 strength tokens."""

    def test_enters_with_3_strength(self):
        cyclone = CerberusianCyclone()
        eng = make_engine(cyclone, Area.ALONG_THE_WAY)
        cyclone.enters_play(eng, Area.ALONG_THE_WAY)
        self.assertEqual(cyclone.unique_tokens.get("strength", 0), 3)

    def test_starting_area_is_along_the_way(self):
        cyclone = CerberusianCyclone()
        self.assertEqual(cyclone.starting_area, Area.ALONG_THE_WAY)


class TestCycloneEvadeTest(unittest.TestCase):
    """AWA + Conflict Evade [2]: discard 1 strength per 2 effort."""

    def _setup(self, hand_icons: int = 1):
        cyclone = CerberusianCyclone()
        hand_card = Card(id="hand0", title="Hand Card",
                         approach_icons={Approach.CONFLICT: hand_icons})
        ranger = make_test_ranger()
        ranger.hand = [hand_card]
        location = LoneTreeStation()
        weather = APerfectDay()
        role = PeerlessPathfinder()
        state = GameState(
            ranger=ranger, role_card=role, location=location, weather=weather,
            campaign_tracker=CampaignTracker(day_number=1),
            areas={
                Area.SURROUNDINGS: [location, weather],
                Area.ALONG_THE_WAY: [cyclone],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        cyclone.enters_play(GameEngine(state), Area.ALONG_THE_WAY)
        eng = GameEngine(state,
                         option_chooser=lambda _e, opts, _p: opts[0],
                         order_decider=lambda _e, items, _p: items)
        return cyclone, eng, state

    def test_evade_test_fields(self):
        cyclone = CerberusianCyclone()
        tests = cyclone.get_tests()
        self.assertEqual(len(tests), 1)
        t = tests[0]
        self.assertEqual(t.aspect, Aspect.AWA)
        self.assertEqual(t.approach, Approach.CONFLICT)
        self.assertEqual(t.verb, "Evade")

    def test_evade_removes_strength_on_success(self):
        """Effort 2 → removes 1 strength (2//2=1). 3→2 strength."""
        cyclone, eng, state = self._setup(hand_icons=1)
        # energy(1) + 1 icon = 2 effort, +0 mod = 2 >= difficulty 2 → success
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        tests = cyclone.get_tests()
        evade = tests[0]
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(evade, decision, cyclone.id)
        self.assertEqual(cyclone.unique_tokens["strength"], 2)
        self.assertIn(cyclone, state.areas[Area.ALONG_THE_WAY])

    def test_evade_high_effort_removes_multiple_strength(self):
        """Effort 4 → removes 2 strength (4//2=2). 3→1 strength."""
        cyclone, eng, state = self._setup(hand_icons=3)
        # energy(1) + 3 icons = 4 effort
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        tests = cyclone.get_tests()
        evade = tests[0]
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(evade, decision, cyclone.id)
        self.assertEqual(cyclone.unique_tokens["strength"], 1)

    def test_evade_removes_all_strength_discards_cyclone(self):
        """If all strength is removed, the cyclone discards itself."""
        cyclone, eng, state = self._setup(hand_icons=5)
        # energy(1) + 5 icons = 6 effort → removes 3 strength, cyclone has 3 → discards
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)
        tests = cyclone.get_tests()
        evade = tests[0]
        decision = CommitDecision(energy=1, hand_indices=[0])
        eng.perform_test(evade, decision, cyclone.id)
        self.assertNotIn(cyclone, state.areas[Area.ALONG_THE_WAY])


class TestCycloneMountainEffect(unittest.TestCase):
    """Mountain: Move this feature. If destination has no other cards, +1 strength."""

    def test_move_to_empty_area_adds_strength(self):
        cyclone = CerberusianCyclone()
        # Option chooser picks "Within Reach" (which will be empty)
        eng = make_engine(cyclone, Area.ALONG_THE_WAY,
                          option_chooser=lambda _e, opts, _p: "Within Reach")
        cyclone.enters_play(eng, Area.ALONG_THE_WAY)
        initial_strength = cyclone.unique_tokens.get("strength", 0)
        cyclone._mountain_effect(eng)
        self.assertIn(cyclone, eng.state.areas[Area.WITHIN_REACH])
        self.assertEqual(cyclone.unique_tokens["strength"], initial_strength + 1)

    def test_move_to_occupied_area_no_extra_strength(self):
        cyclone = CerberusianCyclone()
        eng = make_engine(cyclone, Area.ALONG_THE_WAY,
                          option_chooser=lambda _e, opts, _p: "Surroundings")
        cyclone.enters_play(eng, Area.ALONG_THE_WAY)
        initial_strength = cyclone.unique_tokens.get("strength", 0)
        # Surroundings has location + weather, so it's occupied
        cyclone._mountain_effect(eng)
        self.assertIn(cyclone, eng.state.areas[Area.SURROUNDINGS])
        self.assertEqual(cyclone.unique_tokens["strength"], initial_strength)


class TestCycloneCrestEffect(unittest.TestCase):
    """Crest: Move a card in the same area. Fatigue ranger if moved within reach."""

    def test_move_card_within_reach_fatigues_ranger(self):
        cyclone = CerberusianCyclone()
        victim = Card(id="victim", title="Victim Being", card_types={CardType.PATH, CardType.BEING}, presence=2)
        eng = make_engine(cyclone, Area.ALONG_THE_WAY,
                          option_chooser=lambda _e, opts, _p: "Within Reach")
        eng.state.areas[Area.ALONG_THE_WAY].append(victim)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        cyclone._crest_effect(eng)
        self.assertIn(victim, eng.state.areas[Area.WITHIN_REACH])
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 2)

    def test_move_card_not_within_reach_no_fatigue(self):
        cyclone = CerberusianCyclone()
        victim = Card(id="victim", title="Victim Being", card_types={CardType.PATH, CardType.BEING}, presence=2)
        eng = make_engine(cyclone, Area.ALONG_THE_WAY,
                          option_chooser=lambda _e, opts, _p: "Surroundings")
        eng.state.areas[Area.ALONG_THE_WAY].append(victim)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        cyclone._crest_effect(eng)
        self.assertIn(victim, eng.state.areas[Area.SURROUNDINGS])
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue)

    def test_no_other_cards_returns_false(self):
        cyclone = CerberusianCyclone()
        eng = make_engine(cyclone, Area.WITHIN_REACH)
        # Within Reach has only the cyclone
        result = cyclone._crest_effect(eng)
        self.assertFalse(result)


class TestCycloneNeverClears(unittest.TestCase):
    """Cyclone has no harm or progress thresholds, so it should never clear."""

    def test_no_progress_clear(self):
        cyclone = CerberusianCyclone()
        self.assertIsNone(cyclone.progress_threshold)
        cyclone.progress = 100
        state = GameState(ranger=make_test_ranger())
        self.assertIsNone(cyclone.clear_if_threshold(state))

    def test_no_harm_clear(self):
        cyclone = CerberusianCyclone()
        self.assertIsNone(cyclone.harm_threshold)
        cyclone.harm = 100
        state = GameState(ranger=make_test_ranger())
        self.assertIsNone(cyclone.clear_if_threshold(state))


# ─── Ball Lightning ────────────────────────────────────────────────


class TestBallLightningAmbush(unittest.TestCase):
    """Ball Lightning has Ambush and presence 1. Fatigues on enters_play and move_card."""

    def test_has_ambush_keyword(self):
        bl = BallLightning()
        self.assertTrue(bl.has_keyword(Keyword.AMBUSH))

    def test_ambush_fatigues_on_enters_play(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        bl.enters_play(eng, Area.WITHIN_REACH)
        # Presence is 1, so should fatigue for 1
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)

    def test_ambush_fatigues_on_move_within_reach(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.ALONG_THE_WAY)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        eng.move_card(bl.id, Area.WITHIN_REACH)
        # Ambush triggers on move_card to Within Reach
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue + 1)

    def test_no_ambush_fatigue_on_move_elsewhere(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)
        eng.move_card(bl.id, Area.ALONG_THE_WAY)
        self.assertEqual(len(eng.state.ranger.fatigue_stack), initial_fatigue)


class TestBallLightningHarmClear(unittest.TestCase):
    """Clear [harm]: within reach → 2 injuries; along the way → remove location progress."""

    def test_harm_clear_within_reach_causes_2_injuries(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH)
        initial_injury = eng.state.ranger.injury
        bl.harm = 3  # at threshold
        eng.check_and_process_clears()
        self.assertEqual(eng.state.ranger.injury, initial_injury + 2)
        # Ball Lightning should be discarded
        self.assertNotIn(bl, eng.state.areas[Area.WITHIN_REACH])

    def test_harm_clear_along_the_way_removes_location_progress(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.ALONG_THE_WAY)
        eng.state.location.progress = 5
        bl.harm = 3  # at threshold
        eng.check_and_process_clears()
        self.assertEqual(eng.state.location.progress, 0)
        self.assertNotIn(bl, eng.state.areas[Area.ALONG_THE_WAY])

    def test_harm_clear_along_the_way_no_progress_is_fine(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.ALONG_THE_WAY)
        eng.state.location.progress = 0
        bl.harm = 3
        eng.check_and_process_clears()
        # Should not crash, just message
        self.assertNotIn(bl, eng.state.areas[Area.ALONG_THE_WAY])

    def test_harm_clear_in_surroundings_no_special_effect(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.SURROUNDINGS)
        eng.state.location.progress = 5
        initial_injury = eng.state.ranger.injury
        bl.harm = 3
        eng.check_and_process_clears()
        # No injuries and location progress untouched
        self.assertEqual(eng.state.ranger.injury, initial_injury)
        self.assertEqual(eng.state.location.progress, 5)


class TestBallLightningSunEffect(unittest.TestCase):
    """Sun: Move this feature."""

    def test_sun_moves_ball_lightning(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH,
                          option_chooser=lambda _e, opts, _p: "Along the Way")
        result = bl._sun_effect(eng)
        self.assertTrue(result)
        self.assertIn(bl, eng.state.areas[Area.ALONG_THE_WAY])
        self.assertNotIn(bl, eng.state.areas[Area.WITHIN_REACH])


class TestBallLightningCrestEffect(unittest.TestCase):
    """Crest: Add 1 harm to this feature."""

    def test_crest_adds_harm(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH)
        initial_harm = bl.harm
        bl._crest_effect(eng)
        self.assertEqual(bl.harm, initial_harm + 1)

    def test_crest_accumulates_to_threshold_triggers_clear(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.ALONG_THE_WAY)
        bl.harm = 2  # one more will hit threshold of 3
        bl._crest_effect(eng)
        self.assertEqual(bl.harm, 3)
        # check_and_process_clears should now clear it
        eng.check_and_process_clears()
        self.assertNotIn(bl, eng.state.areas[Area.ALONG_THE_WAY])


class TestBallLightningNoProgressClear(unittest.TestCase):
    """Ball Lightning has no progress threshold; it should never clear by progress."""

    def test_no_progress_threshold(self):
        bl = BallLightning()
        self.assertIsNone(bl.progress_threshold)

    def test_adding_progress_never_clears(self):
        bl = BallLightning()
        eng = make_engine(bl, Area.WITHIN_REACH)
        bl.progress = 100
        state = eng.state
        self.assertIsNone(bl.clear_if_threshold(state))
        cleared = eng.check_and_process_clears()
        self.assertNotIn(bl, cleared)
        self.assertIn(bl, state.areas[Area.WITHIN_REACH])


if __name__ == '__main__':
    unittest.main()
