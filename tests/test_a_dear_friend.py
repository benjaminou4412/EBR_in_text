#type:ignore
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import ADearFriend


class ADearFriendTests(unittest.TestCase):
    """Comprehensive tests for A Dear Friend attachment card"""

    def test_play_targets_humans_in_deck(self):
        """Test that A Dear Friend can target humans in the path deck"""
        adf = ADearFriend()

        # Create a human in path deck
        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        # Create non-human being
        animal = Card(
            title="Animal",
            id="animal1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"animal"},
            starting_area=Area.WITHIN_REACH
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human, animal],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Get play targets
        targets = adf.get_play_targets(state)

        # Should only return human
        self.assertIsNotNone(targets)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].id, "human1")

    def test_play_targets_humans_in_discard(self):
        """Test that A Dear Friend can target humans in the path discard"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_discard=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        targets = adf.get_play_targets(state)

        self.assertIsNotNone(targets)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].id, "human1")

    def test_play_from_deck_puts_human_in_play_and_attaches(self):
        """Test that playing A Dear Friend puts the human into play and attaches correctly"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Verify initial state
        self.assertIn(human, state.path_deck)
        self.assertIn(adf, ranger.hand)
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 0)

        # Play A Dear Friend targeting the human
        adf.play(eng, target=human)

        # Verify human is now in play
        self.assertNotIn(human, state.path_deck)
        self.assertIn(human, state.areas[Area.WITHIN_REACH])

        # Verify attachment is attached to human
        self.assertEqual(adf.attached_to_id, human.id)
        self.assertIn(adf.id, human.attached_card_ids)

        # Verify attachment is in same area as human
        self.assertIn(adf, state.areas[Area.WITHIN_REACH])

        # Verify attachment is not in hand anymore
        self.assertNotIn(adf, ranger.hand)

        # Verify listener was registered
        self.assertEqual(len(eng.listeners), 1)
        self.assertEqual(eng.listeners[0].event_type, EventType.CLEAR)

    def test_play_from_discard_puts_human_in_play(self):
        """Test that A Dear Friend can pull humans from path discard"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.ALONG_THE_WAY,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_discard=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Verify initial state
        self.assertIn(human, state.path_discard)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Verify human is now in play
        self.assertNotIn(human, state.path_discard)
        self.assertIn(human, state.areas[Area.ALONG_THE_WAY])

        # Verify attached
        self.assertEqual(adf.attached_to_id, human.id)

    def test_listener_triggers_when_attached_human_clears(self):
        """Test that the listener triggers when the attached human clears"""
        adf = ADearFriend()

        # Create human with progress at threshold
        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=3,
            progress=3  # At threshold, will clear
        )

        # Create another being to receive the progress
        other_being = Card(
            title="Other Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10,
            progress=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [other_being],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play A Dear Friend to put human into play
        adf.play(eng, target=human)

        # Verify human is in play with 3 progress
        self.assertEqual(human.progress, 3)
        self.assertIn(human, state.areas[Area.WITHIN_REACH])

        # Check and process clears (human should clear)
        eng.check_and_process_clears()

        # Verify human was cleared
        self.assertNotIn(human, state.areas[Area.WITHIN_REACH])
        self.assertIn(human, state.path_discard)

        # Verify progress was redistributed to other being (default choosers pick max)
        self.assertEqual(other_being.progress, 3)

    def test_listener_only_triggers_for_attached_human(self):
        """Test that the listener only triggers when the specific attached human clears"""
        adf = ADearFriend()

        # Create the human A Dear Friend is attached to
        target_human = Card(
            title="Target Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=3,
            progress=0
        )

        # Create a different human that will clear
        other_human = Card(
            title="Other Human",
            id="human2",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.ALONG_THE_WAY,
            progress_threshold=2,
            progress=2  # Will clear
        )

        # Create a being to potentially receive progress
        being = Card(
            title="Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10,
            progress=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[target_human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [other_human],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play A Dear Friend attached to target_human
        adf.play(eng, target=target_human)

        # Verify target_human is in play, other_human will clear
        self.assertIn(target_human, state.areas[Area.WITHIN_REACH])
        self.assertIn(other_human, state.areas[Area.ALONG_THE_WAY])

        # Check and process clears (only other_human should clear)
        eng.check_and_process_clears()

        # Verify other_human cleared but progress was NOT redistributed
        self.assertNotIn(other_human, state.areas[Area.ALONG_THE_WAY])
        self.assertEqual(being.progress, 0)  # No progress added

        # Verify target_human is still in play
        self.assertIn(target_human, state.areas[Area.WITHIN_REACH])

    def test_progress_redistribution_to_multiple_beings(self):
        """Test that progress can be redistributed to multiple beings"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5,
            progress=5  # Will clear with 5 progress
        )

        being1 = Card(
            title="Being 1",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10,
            progress=0
        )

        being2 = Card(
            title="Being 2",
            id="being2",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.ALONG_THE_WAY,
            progress_threshold=10,
            progress=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being2],
                Area.WITHIN_REACH: [being1],
                Area.PLAYER_AREA: []
            }
        )

        # Custom choosers to distribute: 3 to being1, 2 to being2
        call_count = [0]
        def custom_card_chooser(_eng, beings):
            call_count[0] += 1
            if call_count[0] == 1:
                return being1
            else:
                return being2

        amount_calls = [0]
        def custom_amount_chooser(_eng, min_amt, max_amt, _prompt):
            amount_calls[0] += 1
            if amount_calls[0] == 1:
                return 3  # First distribution: 3 to being1
            else:
                return 2  # Second distribution: 2 to being2

        eng = GameEngine(state, card_chooser=custom_card_chooser, amount_chooser=custom_amount_chooser)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Check and process clears
        eng.check_and_process_clears()

        # Verify progress distribution
        self.assertEqual(being1.progress, 3)
        self.assertEqual(being2.progress, 2)

        # Verify human cleared
        self.assertNotIn(human, state.areas[Area.WITHIN_REACH])

    def test_cannot_redistribute_to_clearing_human(self):
        """Test that progress cannot be redistributed to the human that is clearing"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=3,
            progress=3  # Will clear
        )

        # Another being to receive progress
        being = Card(
            title="Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10,
            progress=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: []
            }
        )

        # Track what beings are offered as choices
        offered_beings = []
        def track_beings(_eng, beings):
            offered_beings.extend(beings)
            return beings[0]

        eng = GameEngine(state, card_chooser=track_beings)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Check and process clears
        eng.check_and_process_clears()

        # Verify the clearing human was NOT offered as a choice
        self.assertEqual(len(offered_beings), 1)
        self.assertEqual(offered_beings[0].id, "being1")
        self.assertNotIn(human, offered_beings)

    def test_human_with_zero_progress_on_clear(self):
        """Test that clearing a human with 0 progress doesn't require redistribution"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=0,  # Clears immediately
            progress=0
        )

        being = Card(
            title="Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10,
            progress=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: []
            }
        )

        # Track if choosers are called
        chooser_called = [False]
        def track_chooser(_eng, _beings):
            chooser_called[0] = True
            return None

        eng = GameEngine(state, card_chooser=track_chooser)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Check and process clears
        eng.check_and_process_clears()

        # Verify chooser was never called (no progress to redistribute)
        self.assertFalse(chooser_called[0])

        # Verify being has no progress
        self.assertEqual(being.progress, 0)

        # Verify human cleared
        self.assertNotIn(human, state.areas[Area.WITHIN_REACH])

    def test_attachment_moves_with_human(self):
        """Test that A Dear Friend moves when the attached human moves areas"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Verify both are in WITHIN_REACH
        self.assertIn(human, state.areas[Area.WITHIN_REACH])
        self.assertIn(adf, state.areas[Area.WITHIN_REACH])

        # Move human to ALONG_THE_WAY
        eng.move_card(human.id, Area.ALONG_THE_WAY)

        # Verify attachment moved with it
        self.assertIn(human, state.areas[Area.ALONG_THE_WAY])
        self.assertIn(adf, state.areas[Area.ALONG_THE_WAY])
        self.assertNotIn(adf, state.areas[Area.WITHIN_REACH])

    def test_case_insensitive_human_trait_matching(self):
        """Test that trait matching is case-insensitive"""
        adf = ADearFriend()

        # Create humans with different case traits
        human1 = Card(
            title="Human 1",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"Human"},  # Capital H
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        human2 = Card(
            title="Human 2",
            id="human2",
            card_types={CardType.PATH, CardType.BEING},
            traits={"HUMAN"},  # All caps
            starting_area=Area.WITHIN_REACH,
            progress_threshold=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human1, human2],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Get play targets
        targets = adf.get_play_targets(state)

        # Should return both humans despite case differences
        self.assertIsNotNone(targets)
        self.assertEqual(len(targets), 2)

    def test_attachment_discards_when_human_leaves_play(self):
        """Test that A Dear Friend discards when the attached human is discarded"""
        adf = ADearFriend()

        human = Card(
            title="Test Human",
            id="human1",
            card_types={CardType.PATH, CardType.BEING},
            traits={"human"},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=3,
            progress=3  # Will clear
        )

        being = Card(
            title="Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            starting_area=Area.WITHIN_REACH,
            progress_threshold=10
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[adf],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5}
        )

        state = GameState(
            ranger=ranger,
            path_deck=[human],
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [being],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play A Dear Friend
        adf.play(eng, target=human)

        # Verify both are in play
        self.assertIn(human, state.areas[Area.WITHIN_REACH])
        self.assertIn(adf, state.areas[Area.WITHIN_REACH])

        # Process clears (human will clear)
        eng.check_and_process_clears()

        # Verify both cleared/discarded
        self.assertNotIn(human, state.areas[Area.WITHIN_REACH])
        self.assertNotIn(adf, state.areas[Area.WITHIN_REACH])
        self.assertIn(human, state.path_discard)
        # A Dear Friend is a ranger card, goes to ranger discard
        self.assertIn(adf, state.ranger.discard)


if __name__ == '__main__':
    unittest.main()
