"""
Tests for card discard mechanics
"""

import unittest
from ebr.models import *
from ebr.engine import GameEngine
from tests.test_utils import MockChallengeDeck, make_challenge_card
from ebr.cards.woods_cards import *


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

class DiscardFromPlayTests(unittest.TestCase):
    """Tests for Card.discard_from_play() method"""

    def test_discard_path_card_from_zone(self):
        """Path cards should go to path_discard when discarded"""
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

        # Discard the thicket
        msg = thicket.discard_from_play(eng)

        # Assertions
        self.assertIn("discarded", msg.lower())
        self.assertNotIn(thicket, state.areas[Area.ALONG_THE_WAY])
        self.assertIn(thicket, state.path_discard)

    def test_discard_ranger_card_from_zone(self):
        """Ranger cards should go to ranger.discard when discarded"""
        # Create a ranger card in a zone (unusual but possible for some card types)
        ranger_card = Card(
            id="test-ranger-card",
            title="Test Ranger Card",
            card_types={CardType.RANGER, CardType.GEAR}
        )

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [ranger_card],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Discard the ranger card
        msg = ranger_card.discard_from_play(eng)

        # Assertions
        self.assertIn("discarded", msg.lower())
        self.assertNotIn(ranger_card, state.areas[Area.PLAYER_AREA])
        self.assertIn(ranger_card, state.ranger.discard)
        self.assertNotIn(ranger_card, state.path_discard)

    def test_discard_card_from_multiple_zones(self):
        """Discard should work regardless of which zone card is in"""
        for zone in [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH]:
            bramble = SunberryBramble()
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
            state.areas[zone].append(bramble)
            stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

            eng = GameEngine(state)

            # Discard the bramble
            bramble.discard_from_play(eng)

            # Assertions
            self.assertNotIn(bramble, state.areas[zone], f"Failed for zone {zone}")
            self.assertIn(bramble, state.path_discard, f"Failed for zone {zone}")


class ClearingTests(unittest.TestCase):
    """Tests for card clearing mechanics"""

    def test_card_clears_at_progress_threshold(self):
        """Cards should clear when reaching progress threshold"""
        thicket = OvergrownThicket()
        thicket.progress = 2  # Threshold is 2

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

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 1)
        self.assertIn(thicket, cleared)
        self.assertNotIn(thicket, state.areas[Area.ALONG_THE_WAY])
        self.assertIn(thicket, state.path_discard)

    def test_card_clears_at_harm_threshold(self):
        """Cards should clear when reaching harm threshold"""
        bramble = SunberryBramble()
        bramble.harm = 2  # Threshold is 2

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
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 1)
        self.assertIn(bramble, cleared)
        self.assertNotIn(bramble, state.areas[Area.WITHIN_REACH])
        self.assertIn(bramble, state.path_discard)

    def test_card_doesnt_clear_below_threshold(self):
        """Cards should not clear when below threshold"""
        thicket = OvergrownThicket()
        thicket.progress = 1  # Threshold is 2

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

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 0)
        self.assertIn(thicket, state.areas[Area.ALONG_THE_WAY])
        self.assertNotIn(thicket, state.path_discard)

    def test_multiple_cards_clear_simultaneously(self):
        """Multiple cards can clear in the same check"""
        thicket = OvergrownThicket()
        thicket.progress = 2

        bramble = SunberryBramble()
        bramble.harm = 2

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [thicket],
                Area.WITHIN_REACH: [bramble],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 2)
        self.assertIn(thicket, cleared)
        self.assertIn(bramble, cleared)
        self.assertNotIn(thicket, state.areas[Area.ALONG_THE_WAY])
        self.assertNotIn(bramble, state.areas[Area.WITHIN_REACH])
        self.assertIn(thicket, state.path_discard)
        self.assertIn(bramble, state.path_discard)


class SeparationOfClearAndDiscardTests(unittest.TestCase):
    """Tests verifying that clearing and discarding are properly separated"""

    def test_clearing_calls_discard_by_default(self):
        """By default, clearing a card should discard it"""
        thicket = OvergrownThicket()
        thicket.progress = 2

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

        # Process clears
        eng.check_and_process_clears()

        # Card should have been discarded
        self.assertIn(thicket, state.path_discard)

    def test_can_discard_without_clearing(self):
        """Cards can be discarded directly without clearing"""
        buck = SitkaBuck()
        buck.progress = 0  # Not at threshold

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
        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)

        eng = GameEngine(state)

        # Directly discard (simulating some effect that discards without clearing)
        buck.discard_from_play(eng)

        # Card should be discarded even though it didn't clear
        self.assertNotIn(buck, state.areas[Area.WITHIN_REACH])
        self.assertIn(buck, state.path_discard)


if __name__ == '__main__':
    unittest.main()
