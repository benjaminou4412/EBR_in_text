#type: ignore
"""
Comprehensive tests for Woods terrain set card behaviors
"""


import unittest
from src.models import *
from src.engine import GameEngine
from tests.test_utils import MockChallengeDeck, make_challenge_card
from src.cards.woods_cards import *


def fixed_draw(mod: int, sym: ChallengeIcon):
    """Helper to create fixed challenge draws for testing"""
    return lambda: (mod, sym)




def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    """Helper to stack the challenge deck with a single predetermined card."""
    # Build mods based on which aspect is being tested
    awa_mod = mod if aspect == Aspect.AWA else 0
    fit_mod = mod if aspect == Aspect.FIT else 0
    spi_mod = mod if aspect == Aspect.SPI else 0
    foc_mod = mod if aspect == Aspect.FOC else 0

    state.challenge_deck = MockChallengeDeck([make_challenge_card(
        icon=symbol,
        awa=awa_mod,
        fit=fit_mod,
        spi=spi_mod,
        foc=foc_mod
    )])

class ProwlingWolhundTests(unittest.TestCase):
    """Tests for Prowling Wolhund card"""

    def test_enters_play_with_no_other_predators(self):
        """Prowling Wolhund should enter play ready if no other predators exist"""
        wolhund = ProwlingWolhund()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Manually call enters_play
        wolhund.enters_play(eng, Area.WITHIN_REACH, None)

        # Should NOT be exhausted
        self.assertFalse(wolhund.exhausted)

    def test_enters_play_with_another_predator(self):
        """Prowling Wolhund should enter play exhausted if another predator exists"""
        wolhund1 = ProwlingWolhund()
        wolhund2 = ProwlingWolhund()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund1],  # First predator already in play
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Second wolhund enters play
        wolhund2.enters_play(eng, Area.WITHIN_REACH, None)

        # Second wolhund should be exhausted
        self.assertTrue(wolhund2.exhausted)
        # First wolhund should still be ready
        self.assertFalse(wolhund1.exhausted)

    def test_sun_effect_ready_another_wolhund(self):
        """Sun effect should ready an exhausted Prowling Wolhund"""
        wolhund1 = ProwlingWolhund()
        wolhund2 = ProwlingWolhund()
        wolhund2.exhausted = True  # Second is exhausted

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund1, wolhund2],
                Area.PLAYER_AREA: [],
            }
        )

        # Mock card chooser to always pick wolhund2
        def mock_chooser(engine, cards):
            return wolhund2

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        # Trigger sun effect
        handlers = wolhund1.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved)
        self.assertFalse(wolhund2.exhausted)

    def test_sun_effect_no_other_wolhunds(self):
        """Sun effect should not resolve if no other Wolhunds exist"""
        wolhund = ProwlingWolhund()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = wolhund.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved)

    def test_sun_effect_all_other_wolhunds_ready(self):
        """Sun effect should not resolve if all other Wolhunds are already ready"""
        wolhund1 = ProwlingWolhund()
        wolhund2 = ProwlingWolhund()
        wolhund2.exhausted = False  # Already ready

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund1, wolhund2],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = wolhund1.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved)

    def test_crest_effect_with_low_fatigue(self):
        """Crest effect should not resolve with less than 3 fatigue"""
        wolhund = ProwlingWolhund()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Only 2 fatigue
        ranger.fatigue_stack = [
            Card(id="f1", title="Fatigue 1"),
            Card(id="f2", title="Fatigue 2")
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        handlers = wolhund.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved)
        self.assertFalse(wolhund.exhausted)
        self.assertEqual(ranger.injury, 0)

    def test_crest_effect_with_high_fatigue(self):
        """Crest effect should resolve with 3+ fatigue, exhausting wolhund and injuring ranger"""
        wolhund = ProwlingWolhund()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # 3 fatigue
        ranger.fatigue_stack = [
            Card(id="f1", title="Fatigue 1"),
            Card(id="f2", title="Fatigue 2"),
            Card(id="f3", title="Fatigue 3")
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [wolhund],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        handlers = wolhund.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertTrue(resolved)
        self.assertTrue(wolhund.exhausted)
        self.assertEqual(ranger.injury, 1)
        self.assertEqual(len(ranger.fatigue_stack), 0)  # Fatigue discarded by injury
        self.assertEqual(len(ranger.discard), 3)  # Fatigue moved to discard


class SitkaBuckTests(unittest.TestCase):
    """Tests for Sitka Buck card"""

    def test_sun_effect_harms_both_bucks(self):
        """Sun effect should exhaust this buck and add 2 harm to both bucks"""
        buck1 = SitkaBuck()
        buck2 = SitkaBuck()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck1, buck2],
                Area.PLAYER_AREA: [],
            }
        )

        def mock_chooser(engine, cards):
            return buck2

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        handlers = buck1.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved)
        self.assertTrue(buck1.exhausted)
        self.assertEqual(buck1.harm, 2)
        self.assertEqual(buck2.harm, 2)

    def test_sun_effect_no_other_active_bucks(self):
        """Sun effect should not resolve if no other ACTIVE bucks exist"""
        buck1 = SitkaBuck()
        buck2 = SitkaBuck()
        buck2.exhausted = True  # Other buck is exhausted

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck1, buck2],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = buck1.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved)
        self.assertFalse(buck1.exhausted)
        self.assertEqual(buck1.harm, 0)

    def test_mountain_effect_harms_predator_and_buck(self):
        """Mountain effect should exhaust predator, add 2 harm to it, then harm buck by predator's presence"""
        buck = SitkaBuck()
        wolhund = ProwlingWolhund()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck, wolhund],
                Area.PLAYER_AREA: [],
            }
        )

        def mock_chooser(engine, cards):
            return wolhund

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        handlers = buck.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(resolved)
        self.assertTrue(wolhund.exhausted)
        self.assertEqual(wolhund.harm, 2)
        self.assertEqual(buck.harm, 2)  # Wolhund has presence 2

    def test_mountain_effect_no_predators(self):
        """Mountain effect should not resolve if no predators exist"""
        buck = SitkaBuck()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        handlers = buck.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertFalse(resolved)

    def test_crest_effect_with_active_doe(self):
        """Crest effect should injure ranger if active Sitka Doe exists"""
        buck = SitkaBuck()
        doe = SitkaDoe()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck, doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        handlers = buck.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertTrue(resolved)
        self.assertEqual(ranger.injury, 1)

    def test_crest_effect_no_active_doe(self):
        """Crest effect should not resolve if no active doe exists"""
        buck = SitkaBuck()
        doe = SitkaDoe()
        doe.exhausted = True  # Doe is exhausted

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck, doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        handlers = buck.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved)
        self.assertEqual(ranger.injury, 0)


class SitkaDoeTests(unittest.TestCase):
    """Tests for Sitka Doe card"""

    def test_spook_test_moves_doe(self):
        """Spook test should move doe to Along the Way"""
        doe = SitkaDoe()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.SPI, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Manually invoke on_success
        doe._on_spook_success(eng, 1, None)

        # Doe should have moved
        self.assertNotIn(doe, state.areas[Area.WITHIN_REACH])
        self.assertIn(doe, state.areas[Area.ALONG_THE_WAY])

    def test_sun_effect_moves_all_bucks(self):
        """Sun effect should move all bucks to Within Reach"""
        doe = SitkaDoe()
        buck1 = SitkaBuck()
        buck2 = SitkaBuck()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [buck1],
                Area.ALONG_THE_WAY: [buck2],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = doe.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved)
        # Both bucks should be Within Reach
        self.assertIn(buck1, state.areas[Area.WITHIN_REACH])
        self.assertIn(buck2, state.areas[Area.WITHIN_REACH])

    def test_sun_effect_no_bucks(self):
        """Sun effect should not resolve if no bucks exist"""
        doe = SitkaDoe()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = doe.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved)

    def test_sun_effect_bucks_already_within_reach(self):
        """Sun effect should not resolve if all bucks are already Within Reach"""
        doe = SitkaDoe()
        buck = SitkaBuck()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe, buck],  # Buck already here
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = doe.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved)  # No actual movement occurred

    def test_mountain_effect_harm_from_predator(self):
        """Mountain effect should harm doe equal to predator's presence"""
        doe = SitkaDoe()
        wolhund = ProwlingWolhund()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe, wolhund],
                Area.PLAYER_AREA: [],
            }
        )

        def mock_chooser(engine, cards):
            return wolhund

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        handlers = doe.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(resolved)
        self.assertTrue(wolhund.exhausted)
        self.assertEqual(doe.harm, 2)  # Wolhund has presence 2


class SunberryBrambleTests(unittest.TestCase):
    """Tests for Sunberry Bramble card"""

    def test_pluck_test_success_adds_harm_and_soothes(self):
        """Pluck test success should add 1 harm to bramble and soothe 2 fatigue"""
        bramble = SunberryBramble()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Add some fatigue
        ranger.fatigue_stack = [
            Card(id="f1", title="Fatigue 1"),
            Card(id="f2", title="Fatigue 2"),
            Card(id="f3", title="Fatigue 3")
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [bramble],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Invoke on_success
        bramble._on_pluck_success(eng, 2, None)

        self.assertEqual(bramble.harm, 1)
        self.assertEqual(len(ranger.fatigue_stack), 1)  # 2 soothed
        self.assertEqual(len(ranger.hand), 2)  # 2 moved to hand

    def test_pluck_test_fail_fatigues_ranger(self):
        """Pluck test fail should fatigue ranger by bramble's presence"""
        bramble = SunberryBramble()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.deck = [
            Card(id="d1", title="Deck 1"),
            Card(id="d2", title="Deck 2"),
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [bramble],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Invoke fail effect
        bramble._fail_effect(eng, 0, None)

        self.assertEqual(len(ranger.fatigue_stack), 1)  # Presence is 1
        self.assertEqual(len(ranger.deck), 1)

    def test_mountain_effect_with_active_prey(self):
        """Mountain effect should exhaust prey and add progress/harm equal to prey's presence"""
        bramble = SunberryBramble()
        buck = SitkaBuck()  # Prey with presence 1

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [bramble, buck],
                Area.PLAYER_AREA: [],
            }
        )

        def mock_chooser(engine, cards):
            return buck

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        handlers = bramble.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(resolved)
        self.assertTrue(buck.exhausted)
        self.assertEqual(buck.progress, 1)  # Buck gets progress
        self.assertEqual(bramble.harm, 1)  # Bramble gets harm

    def test_mountain_effect_no_prey(self):
        """Mountain effect should not resolve if no prey exists"""
        bramble = SunberryBramble()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [bramble],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        handlers = bramble.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertFalse(resolved)


class OvergrownThicketTests(unittest.TestCase):
    """Tests for Overgrown Thicket card"""

    def test_hunt_test_adds_progress(self):
        """Hunt test should add progress equal to effort"""
        thicket = OvergrownThicket()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Invoke on_success with 3 effort
        thicket._on_hunt_success(eng, 3, None)

        self.assertEqual(thicket.progress, 3)

    def test_mountain_effect_discards_progress_and_fatigues(self):
        """Mountain effect should discard 1 progress and fatigue ranger"""
        thicket = OvergrownThicket()
        thicket.progress = 2  # Has some progress

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        ranger.deck = [
            Card(id="d1", title="Deck 1"),
            Card(id="d2", title="Deck 2"),
        ]

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        handlers = thicket.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(resolved)
        self.assertEqual(thicket.progress, 1)  # 1 progress removed
        self.assertEqual(len(ranger.fatigue_stack), 1)  # Fatigued by presence (1)
        self.assertEqual(len(ranger.deck), 1)

    def test_mountain_effect_no_progress(self):
        """Mountain effect should not resolve if thicket has no progress"""
        thicket = OvergrownThicket()
        thicket.progress = 0

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        handlers = thicket.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertFalse(resolved)

    def test_obstacle_keyword_set(self):
        """Thicket should have Obstacle keyword"""
        thicket = OvergrownThicket()
        self.assertIn(Keyword.OBSTACLE, thicket.keywords)


class WoodsCardInteractionTests(unittest.TestCase):
    """Tests for interactions between multiple Woods cards"""

    def test_multiple_wolhunds_entering_play(self):
        """Test cascading exhaustion when multiple Prowling Wolhunds enter play"""
        wolhund1 = ProwlingWolhund()
        wolhund2 = ProwlingWolhund()
        wolhund3 = ProwlingWolhund()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # First wolhund enters play
        state.areas[Area.WITHIN_REACH].append(wolhund1)
        wolhund1.enters_play(eng, Area.WITHIN_REACH, None)
        self.assertFalse(wolhund1.exhausted)

        # Second wolhund enters play
        state.areas[Area.WITHIN_REACH].append(wolhund2)
        wolhund2.enters_play(eng, Area.WITHIN_REACH, None)
        self.assertTrue(wolhund2.exhausted)

        # Third wolhund enters play
        state.areas[Area.WITHIN_REACH].append(wolhund3)
        wolhund3.enters_play(eng, Area.WITHIN_REACH, None)
        self.assertTrue(wolhund3.exhausted)

    def test_buck_and_doe_interaction(self):
        """Test that bucks move to doe when sun effect triggers"""
        doe = SitkaDoe()
        buck1 = SitkaBuck()
        buck2 = SitkaBuck()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [buck1, buck2],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        handlers = doe.get_challenge_handlers()
        handlers[ChallengeIcon.SUN](eng)

        # Both bucks should be Within Reach with doe
        self.assertIn(buck1, state.areas[Area.WITHIN_REACH])
        self.assertIn(buck2, state.areas[Area.WITHIN_REACH])

    def test_buck_crest_with_exhausted_doe(self):
        """Test that buck's crest effect doesn't trigger with exhausted doe"""
        buck = SitkaBuck()
        doe = SitkaDoe()
        doe.exhausted = True

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck, doe],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        handlers = buck.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved)
        self.assertEqual(ranger.injury, 0)

    def test_wolhund_hunts_prey(self):
        """Test that Wolhund (predator) can be exhausted by buck's mountain effect"""
        buck = SitkaBuck()
        wolhund = ProwlingWolhund()

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [buck, wolhund],
                Area.PLAYER_AREA: [],
            }
        )

        def mock_chooser(engine, cards):
            return wolhund

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)


        eng = GameEngine(state, card_chooser=mock_chooser)

        handlers = buck.get_challenge_handlers()
        handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(wolhund.exhausted)
        self.assertEqual(wolhund.harm, 2)
        self.assertEqual(buck.harm, 2)  # Buck takes harm from wolhund's presence


if __name__ == '__main__':
    unittest.main()
