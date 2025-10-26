"""
Tests for card discard mechanics
"""

import unittest
from src.models import *
from src.engine import GameEngine
from src.cards.woods_cards import *


def fixed_draw(mod: int, sym: ChallengeIcon):
    """Helper to create fixed challenge draws for testing"""
    return lambda: (mod, sym)


class DiscardFromPlayTests(unittest.TestCase):
    """Tests for Card.discard_from_play() method"""

    def test_discard_path_card_from_zone(self):
        """Path cards should go to path_discard when discarded"""
        thicket = OvergrownThicket()
        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Discard the thicket
        msg = thicket.discard_from_play(eng)

        # Assertions
        self.assertIn("discarded", msg.lower())
        self.assertNotIn(thicket, state.zones[Zone.ALONG_THE_WAY])
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
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [ranger_card],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Discard the ranger card
        msg = ranger_card.discard_from_play(eng)

        # Assertions
        self.assertIn("discarded", msg.lower())
        self.assertNotIn(ranger_card, state.zones[Zone.PLAYER_AREA])
        self.assertIn(ranger_card, state.ranger.discard)
        self.assertNotIn(ranger_card, state.path_discard)

    def test_discard_card_from_multiple_zones(self):
        """Discard should work regardless of which zone card is in"""
        for zone in [Zone.SURROUNDINGS, Zone.ALONG_THE_WAY, Zone.WITHIN_REACH]:
            bramble = SunberryBramble()
            ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
            state = GameState(
                ranger=ranger,
                zones={
                    Zone.SURROUNDINGS: [],
                    Zone.ALONG_THE_WAY: [],
                    Zone.WITHIN_REACH: [],
                    Zone.PLAYER_AREA: [],
                }
            )
            state.zones[zone].append(bramble)
            eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

            # Discard the bramble
            bramble.discard_from_play(eng)

            # Assertions
            self.assertNotIn(bramble, state.zones[zone], f"Failed for zone {zone}")
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
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 1)
        self.assertIn(thicket, cleared)
        self.assertNotIn(thicket, state.zones[Zone.ALONG_THE_WAY])
        self.assertIn(thicket, state.path_discard)

    def test_card_clears_at_harm_threshold(self):
        """Cards should clear when reaching harm threshold"""
        bramble = SunberryBramble()
        bramble.harm = 2  # Threshold is 2

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [bramble],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 1)
        self.assertIn(bramble, cleared)
        self.assertNotIn(bramble, state.zones[Zone.WITHIN_REACH])
        self.assertIn(bramble, state.path_discard)

    def test_card_doesnt_clear_below_threshold(self):
        """Cards should not clear when below threshold"""
        thicket = OvergrownThicket()
        thicket.progress = 1  # Threshold is 2

        ranger = RangerState(name="Ranger", aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(
            ranger=ranger,
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 0)
        self.assertIn(thicket, state.zones[Zone.ALONG_THE_WAY])
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
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [bramble],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Check and process clears
        cleared = eng.check_and_process_clears()

        # Assertions
        self.assertEqual(len(cleared), 2)
        self.assertIn(thicket, cleared)
        self.assertIn(bramble, cleared)
        self.assertNotIn(thicket, state.zones[Zone.ALONG_THE_WAY])
        self.assertNotIn(bramble, state.zones[Zone.WITHIN_REACH])
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
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [thicket],
                Zone.WITHIN_REACH: [],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

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
            zones={
                Zone.SURROUNDINGS: [],
                Zone.ALONG_THE_WAY: [],
                Zone.WITHIN_REACH: [buck],
                Zone.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Directly discard (simulating some effect that discards without clearing)
        buck.discard_from_play(eng)

        # Card should be discarded even though it didn't clear
        self.assertNotIn(buck, state.zones[Zone.WITHIN_REACH])
        self.assertIn(buck, state.path_discard)


if __name__ == '__main__':
    unittest.main()
