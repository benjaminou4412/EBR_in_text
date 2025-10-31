import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import QuisiVosRascal


def fixed_draw(mod: int, sym: ChallengeIcon):
    return lambda: (mod, sym)


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(10)],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
    )


class QuisiVosTests(unittest.TestCase):
    """Tests for Quisi Vos, Rascal"""

    def test_quisi_has_fatiguing_keyword(self):
        """Test that Quisi has the Fatiguing keyword"""
        quisi = QuisiVosRascal()
        self.assertTrue(quisi.has_keyword(Keyword.FATIGUING))

    def test_quisi_has_friendly_keyword(self):
        """Test that Quisi has the Friendly keyword"""
        quisi = QuisiVosRascal()
        self.assertTrue(quisi.has_keyword(Keyword.FRIENDLY))

    def test_quisi_has_persistent_keyword(self):
        """Test that Quisi has the Persistent keyword"""
        quisi = QuisiVosRascal()
        self.assertTrue(quisi.has_keyword(Keyword.PERSISTENT))

    def test_quisi_generates_fatiguing_listener(self):
        """Test that Quisi auto-generates a REST listener from Fatiguing keyword"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        listeners = quisi.get_listeners(eng)
        self.assertIsNotNone(listeners, "Quisi should generate listeners from Fatiguing keyword")
        self.assertEqual(len(listeners), 1, "Should have exactly 1 listener")
        self.assertEqual(listeners[0].event_type, EventType.REST, "Listener should be REST type")
        self.assertEqual(listeners[0].timing_type, TimingType.WHEN, "Listener should be WHEN timing")

    def test_fatiguing_listener_can_be_registered(self):
        """Test that Quisi's Fatiguing listener can be retrieved and registered"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Get listeners from Quisi
        listeners = quisi.get_listeners(eng)

        self.assertIsNotNone(listeners, "Should return listeners")
        assert listeners is not None  # Type narrowing for mypy
        self.assertEqual(len(listeners), 1, "Should have 1 listener")
        self.assertEqual(listeners[0].event_type, EventType.REST)

        # Register the listener
        eng.register_listeners(listeners)

        # Verify listener is in engine's listener list
        rest_listeners = [l for l in eng.listeners if l.event_type == EventType.REST]
        self.assertEqual(len(rest_listeners), 1, "Engine should have 1 REST listener registered")

    def test_fatiguing_triggers_on_rest(self):
        """Test that Fatiguing keyword actually fatigues the ranger when REST is triggered"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Register Quisi's listeners
        listeners = quisi.get_listeners(eng)
        eng.register_listeners(listeners)

        # Trigger REST event
        eng.resolve_fatiguing_keyword()

        # Verify ranger was fatigued by Quisi's presence (should be 1)
        expected_fatigue = quisi.get_current_presence(eng)
        self.assertEqual(len(ranger.fatigue_stack), expected_fatigue,
                        f"Ranger should have {expected_fatigue} cards in fatigue stack")
        self.assertEqual(len(ranger.deck), initial_deck_size - expected_fatigue,
                        f"Ranger deck should be reduced by {expected_fatigue}")

    def test_multiple_fatiguing_cards_stack(self):
        """Test that multiple Fatiguing cards each trigger separately"""
        quisi1 = QuisiVosRascal()
        quisi2 = QuisiVosRascal()

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi1, quisi2],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Register both cards' listeners
        eng.register_listeners(quisi1.get_listeners(eng))
        eng.register_listeners(quisi2.get_listeners(eng))

        # Trigger REST event
        eng.resolve_fatiguing_keyword()

        # Both Quisis should fatigue (1 each = 2 total)
        total_presence = quisi1.get_current_presence(eng) + quisi2.get_current_presence(eng)
        self.assertEqual(len(ranger.fatigue_stack), total_presence,
                        f"Ranger should have {total_presence} cards in fatigue stack from both Quisis")

    def test_quisi_sun_effect_with_flora_target(self):
        """Test Quisi's Sun effect can target Flora with progress"""
        quisi = QuisiVosRascal()

        flora = Card(
            id="flora-target",
            title="Test Flora",
            card_types={CardType.PATH, CardType.FEATURE},
            traits={"Flora"},
            progress=3,
            progress_threshold=5
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [flora],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })

        def choose_flora(_engine: GameEngine, targets: list[Card]) -> Card:
            return flora

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=choose_flora)

        # Trigger Sun effect
        handlers = quisi.get_challenge_handlers()
        self.assertIsNotNone(handlers)
        self.assertIn(ChallengeIcon.SUN, handlers)

        initial_progress = flora.progress
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved, "Sun effect should resolve successfully")
        self.assertEqual(flora.progress, initial_progress - 1, "Flora should lose 1 progress")

    def test_quisi_sun_effect_with_insect_target(self):
        """Test Quisi's Sun effect can target Insect with progress"""
        quisi = QuisiVosRascal()

        insect = Card(
            id="insect-target",
            title="Test Insect",
            card_types={CardType.PATH, CardType.BEING},
            traits={"Insect"},
            progress=2,
            progress_threshold=3
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [insect],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })

        def choose_insect(_engine: GameEngine, targets: list[Card]) -> Card:
            return insect

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=choose_insect)

        # Trigger Sun effect
        handlers = quisi.get_challenge_handlers()
        initial_progress = insect.progress
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved, "Sun effect should resolve successfully")
        self.assertEqual(insect.progress, initial_progress - 1, "Insect should lose 1 progress")

    def test_quisi_sun_effect_with_gear_target(self):
        """Test Quisi's Sun effect can target Gear with progress"""
        quisi = QuisiVosRascal()

        gear = Card(
            id="gear-target",
            title="Test Gear",
            card_types={CardType.RANGER, CardType.GEAR},
            progress=2,
            progress_threshold=4
        )

        ranger = make_test_ranger()
        # Put gear in hand first, then we'll simulate it in play
        ranger.hand.append(gear)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [gear],  # Gear in player area
        })

        def choose_gear(_engine: GameEngine, targets: list[Card]) -> Card:
            return gear

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=choose_gear)

        # Trigger Sun effect
        handlers = quisi.get_challenge_handlers()
        initial_progress = gear.progress
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved, "Sun effect should resolve successfully")
        self.assertEqual(gear.progress, initial_progress - 1, "Gear should lose 1 progress")

    def test_quisi_sun_effect_no_valid_targets(self):
        """Test Quisi's Sun effect when no valid targets exist"""
        quisi = QuisiVosRascal()

        # Card with right trait but no progress
        flora_no_progress = Card(
            id="flora-no-progress",
            title="Flora No Progress",
            card_types={CardType.PATH, CardType.FEATURE},
            traits={"Flora"},
            progress=0,
            progress_threshold=5
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [flora_no_progress],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })

        eng = GameEngine(state, challenge_drawer=fixed_draw(0, ChallengeIcon.SUN))

        # Trigger Sun effect
        handlers = quisi.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertFalse(resolved, "Sun effect should not resolve when no valid targets")

    def test_quisi_sun_effect_multiple_valid_targets(self):
        """Test Quisi's Sun effect when multiple valid targets exist"""
        quisi = QuisiVosRascal()

        flora = Card(
            id="flora",
            title="Flora",
            card_types={CardType.PATH, CardType.FEATURE},
            traits={"Flora"},
            progress=3,
            progress_threshold=5
        )

        insect = Card(
            id="insect",
            title="Insect",
            card_types={CardType.PATH, CardType.BEING},
            traits={"Insect"},
            progress=2,
            progress_threshold=3
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [flora, insect],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })

        # Track which targets were offered
        offered_targets = []

        def track_and_choose(_engine: GameEngine, targets: list[Card]) -> Card:
            offered_targets.extend(targets)
            return insect

        eng = GameEngine(state,
                        challenge_drawer=fixed_draw(0, ChallengeIcon.SUN),
                        card_chooser=track_and_choose)

        # Trigger Sun effect
        handlers = quisi.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.SUN](eng)

        self.assertTrue(resolved, "Sun effect should resolve")
        self.assertEqual(len(offered_targets), 2, "Should offer both flora and insect as targets")
        self.assertIn(flora, offered_targets)
        self.assertIn(insect, offered_targets)
        self.assertEqual(insect.progress, 1, "Chosen insect should lose 1 progress")
        self.assertEqual(flora.progress, 3, "Unchosen flora should keep its progress")


class AmbushKeywordTests(unittest.TestCase):
    """Tests for the Ambush keyword"""

    def test_ambush_triggers_on_enter_within_reach(self):
        """Test that Ambush triggers when a card enters play at Within Reach"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=2,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Manually trigger enters_play
        state.areas[Area.WITHIN_REACH].append(ambush_card)
        ambush_card.enters_play(eng, Area.WITHIN_REACH)

        # Verify ranger was fatigued by presence (2)
        self.assertEqual(len(ranger.fatigue_stack), 2,
                        "Ranger should have 2 cards in fatigue stack from Ambush")
        self.assertEqual(len(ranger.deck), initial_deck_size - 2,
                        "Ranger deck should be reduced by 2")

    def test_ambush_does_not_trigger_in_other_areas(self):
        """Test that Ambush does NOT trigger when entering play in other areas"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=2,
            starting_area=Area.ALONG_THE_WAY
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Enter play in Along the Way (not Within Reach)
        state.areas[Area.ALONG_THE_WAY].append(ambush_card)
        ambush_card.enters_play(eng, Area.ALONG_THE_WAY)

        # Verify ranger was NOT fatigued
        self.assertEqual(len(ranger.fatigue_stack), 0,
                        "Ranger should not be fatigued when Ambush card enters Along the Way")
        self.assertEqual(len(ranger.deck), initial_deck_size,
                        "Ranger deck should be unchanged")

    def test_ambush_triggers_on_move_to_within_reach(self):
        """Test that Ambush triggers when a card moves to Within Reach"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=3,
            starting_area=Area.ALONG_THE_WAY
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [ambush_card],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Move card from Along the Way to Within Reach
        eng.move_card(ambush_card.id, Area.WITHIN_REACH)

        # Verify ranger was fatigued by presence (3)
        self.assertEqual(len(ranger.fatigue_stack), 3,
                        "Ranger should have 3 cards in fatigue stack from Ambush on move")
        self.assertEqual(len(ranger.deck), initial_deck_size - 3,
                        "Ranger deck should be reduced by 3")

    def test_ambush_does_not_trigger_on_move_to_other_areas(self):
        """Test that Ambush does NOT trigger when moving to areas other than Within Reach"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=2,
            starting_area=Area.SURROUNDINGS
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [ambush_card],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Move from Surroundings to Along the Way (not Within Reach)
        eng.move_card(ambush_card.id, Area.ALONG_THE_WAY)

        # Verify ranger was NOT fatigued
        self.assertEqual(len(ranger.fatigue_stack), 0,
                        "Ranger should not be fatigued when Ambush card moves to Along the Way")
        self.assertEqual(len(ranger.deck), initial_deck_size,
                        "Ranger deck should be unchanged")

    def test_ambush_with_modified_presence(self):
        """Test that Ambush uses current presence (which can be modified)"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=2,  # Base presence
            starting_area=Area.ALONG_THE_WAY
        )

        # Add a modifier that increases presence
        ambush_card.modifiers.append(
            ValueModifier(target="presence", amount=2, source_id="test-modifier")
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [ambush_card],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Current presence should be 2 + 2 = 4
        self.assertEqual(ambush_card.get_current_presence(eng), 4)

        # Move to Within Reach to trigger Ambush
        eng.move_card(ambush_card.id, Area.WITHIN_REACH)

        # Should fatigue by modified presence (4)
        self.assertEqual(len(ranger.fatigue_stack), 4,
                        "Ranger should be fatigued by modified presence (4)")

    def test_ambush_does_not_trigger_twice_on_same_card(self):
        """Test that Ambush doesn't trigger twice if card enters and then moves"""
        ambush_card = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=2,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Enter play at Within Reach (triggers Ambush once)
        state.areas[Area.WITHIN_REACH].append(ambush_card)
        ambush_card.enters_play(eng, Area.WITHIN_REACH)

        self.assertEqual(len(ranger.fatigue_stack), 2, "Should trigger once on enter")

        # Move to another area and back
        eng.move_card(ambush_card.id, Area.ALONG_THE_WAY)
        eng.move_card(ambush_card.id, Area.WITHIN_REACH)

        # Should trigger again on the move back
        self.assertEqual(len(ranger.fatigue_stack), 4,
                        "Should trigger again on move back to Within Reach (2 + 2 = 4)")


if __name__ == '__main__':
    unittest.main()
