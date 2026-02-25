#type: ignore
import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import QuisiVosRascal, TheFundamentalist, ProwlingWolhund
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_test_ranger() -> RangerState:
    """Create a test ranger with basic setup"""
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(10)],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
    )




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

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
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

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
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

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
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

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state)

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

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.SUN)


        eng = GameEngine(state,
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
        ambush_card.enters_play(eng, Area.WITHIN_REACH, None)

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


class TheFundamentalistTests(unittest.TestCase):
    """Tests for The Fundamentalist"""

    def test_fundamentalist_has_friendly_keyword(self):
        """Test that The Fundamentalist has the Friendly keyword"""
        fundamentalist = TheFundamentalist()
        self.assertTrue(fundamentalist.has_keyword(Keyword.FRIENDLY))

    def test_fundamentalist_presence_reduction_same_area(self):
        """Test that The Fundamentalist reduces presence of beings in the same area by 1"""
        fundamentalist = TheFundamentalist()
        being = Card(
            id="test-being",
            title="Test Being",
            card_types={CardType.PATH, CardType.BEING},
            presence=3,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist, being],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Verify base presence
        self.assertEqual(being.presence, 3, "Being should have base presence of 3")

        # Check current presence with Fundamentalist in same area
        current_presence = being.get_current_presence(eng)
        self.assertEqual(current_presence, 2, "Being's presence should be reduced by 1 (3 - 1 = 2)")

    def test_fundamentalist_no_reduction_different_area(self):
        """Test that The Fundamentalist does NOT reduce presence of beings in different areas"""
        fundamentalist = TheFundamentalist()
        being = Card(
            id="test-being",
            title="Test Being",
            card_types={CardType.PATH, CardType.BEING},
            presence=3,
            starting_area=Area.ALONG_THE_WAY
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [being],
            Area.WITHIN_REACH: [fundamentalist],  # Different area
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Check current presence - should NOT be reduced
        current_presence = being.get_current_presence(eng)
        self.assertEqual(current_presence, 3, "Being's presence should not be reduced (different area)")

    def test_fundamentalist_does_not_reduce_own_presence(self):
        """Test that The Fundamentalist does not reduce his own presence"""
        fundamentalist = TheFundamentalist()

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Check Fundamentalist's own presence (should be base 2)
        current_presence = fundamentalist.get_current_presence(eng)
        self.assertEqual(current_presence, 2, "Fundamentalist should not reduce his own presence")

    def test_fundamentalist_reduces_multiple_beings(self):
        """Test that The Fundamentalist reduces presence of multiple beings in same area"""
        fundamentalist = TheFundamentalist()
        being1 = Card(
            id="being-1",
            title="Being 1",
            card_types={CardType.PATH, CardType.BEING},
            presence=3,
            starting_area=Area.WITHIN_REACH
        )
        being2 = Card(
            id="being-2",
            title="Being 2",
            card_types={CardType.PATH, CardType.BEING},
            presence=2,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist, being1, being2],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Both beings should have reduced presence
        self.assertEqual(being1.get_current_presence(eng), 2, "Being 1 presence should be 3 - 1 = 2")
        self.assertEqual(being2.get_current_presence(eng), 1, "Being 2 presence should be 2 - 1 = 1")

    def test_fundamentalist_does_not_affect_features(self):
        """Test that The Fundamentalist only affects beings, not features"""
        fundamentalist = TheFundamentalist()
        feature = Card(
            id="test-feature",
            title="Test Feature",
            card_types={CardType.PATH, CardType.FEATURE},
            presence=3,
            starting_area=Area.WITHIN_REACH
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist, feature],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Feature presence should NOT be affected
        current_presence = feature.get_current_presence(eng)
        self.assertEqual(current_presence, 3, "Feature presence should not be reduced")

    def test_fundamentalist_mountain_effect_removes_harm(self):
        """Test that The Fundamentalist's Mountain effect removes 1 harm when he has harm"""
        fundamentalist = TheFundamentalist()
        fundamentalist.harm = 2

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Trigger Mountain effect
        handlers = fundamentalist.get_challenge_handlers()
        self.assertIsNotNone(handlers)
        self.assertIn(ChallengeIcon.MOUNTAIN, handlers)

        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertTrue(resolved, "Mountain effect should resolve successfully")
        self.assertEqual(fundamentalist.harm, 1, "Fundamentalist should have 1 less harm (2 - 1 = 1)")

    def test_fundamentalist_mountain_effect_no_harm(self):
        """Test that The Fundamentalist's Mountain effect does nothing when he has no harm"""
        fundamentalist = TheFundamentalist()
        fundamentalist.harm = 0

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.MOUNTAIN)

        eng = GameEngine(state)

        # Trigger Mountain effect
        handlers = fundamentalist.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.MOUNTAIN](eng)

        self.assertFalse(resolved, "Mountain effect should not resolve when no harm")
        self.assertEqual(fundamentalist.harm, 0, "Fundamentalist should still have 0 harm")

    def test_fundamentalist_crest_effect_with_predator(self):
        """Test that The Fundamentalist's Crest effect exhausts predator and adds harm"""
        fundamentalist = TheFundamentalist()
        wolhund = ProwlingWolhund()
        wolhund.exhausted = False

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [wolhund],  # Active predator
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        # Verify initial state
        self.assertFalse(wolhund.exhausted, "Wolhund should start active")
        self.assertEqual(fundamentalist.harm, 0, "Fundamentalist should start with 0 harm")

        # Get wolhund's presence
        wolhund_presence = wolhund.get_current_presence(eng)

        # Trigger Crest effect
        handlers = fundamentalist.get_challenge_handlers()
        self.assertIsNotNone(handlers)
        self.assertIn(ChallengeIcon.CREST, handlers)

        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertTrue(resolved, "Crest effect should resolve successfully")
        self.assertTrue(wolhund.exhausted, "Wolhund should be exhausted")
        self.assertEqual(fundamentalist.harm, wolhund_presence,
                        f"Fundamentalist should have harm equal to wolhund's presence ({wolhund_presence})")

    def test_fundamentalist_crest_effect_no_predator(self):
        """Test that The Fundamentalist's Crest effect does nothing when no predator"""
        fundamentalist = TheFundamentalist()

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })

        stack_deck(state, Aspect.AWA, 0, ChallengeIcon.CREST)

        eng = GameEngine(state)

        # Trigger Crest effect
        handlers = fundamentalist.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved, "Crest effect should not resolve when no predator")
        self.assertEqual(fundamentalist.harm, 0, "Fundamentalist should still have 0 harm")

    def test_fundamentalist_presence_reduction_during_ambush(self):
        """Test that Fundamentalist's presence reduction applies during Ambush fatigue calculation"""
        fundamentalist = TheFundamentalist()
        ambush_being = Card(
            id="ambush-being",
            title="Ambush Being",
            card_types={CardType.PATH, CardType.BEING},
            keywords={Keyword.AMBUSH},
            presence=3,
            starting_area=Area.ALONG_THE_WAY  # Will move to Within Reach
        )

        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [ambush_being],
            Area.WITHIN_REACH: [fundamentalist],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Move ambush being to same area as Fundamentalist
        eng.move_card(ambush_being.id, Area.WITHIN_REACH)

        # Ambush should trigger with REDUCED presence (3 - 1 = 2)
        self.assertEqual(len(ranger.fatigue_stack), 2,
                        "Ranger should be fatigued by reduced presence (3 - 1 = 2)")
        self.assertEqual(len(ranger.deck), initial_deck_size - 2,
                        "Ranger deck should be reduced by 2 (reduced presence)")

    def test_fundamentalist_constant_ability_registers_on_play(self):
        """Test that Fundamentalist's constant ability is registered when he enters play"""
        fundamentalist = TheFundamentalist()

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Get constant abilities
        abilities = fundamentalist.get_constant_abilities()
        self.assertIsNotNone(abilities, "Fundamentalist should have constant abilities")
        self.assertEqual(len(abilities), 1, "Should have exactly 1 constant ability")
        self.assertEqual(abilities[0].ability_type, ConstantAbilityType.MODIFY_PRESENCE,
                        "Should be MODIFY_PRESENCE type")

        # Register the ability
        eng.register_constant_abilities(abilities)

        # Verify ability is in engine's constant abilities list
        presence_abilities = [a for a in eng.constant_abilities
                            if a.ability_type == ConstantAbilityType.MODIFY_PRESENCE]
        self.assertEqual(len(presence_abilities), 1,
                        "Engine should have 1 MODIFY_PRESENCE ability registered")


class QuisiCampaignGuideTests(unittest.TestCase):
    """Tests for Quisi's campaign guide entries"""

    def test_quisi_cleared_by_progress_default_entry(self):
        """Test that clearing Quisi by progress triggers entry 80 -> 80.5 (default case)"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Add progress to reach threshold (3R = 3 for solo)
        quisi.progress = 3

        # Clear should trigger campaign entry 80.5
        cleared = eng.check_and_process_clears()

        # Entry 80.5 discards Quisi itself and returns True, so Quisi won't be in cleared list
        # But we can verify the campaign entry was triggered and Quisi was removed
        self.assertNotIn(quisi, state.areas[Area.WITHIN_REACH],
                        "Quisi should be removed from play")

    def test_quisi_cleared_by_harm_ends_day(self):
        """Test that clearing Quisi by harm triggers entry 80 -> 80.6 (ends the day)"""
        from src.models import DayEndException

        quisi = QuisiVosRascal()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Add harm to reach threshold
        quisi.harm = 3

        # Entry 80.6 calls end_day() which raises DayEndException
        with self.assertRaises(DayEndException):
            eng.check_and_process_clears()

        # Check for the specific message from entry 80.6
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("yelps" in m for m in messages),
                       "Should contain entry 80.6 story text about Quisi yelping")
        self.assertTrue(any("Day" in m and "ended" in m for m in messages),
                       "Should contain day ended message")

    def test_quisi_entry_80_with_biscuit_basket(self):
        """Test entry 80 routes to 80.1 when Biscuit Basket is equipped"""
        quisi = QuisiVosRascal()
        biscuit_basket = Card(
            id="biscuit-basket",
            title="Biscuit Basket",
            card_types={CardType.RANGER, CardType.GEAR}
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [biscuit_basket],  # Equipped gear
        })
        eng = GameEngine(state)

        # Manually trigger entry 80 (enters play)
        eng.campaign_guide.resolve_entry("80", quisi, eng, None)

        # Check messages for entry 80.1 text
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("giggle" in m for m in messages),
                       "Should route to entry 80.1 with giggle text")
        self.assertTrue(any("biscuits" in m for m in messages),
                       "Entry 80.1 should mention biscuits")

    def test_quisi_entry_80_with_oura_vos(self):
        """Test entry 80 routes to 80.2 when Oura Vos is in play"""
        quisi = QuisiVosRascal()
        oura = Card(
            id="oura-vos",
            title="Oura Vos, Traveler",
            card_types={CardType.PATH, CardType.BEING}
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [oura],  # Oura in play
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Manually trigger entry 80 (enters play)
        eng.campaign_guide.resolve_entry("80", quisi, eng, None)

        # Check for entry 80.2 effects
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("Didn't I tell you" in m for m in messages),
                       "Should route to entry 80.2 with mother's dialogue")

        # Verify reward was unlocked
        self.assertIn("Quisi's Favorite Snack", state.campaign_tracker.unlocked_rewards,
                     "Should unlock Quisi's Favorite Snack reward")

        # Verify notable event was recorded
        self.assertIn("ACCEPTED SNACKS", state.campaign_tracker.notable_events,
                     "Should record ACCEPTED SNACKS event")

        # Verify both cards were discarded
        self.assertNotIn(quisi, state.areas[Area.WITHIN_REACH],
                        "Quisi should be discarded")
        self.assertNotIn(oura, state.areas[Area.ALONG_THE_WAY],
                        "Oura should be discarded")

    def test_quisi_entry_80_default_case(self):
        """Test entry 80 routes to 80.3 when no special conditions"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Manually trigger entry 80 (enters play) - no Biscuit Basket, no Oura
        eng.campaign_guide.resolve_entry("80", quisi, eng, None)

        # Check for entry 80.3 text
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("singing to herself" in m for m in messages),
                       "Should route to entry 80.3 with singing text")
        self.assertTrue(any("prosthesis" in m for m in messages),
                       "Entry 80.3 should describe her prosthetic hand")
        self.assertTrue(any("Hi! I" in m and "Quisi" in m for m in messages),
                       "Entry 80.3 should have Quisi's introduction")

    def test_quisi_entry_80_biscuit_basket_takes_priority_over_oura(self):
        """Test that Biscuit Basket check happens before Oura Vos check"""
        quisi = QuisiVosRascal()
        biscuit_basket = Card(
            id="biscuit-basket",
            title="Biscuit Basket",
            card_types={CardType.RANGER, CardType.GEAR}
        )
        oura = Card(
            id="oura-vos",
            title="Oura Vos, Traveler",
            card_types={CardType.PATH, CardType.BEING}
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [oura],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [biscuit_basket],
        })
        eng = GameEngine(state)

        # Trigger entry 80 with BOTH conditions present
        eng.campaign_guide.resolve_entry("80", quisi, eng, None)

        # Should route to 80.1 (Biscuit Basket), not 80.2 (Oura)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("giggle" in m for m in messages),
                       "Should route to entry 80.1 (Biscuit Basket has priority)")
        self.assertFalse(any("Didn't I tell you" in m for m in messages),
                        "Should NOT route to entry 80.2")

    def test_quisi_entry_80_5_soothes_and_discards(self):
        """Test that entry 80.5 (clear by progress) soothes fatigue and discards Quisi"""
        quisi = QuisiVosRascal()
        ranger = make_test_ranger()

        # Give ranger some fatigue to soothe
        ranger.fatigue_stack = [
            Card(id="fat1", title="Fatigue 1"),
            Card(id="fat2", title="Fatigue 2"),
            Card(id="fat3", title="Fatigue 3"),
        ]

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Manually trigger entry 80.5
        eng.campaign_guide.resolve_entry("80.5", quisi, eng, None)

        # Verify soothe happened (2 cards moved from fatigue to hand)
        self.assertEqual(len(ranger.fatigue_stack), 1,
                        "Should soothe 2 fatigue (3 - 2 = 1)")
        self.assertEqual(len(ranger.hand), 2,
                        "Should draw 2 cards from fatigue into hand")

        # Verify Quisi was discarded
        self.assertNotIn(quisi, state.areas[Area.WITHIN_REACH],
                        "Quisi should be discarded")

    def test_quisi_entry_80_6_story_text(self):
        """Test that entry 80.6 (clear by harm) displays correct story text"""
        from src.models import DayEndException

        quisi = QuisiVosRascal()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Manually trigger entry 80.6 (should raise DayEndException)
        with self.assertRaises(DayEndException):
            eng.campaign_guide.resolve_entry("80.6", quisi, eng, None)

        # Check for entry 80.6 story text
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("yelps" in m for m in messages),
                       "Entry 80.6 should contain 'yelps'")
        self.assertTrue(any("End the day" in m for m in messages),
                       "Entry 80.6 should say to end the day")

    def test_quisi_entry_returns_correct_discard_flag(self):
        """Test that campaign entries return correct bool for whether card was discarded"""
        quisi = QuisiVosRascal()
        oura = Card(
            id="oura-vos",
            title="Oura Vos, Traveler",
            card_types={CardType.PATH, CardType.BEING}
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [oura],
            Area.WITHIN_REACH: [quisi],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Entry 80.1 should return False (card NOT discarded by entry)
        result_80_1 = eng.campaign_guide.resolve_entry("80.1", quisi, eng, None)
        self.assertFalse(result_80_1, "Entry 80.1 should return False (card not discarded)")

        # Entry 80.2 should return True (card discarded by entry)
        result_80_2 = eng.campaign_guide.resolve_entry("80.2", quisi, eng, None)
        self.assertTrue(result_80_2, "Entry 80.2 should return True (card discarded)")

        # Re-create state for next test
        quisi2 = QuisiVosRascal()
        state2 = GameState(ranger=make_test_ranger(), areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [quisi2],
            Area.PLAYER_AREA: [],
        })
        eng2 = GameEngine(state2)

        # Entry 80.5 should return True (card discarded by entry)
        result_80_5 = eng2.campaign_guide.resolve_entry("80.5", quisi2, eng2, None)
        self.assertTrue(result_80_5, "Entry 80.5 should return True (card discarded)")

    def test_quisi_campaign_log_fields_loaded_from_json(self):
        """Test that Quisi's campaign log entry fields are properly loaded from JSON"""
        quisi = QuisiVosRascal()

        # Quisi should have all campaign log entries set to "80"
        self.assertEqual(quisi.on_enter_log, "80",
                         "Quisi should have enters_play campaign entry 80")
        self.assertEqual(quisi.on_progress_clear_log, "80",
                        "Quisi should have progress clear entry 80")
        self.assertEqual(quisi.on_harm_clear_log, "80",
                        "Quisi should have harm clear entry 80")


if __name__ == '__main__':
    unittest.main()
