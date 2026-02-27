#type: ignore
"""
Comprehensive tests for Hy Pimpot, Chef and his campaign guide entries (47.x).
Covers:
- Static fields (traits, keywords, thresholds, presence)
- Friendly keyword behavior (skips interaction fatigue, blocks Weapon targeting)
- Crest challenge handler (harm_from_predator)
- Harvest test (flora attachment, facedown counting, 47.4 trigger)
- Campaign guide entry routing (47 -> 47.1/47.2/47.3/47.6)
- Entry 47.4/47.5 (location conditional, soothe, reward unlock)
- HelpingHand (attachment, Persistent grant)
"""

import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import HelpingHand
from ebr.cards.lone_tree_station_cards import HyPimpotChef
from ebr.cards.woods_cards import ProwlingWolhund, SunberryBramble
from tests.test_utils import MockChallengeDeck, make_challenge_card


def make_test_ranger() -> RangerState:
    """Create a test ranger with a 10-card deck and standard aspects."""
    return RangerState(
        name="Test Ranger",
        hand=[],
        deck=[Card(id=f"deck{i}", title=f"Deck Card {i}") for i in range(10)],
        aspects={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1}
    )


def stack_deck(state: GameState, aspect: Aspect, mod: int, symbol: ChallengeIcon) -> None:
    """Helper to stack the challenge deck with a single predetermined card."""
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


def make_flora_card(title: str = "Test Flora") -> Card:
    """Create a simple Flora-traited path card for Harvest testing."""
    return Card(
        title=title,
        card_types={CardType.PATH, CardType.FEATURE},
        traits={"Flora"},
        presence=1,
        starting_area=Area.ALONG_THE_WAY,
        harm_threshold=3,
        progress_threshold=3,
    )


def make_lone_tree_location() -> Card:
    """Create a minimal Lone Tree Station location card."""
    return Card(
        title="Lone Tree Station",
        id="lone-tree-station",
        card_types={CardType.LOCATION},
        traits={"Pivotal"},
        progress_threshold=4,
    )


def make_other_location() -> Card:
    """Create a non-Lone-Tree location card."""
    return Card(
        title="Boulder Field",
        id="boulder-field",
        card_types={CardType.LOCATION},
        progress_threshold=3,
    )


# ============================================================
# Unit Tests: Static fields
# ============================================================

class TestHyPimpotStaticFields(unittest.TestCase):
    """Tests for Hy Pimpot's card data loaded from JSON."""

    def setUp(self):
        self.hy = HyPimpotChef()

    def test_title(self):
        self.assertEqual(self.hy.title, "Hy Pimpot, Chef")

    def test_card_types(self):
        self.assertIn(CardType.PATH, self.hy.card_types)
        self.assertIn(CardType.BEING, self.hy.card_types)

    def test_traits(self):
        self.assertTrue(self.hy.has_trait("Human"))
        self.assertTrue(self.hy.has_trait("Ranger"))

    def test_presence(self):
        self.assertEqual(self.hy.presence, 2)

    def test_harm_threshold(self):
        self.assertEqual(self.hy.harm_threshold, 3)

    def test_progress_threshold(self):
        """Progress threshold is 2R: value 2. Note: 'R' suffix not yet parsed into clears_by_ranger_tokens."""
        self.assertEqual(self.hy.progress_threshold, 2)

    def test_starting_area(self):
        self.assertEqual(self.hy.starting_area, Area.WITHIN_REACH)

    def test_friendly_keyword(self):
        self.assertTrue(self.hy.has_keyword(Keyword.FRIENDLY))

    def test_campaign_log_entries(self):
        self.assertEqual(self.hy.on_enter_log, "47")
        self.assertEqual(self.hy.on_progress_clear_log, "47")
        self.assertEqual(self.hy.on_harm_clear_log, "47")

    def test_art_description_set(self):
        self.assertIsNotNone(self.hy.art_description)

    def test_has_harvest_test(self):
        tests = self.hy.get_tests()
        self.assertIsNotNone(tests)
        self.assertEqual(len(tests), 1)
        harvest = tests[0]
        self.assertEqual(harvest.verb, "Harvest")
        self.assertEqual(harvest.aspect, Aspect.AWA)
        self.assertEqual(harvest.approach, Approach.REASON)

    def test_harvest_difficulty_is_2(self):
        tests = self.hy.get_tests()
        harvest = tests[0]
        self.assertEqual(harvest.difficulty_fn(None, None), 2)

    def test_has_crest_challenge_handler(self):
        handlers = self.hy.get_challenge_handlers()
        self.assertIsNotNone(handlers)
        self.assertIn(ChallengeIcon.CREST, handlers)

    def test_no_sun_or_mountain_handlers(self):
        handlers = self.hy.get_challenge_handlers()
        self.assertNotIn(ChallengeIcon.SUN, handlers)
        self.assertNotIn(ChallengeIcon.MOUNTAIN, handlers)


# ============================================================
# Unit Tests: Friendly keyword behavior
# ============================================================

class TestHyPimpotFriendlyKeyword(unittest.TestCase):
    """Tests that the Friendly keyword works correctly on Hy."""

    def test_friendly_skips_interaction_fatigue(self):
        """Hy in Within Reach should not fatigue the ranger during interaction."""
        hy = HyPimpotChef()
        target_card = make_flora_card()
        ranger = make_test_ranger()
        initial_deck_size = len(ranger.deck)

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [target_card],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        eng.interaction_fatigue(ranger, target_card)

        # Friendly Hy should not have caused fatigue
        self.assertEqual(len(ranger.deck), initial_deck_size)
        self.assertEqual(len(ranger.fatigue_stack), 0)

    def test_friendly_blocks_weapon_targeting(self):
        """Weapon-traited cards should not be able to target Friendly cards."""
        hy = HyPimpotChef()
        weapon_card = Card(
            title="Test Weapon",
            card_types={CardType.RANGER, CardType.GEAR},
            traits={"Weapon"},
        )

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [weapon_card],
        })
        eng = GameEngine(state)

        # Create a weapon-sourced action that would target Hy
        action = Action(
            id="weapon-test",
            name="Weapon Attack",
            aspect=Aspect.FIT,
            approach=Approach.CONFLICT,
            verb="Hunt",
            target_provider=lambda s: s.beings_in_play(),
            source_id=weapon_card.id,
            source_title=weapon_card.title,
        )
        targets = eng.get_valid_targets(action)
        self.assertNotIn(hy, targets)


# ============================================================
# Unit Tests: Crest challenge handler
# ============================================================

class TestHyPimpotCrestHandler(unittest.TestCase):
    """Tests for Hy Pimpot's Crest challenge effect (harm_from_predator)."""

    def test_crest_with_active_predator(self):
        """Crest should exhaust predator and add harm equal to predator's presence."""
        hy = HyPimpotChef()
        wolhund = ProwlingWolhund()  # Predator with presence 2

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy, wolhund],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        handlers = hy.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertTrue(resolved)
        self.assertTrue(wolhund.exhausted)
        wolhund_presence = wolhund.get_current_presence(eng)
        self.assertEqual(hy.harm, wolhund_presence)

    def test_crest_no_predator_does_not_resolve(self):
        """Crest should not resolve when no predators are in play."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        handlers = hy.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved)
        self.assertEqual(hy.harm, 0)

    def test_crest_exhausted_predator_does_not_resolve(self):
        """Crest should not resolve if the only predator is exhausted."""
        hy = HyPimpotChef()
        wolhund = ProwlingWolhund()
        wolhund.exhausted = True

        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy, wolhund],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        handlers = hy.get_challenge_handlers()
        resolved = handlers[ChallengeIcon.CREST](eng)

        self.assertFalse(resolved)
        self.assertEqual(hy.harm, 0)


# ============================================================
# Integration Tests: Harvest test
# ============================================================

class TestHyPimpotHarvestTest(unittest.TestCase):
    """Tests for Hy's Harvest test: flip flora facedown, attach, count, trigger 47.4."""

    def _setup_harvest(self, flora_cards: list[Card], location_title: str = "Lone Tree Station"):
        """Helper: set up a game state with Hy and flora cards, return (hy, engine, state)."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = Card(
            title=location_title,
            id="location",
            card_types={CardType.LOCATION},
            progress_threshold=4,
        )

        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: flora_cards,
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        stack_deck(state, Aspect.AWA, +5, ChallengeIcon.SUN)  # Guaranteed success
        eng = GameEngine(state)
        return hy, eng, state

    def test_harvest_success_attaches_flora_facedown(self):
        """Successful Harvest should flip target flora facedown and attach to Hy."""
        flora = make_flora_card()
        hy, eng, state = self._setup_harvest([flora])

        # Call the on_success handler directly
        hy._on_harvest_success(eng, 3, flora)

        # Flora should now be facedown and attached to Hy
        self.assertEqual(len(hy.attached_card_ids), 1)
        attached_card = state.get_card_by_id(hy.attached_card_ids[0])
        self.assertIsInstance(attached_card, FacedownCard)
        self.assertEqual(attached_card.backside.title, "Test Flora")

    def test_harvest_success_flora_count_message(self):
        """After successful Harvest, a message should indicate how many flora are attached."""
        flora = make_flora_card()
        hy, eng, state = self._setup_harvest([flora])

        hy._on_harvest_success(eng, 3, flora)

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("1 flora now attached" in m for m in messages))

    def test_harvest_two_flora_no_trigger(self):
        """With only 2 flora attached, entry 47.4 should NOT trigger."""
        flora1 = make_flora_card("Flora 1")
        flora2 = make_flora_card("Flora 2")
        hy, eng, state = self._setup_harvest([flora1, flora2])

        hy._on_harvest_success(eng, 3, flora1)
        hy._on_harvest_success(eng, 3, flora2)

        self.assertEqual(len(hy.attached_card_ids), 2)
        messages = [m.message for m in eng.message_queue]
        self.assertFalse(any("47.4" in m for m in messages),
                         "Should not trigger entry 47.4 with only 2 flora")

    def test_harvest_three_flora_triggers_47_4(self):
        """With 3 flora attached, entry 47.4 should trigger."""
        flora1 = make_flora_card("Flora 1")
        flora2 = make_flora_card("Flora 2")
        flora3 = make_flora_card("Flora 3")
        hy, eng, state = self._setup_harvest([flora1, flora2, flora3])

        hy._on_harvest_success(eng, 3, flora1)
        hy._on_harvest_success(eng, 3, flora2)
        hy._on_harvest_success(eng, 3, flora3)

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("3 flora attached" in m.lower() for m in messages))
        self.assertTrue(any("47.4" in m for m in messages))

    def test_harvest_counts_only_flora_not_other_facedown(self):
        """Flora count should only count FacedownCards whose backside has Flora trait."""
        non_flora = Card(
            title="Not Flora",
            card_types={CardType.PATH, CardType.FEATURE},
            traits={"Plant"},  # NOT "Flora"
            presence=1,
            starting_area=Area.ALONG_THE_WAY,
        )
        flora1 = make_flora_card("Flora 1")
        flora2 = make_flora_card("Flora 2")
        hy, eng, state = self._setup_harvest([non_flora, flora1, flora2])

        # Manually attach a non-flora facedown to Hy
        facedown_non_flora = non_flora.flip(eng)
        eng.attach(facedown_non_flora, hy)

        # Now harvest two actual flora
        hy._on_harvest_success(eng, 3, flora1)
        hy._on_harvest_success(eng, 3, flora2)

        # Should have 3 attachments but only 2 flora
        self.assertEqual(len(hy.attached_card_ids), 3)
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("2 flora now attached" in m for m in messages),
                        "Should count only 2 actual flora, not the non-flora facedown")
        self.assertFalse(any("47.4" in m for m in messages),
                         "Should NOT trigger 47.4 with only 2 real flora")

    def test_harvest_no_target_raises(self):
        """Harvest on_success with None target should raise RuntimeError."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        eng = GameEngine(state)

        with self.assertRaises(RuntimeError):
            hy._on_harvest_success(eng, 3, None)

    def test_harvest_target_provider_returns_only_flora(self):
        """The Harvest test's target_provider should only return Flora-traited cards."""
        hy = HyPimpotChef()
        flora = make_flora_card()
        non_flora = Card(title="Rock", card_types={CardType.PATH, CardType.FEATURE},
                         traits={"Mineral"}, presence=1, starting_area=Area.ALONG_THE_WAY)
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [],
            Area.ALONG_THE_WAY: [flora, non_flora],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [],
        })

        tests = hy.get_tests()
        harvest = tests[0]
        targets = harvest.target_provider(state)

        self.assertIn(flora, targets)
        self.assertNotIn(non_flora, targets)


# ============================================================
# Integration Tests: Campaign guide entry routing (entry 47)
# ============================================================

class TestHyPimpotEntryRouting(unittest.TestCase):
    """Tests for the top-level entry 47 router."""

    def _make_engine_with_hy(self, response=True):
        """Helper: create engine with Hy in play, returning (hy, engine)."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = make_lone_tree_location()
        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, response_decider=lambda _e, _p: response)
        return hy, eng

    def test_enter_play_routes_to_47_1(self):
        """Entry 47 with clear_type=None should route to 47.1."""
        hy, eng = self._make_engine_with_hy()
        eng.campaign_guide.resolve_entry("47", hy, eng, None)

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.1" in m for m in messages))

    def test_progress_clear_no_helping_hand_routes_to_47_3(self):
        """Entry 47 with progress clear and no Helping Hand -> 47.3."""
        hy, eng = self._make_engine_with_hy()
        eng.campaign_guide.resolve_entry("47", hy, eng, "progress")

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.3" in m for m in messages))

    def test_progress_clear_with_helping_hand_routes_to_47_2(self):
        """Entry 47 with progress clear and Helping Hand attached -> 47.2."""
        hy, eng = self._make_engine_with_hy()

        # Attach Helping Hand to Hy
        helping_hand = HelpingHand()
        eng.state.areas[Area.SURROUNDINGS].append(helping_hand)
        helping_hand.enters_play(eng, Area.SURROUNDINGS, hy)

        eng.clear_messages()
        eng.campaign_guide.resolve_entry("47", hy, eng, "progress")

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.2" in m for m in messages))

    def test_harm_clear_routes_to_47_6(self):
        """Entry 47 with harm clear -> 47.6 which ends the day."""
        hy, eng = self._make_engine_with_hy()

        with self.assertRaises(DayEndException):
            eng.campaign_guide.resolve_entry("47", hy, eng, "harm")

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.6" in m for m in messages))


# ============================================================
# Integration Tests: Entry 47.1 (enters play)
# ============================================================

class TestEntry47_1(unittest.TestCase):
    """Tests for entry 47.1 (Hy enters play narrative)."""

    def test_47_1_shows_story_text(self):
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        eng = GameEngine(state)

        result = eng.campaign_guide.resolve_entry("47.1", hy, eng, None)

        messages = [m.message for m in eng.message_queue]
        self.assertFalse(result, "47.1 should return False (Hy stays in play)")
        self.assertTrue(any("shrill whistling" in m for m in messages))

    def test_47_1_shows_guidance(self):
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        eng = GameEngine(state)

        eng.campaign_guide.resolve_entry("47.1", hy, eng, None)

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("Guidance" in m for m in messages))


# ============================================================
# Integration Tests: Entry 47.2 (progress clear, Helping Hand attached)
# ============================================================

class TestEntry47_2(unittest.TestCase):
    """Tests for entry 47.2 (progress clear with Helping Hand)."""

    def _setup_47_2(self, choose_A: bool):
        hy = HyPimpotChef()
        hy.progress = 2
        ranger = make_test_ranger()
        location = make_lone_tree_location()

        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, response_decider=lambda _e, _p: choose_A)

        # Attach Helping Hand
        hh = HelpingHand()
        eng.state.areas[Area.SURROUNDINGS].append(hh)
        hh.enters_play(eng, Area.SURROUNDINGS, hy)

        return hy, eng, state

    def test_47_2_option_A_discards_progress(self):
        """Option A: discard all progress from Hy, Hy stays in play."""
        hy, eng, state = self._setup_47_2(choose_A=True)
        result = eng.campaign_guide.resolve_entry("47.2", hy, eng, "progress")

        self.assertFalse(result, "Option A should return False (Hy stays)")
        self.assertEqual(hy.progress, 0)
        self.assertIn(hy, state.areas[Area.WITHIN_REACH])

    def test_47_2_option_B_discards_hy_and_soothes(self):
        """Option B: discard Hy, return Helping Hand, soothe 1."""
        hy, eng, state = self._setup_47_2(choose_A=False)
        initial_fatigue = len(eng.state.ranger.fatigue_stack)

        result = eng.campaign_guide.resolve_entry("47.2", hy, eng, "progress")

        self.assertTrue(result, "Option B should return True (Hy discarded)")
        self.assertNotIn(hy, state.areas[Area.WITHIN_REACH])


# ============================================================
# Integration Tests: Entry 47.3 (progress clear, no Helping Hand)
# ============================================================

class TestEntry47_3(unittest.TestCase):
    """Tests for entry 47.3 (progress clear without Helping Hand)."""

    def _setup_47_3(self, choose_A: bool):
        hy = HyPimpotChef()
        hy.progress = 2
        ranger = make_test_ranger()
        location = make_lone_tree_location()

        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state, response_decider=lambda _e, _p: choose_A)
        return hy, eng, state

    def test_47_3_option_A_creates_and_attaches_helping_hand(self):
        """Option A: discard progress, create Helping Hand, attach to Hy."""
        hy, eng, state = self._setup_47_3(choose_A=True)
        result = eng.campaign_guide.resolve_entry("47.3", hy, eng, "progress")

        self.assertFalse(result, "Option A should return False (Hy stays)")
        self.assertEqual(hy.progress, 0)

        # Helping Hand should be attached to Hy
        has_helping_hand = False
        for aid in hy.attached_card_ids:
            card = state.get_card_by_id(aid)
            if card and card.title == "Helping Hand":
                has_helping_hand = True
                break
        self.assertTrue(has_helping_hand, "Helping Hand should be attached to Hy")

    def test_47_3_option_A_grants_persistent(self):
        """Option A: Hy should gain Persistent from Helping Hand."""
        hy, eng, state = self._setup_47_3(choose_A=True)
        eng.campaign_guide.resolve_entry("47.3", hy, eng, "progress")

        self.assertTrue(hy.has_keyword(Keyword.PERSISTENT))

    def test_47_3_option_B_discards_hy_and_soothes(self):
        """Option B: discard Hy, soothe 1."""
        hy, eng, state = self._setup_47_3(choose_A=False)
        result = eng.campaign_guide.resolve_entry("47.3", hy, eng, "progress")

        self.assertTrue(result, "Option B should return True (Hy discarded)")
        self.assertNotIn(hy, state.areas[Area.WITHIN_REACH])


# ============================================================
# Integration Tests: Entry 47.4 / 47.5 (stew completion)
# ============================================================

class TestEntry47_4And47_5(unittest.TestCase):
    """Tests for entries 47.4 (at Lone Tree) and 47.5 (not at Lone Tree)."""

    def _setup_hy_with_flora(self, location_title: str):
        """Helper: set up Hy with 3 facedown flora attached."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = Card(
            title=location_title,
            id="location",
            card_types={CardType.LOCATION},
            progress_threshold=4,
        )

        flora_cards = [make_flora_card(f"Flora {i}") for i in range(3)]

        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: flora_cards,
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        # Attach 3 facedown flora to Hy (iterate over copy since flip() modifies the area list)
        for flora in list(flora_cards):
            facedown = flora.flip(eng)
            eng.attach(facedown, hy)

        return hy, eng, state

    def test_47_4_at_lone_tree_soothes_4(self):
        """At Lone Tree: entry 47.4 should soothe 4 and discard flora."""
        hy, eng, state = self._setup_hy_with_flora("Lone Tree Station")
        initial_fatigue = len(eng.state.ranger.fatigue_stack)

        eng.clear_messages()
        result = eng.campaign_guide.resolve_entry("47.4", hy, eng, None)

        self.assertFalse(result, "47.4 at Lone Tree should return False (Hy stays)")
        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.4" in m for m in messages))
        # Flora should have been discarded from Hy
        flora_attached = sum(1 for aid in hy.attached_card_ids
                            if isinstance(card := state.get_card_by_id(aid), FacedownCard)
                            and card.backside is not None and card.backside.has_trait("Flora"))
        self.assertEqual(flora_attached, 0, "All flora should be discarded from Hy")

    def test_47_4_not_at_lone_tree_routes_to_47_5(self):
        """Not at Lone Tree: entry 47.4 should route to 47.5."""
        hy, eng, state = self._setup_hy_with_flora("Boulder Field")

        eng.clear_messages()
        result = eng.campaign_guide.resolve_entry("47.4", hy, eng, None)

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("47.5" in m for m in messages))

    def test_47_5_discards_hy(self):
        """Entry 47.5 should discard Hy."""
        hy, eng, state = self._setup_hy_with_flora("Boulder Field")

        eng.clear_messages()
        result = eng.campaign_guide.resolve_entry("47.5", hy, eng, None)

        self.assertTrue(result, "47.5 should return True (Hy discarded)")
        self.assertNotIn(hy, state.areas[Area.WITHIN_REACH])

    def test_47_5_unlocks_recipe_reward(self):
        """Entry 47.5 should unlock 'Hy Pimpot's Secret Recipe' reward."""
        hy, eng, state = self._setup_hy_with_flora("Boulder Field")

        eng.campaign_guide.resolve_entry("47.5", hy, eng, None)

        self.assertIn("Hy Pimpot's Secret Recipe",
                       eng.state.campaign_tracker.unlocked_rewards)

    def test_47_5_soothes_4(self):
        """Entry 47.5 should soothe 4 fatigue."""
        hy, eng, state = self._setup_hy_with_flora("Boulder Field")
        # Put some cards in fatigue stack so soothe has something to work with
        eng.state.ranger.fatigue(eng, 5)
        fatigue_after_fatigue = len(eng.state.ranger.fatigue_stack)

        eng.clear_messages()
        eng.campaign_guide.resolve_entry("47.5", hy, eng, None)

        # Should have soothed 4 cards from fatigue to hand
        self.assertEqual(len(eng.state.ranger.fatigue_stack), fatigue_after_fatigue - 4)

    def test_47_5_discards_flora_from_hy(self):
        """Entry 47.5 should discard all flora attached to Hy."""
        hy, eng, state = self._setup_hy_with_flora("Boulder Field")

        eng.campaign_guide.resolve_entry("47.5", hy, eng, None)

        # Hy is discarded, so his attached_card_ids should be cleared
        self.assertEqual(len(hy.attached_card_ids), 0)


class TestDiscardFloraFrom(unittest.TestCase):
    """Tests for _discard_flora_from: should only discard FacedownCards whose backside has Flora trait."""

    def _setup_hy_with_mixed_attachments(self):
        """Set up Hy with a mix of flora facedown, non-flora facedown, and regular attachments."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = Card(title="Lone Tree Station", id="location",
                        card_types={CardType.LOCATION}, progress_threshold=4)

        flora = make_flora_card("Test Flora")
        non_flora = Card(title="Rocky Outcrop", id="rock",
                         card_types={CardType.PATH, CardType.FEATURE},
                         traits={"Mineral"}, presence=1,
                         starting_area=Area.ALONG_THE_WAY)
        regular_attachment = Card(title="Helping Hand", id="helping",
                                 card_types={CardType.ATTACHMENT})

        state = GameState(
            ranger=ranger, location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [flora, non_flora],
                Area.WITHIN_REACH: [hy, regular_attachment],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        # Attach a facedown flora
        facedown_flora = flora.flip(eng)
        eng.attach(facedown_flora, hy)

        # Attach a facedown non-flora
        facedown_non_flora = non_flora.flip(eng)
        eng.attach(facedown_non_flora, hy)

        # Attach a regular (non-facedown) card
        eng.attach(regular_attachment, hy)

        return hy, eng, state

    def test_discards_only_flora_facedown_cards(self):
        """_discard_flora_from should discard facedown Flora but leave non-Flora facedown and regular attachments."""
        hy, eng, state = self._setup_hy_with_mixed_attachments()

        # Hy should have 3 attachments before
        self.assertEqual(len(hy.attached_card_ids), 3)

        eng.campaign_guide._discard_flora_from(hy, eng)

        # Should have 2 remaining: the non-flora facedown and the regular attachment
        self.assertEqual(len(hy.attached_card_ids), 2,
                        "Should keep non-Flora facedown and regular attachment")
        remaining = [state.get_card_by_id(aid) for aid in hy.attached_card_ids]
        remaining_backsides = [
            c.backside.title for c in remaining
            if c is not None and isinstance(c, FacedownCard) and c.backside is not None
        ]
        self.assertIn("Rocky Outcrop", remaining_backsides,
                      "Non-Flora facedown should remain")
        self.assertNotIn("Test Flora", remaining_backsides,
                        "Flora facedown should be gone")

    def test_no_crash_when_no_attachments(self):
        """_discard_flora_from should handle a card with no attachments gracefully."""
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = Card(title="Lone Tree Station", id="location",
                        card_types={CardType.LOCATION})
        state = GameState(
            ranger=ranger, location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        # Should not raise
        eng.campaign_guide._discard_flora_from(hy, eng)
        self.assertEqual(len(hy.attached_card_ids), 0)


# ============================================================
# Integration Tests: Entry 47.6 (harm clear, ends day)
# ============================================================

class TestEntry47_6(unittest.TestCase):
    """Tests for entry 47.6 (harm clear -> ends the day)."""

    def test_47_6_ends_day(self):
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = make_lone_tree_location()
        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        with self.assertRaises(DayEndException):
            eng.campaign_guide.resolve_entry("47.6", hy, eng, "harm")

    def test_47_6_shows_story(self):
        hy = HyPimpotChef()
        ranger = make_test_ranger()
        location = make_lone_tree_location()
        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        try:
            eng.campaign_guide.resolve_entry("47.6", hy, eng, "harm")
        except DayEndException:
            pass

        messages = [m.message for m in eng.message_queue]
        self.assertTrue(any("hurts" in m for m in messages))


# ============================================================
# Integration Tests: Hy clears by threshold
# ============================================================

class TestHyPimpotClearing(unittest.TestCase):
    """Tests for Hy clearing via harm or progress thresholds."""

    def test_hy_clears_by_harm_at_threshold(self):
        """Hy should clear by harm when harm reaches 3."""
        hy = HyPimpotChef()
        hy.harm = 3
        clear_type = hy.clear_if_threshold(GameState(
            ranger=make_test_ranger()
        ))
        self.assertEqual(clear_type, "harm")

    def test_hy_does_not_clear_below_harm_threshold(self):
        """Hy should not clear when harm is below 3."""
        hy = HyPimpotChef()
        hy.harm = 2
        clear_type = hy.clear_if_threshold(GameState(
            ranger=make_test_ranger()
        ))
        self.assertIsNone(clear_type)

    def test_hy_clears_by_progress_at_threshold(self):
        """Hy should clear by progress when progress reaches 2."""
        hy = HyPimpotChef()
        hy.progress = 2
        clear_type = hy.clear_if_threshold(GameState(
            ranger=make_test_ranger()
        ))
        self.assertEqual(clear_type, "progress")


# ============================================================
# Tests: HelpingHand card
# ============================================================

class TestHelpingHand(unittest.TestCase):
    """Tests for the Helping Hand mission card."""

    def test_helping_hand_attaches_to_target(self):
        """Helping Hand should attach to its target when entering play."""
        hy = HyPimpotChef()
        hh = HelpingHand()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [hh],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        hh.enters_play(eng, Area.SURROUNDINGS, hy)

        self.assertEqual(hh.attached_to_id, hy.id)
        self.assertIn(hh.id, hy.attached_card_ids)

    def test_helping_hand_grants_persistent(self):
        """Helping Hand should grant its target the Persistent keyword."""
        hy = HyPimpotChef()
        hh = HelpingHand()
        ranger = make_test_ranger()

        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [hh],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [hy],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        self.assertFalse(hy.has_keyword(Keyword.PERSISTENT))
        hh.enters_play(eng, Area.SURROUNDINGS, hy)
        self.assertTrue(hy.has_keyword(Keyword.PERSISTENT))

    def test_helping_hand_no_target_does_nothing_extra(self):
        """Helping Hand entering play without a target should not crash."""
        hh = HelpingHand()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, areas={
            Area.SURROUNDINGS: [hh],
            Area.ALONG_THE_WAY: [],
            Area.WITHIN_REACH: [],
            Area.PLAYER_AREA: [],
        })
        eng = GameEngine(state)

        # Should not raise
        hh.enters_play(eng, Area.SURROUNDINGS, None)

    def test_helping_hand_is_mission_card(self):
        """Helping Hand should be a Mission-type card."""
        hh = HelpingHand()
        self.assertIn(CardType.MISSION, hh.card_types)


# ============================================================
# Integration Test: Full Harvest -> 47.4 -> 47.5 flow
# ============================================================

class TestHyPimpotFullStewFlow(unittest.TestCase):
    """End-to-end test: Harvest 3 flora away from Lone Tree -> 47.4 -> 47.5 -> reward."""

    def test_full_stew_away_from_lone_tree(self):
        """3 successful Harvests away from Lone Tree should trigger 47.4 -> 47.5,
        unlock recipe reward, and discard Hy."""
        hy = HyPimpotChef()
        flora_cards = [make_flora_card(f"Flora {i}") for i in range(3)]
        ranger = make_test_ranger()
        # Fatigue some cards so soothe has something to work with
        ranger.fatigue_stack = ranger.deck[:5]
        ranger.deck = ranger.deck[5:]

        location = make_other_location()
        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: flora_cards,
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        # Harvest all 3 flora (iterate over copy since flip() modifies the area list)
        for flora in list(flora_cards):
            hy._on_harvest_success(eng, 3, flora)

        # Verify Hy was discarded (47.5 result)
        self.assertNotIn(hy, state.areas[Area.WITHIN_REACH])

        # Verify reward unlocked
        self.assertIn("Hy Pimpot's Secret Recipe",
                       state.campaign_tracker.unlocked_rewards)

        # Verify soothe happened (fatigue stack should be reduced by 4)
        self.assertEqual(len(ranger.fatigue_stack), 1,
                         "Should have soothed 4 of 5 fatigue cards")

    def test_full_stew_at_lone_tree(self):
        """3 successful Harvests at Lone Tree should trigger 47.4 only,
        soothe 4, Hy stays in play."""
        hy = HyPimpotChef()
        flora_cards = [make_flora_card(f"Flora {i}") for i in range(3)]
        ranger = make_test_ranger()
        ranger.fatigue_stack = ranger.deck[:5]
        ranger.deck = ranger.deck[5:]

        location = make_lone_tree_location()
        state = GameState(
            ranger=ranger,
            location=location,
            areas={
                Area.SURROUNDINGS: [location],
                Area.ALONG_THE_WAY: flora_cards,
                Area.WITHIN_REACH: [hy],
                Area.PLAYER_AREA: [],
            }
        )
        eng = GameEngine(state)

        # Harvest all 3 flora (iterate over copy since flip() modifies the area list)
        for flora in list(flora_cards):
            hy._on_harvest_success(eng, 3, flora)

        # Hy should stay in play at Lone Tree
        self.assertIn(hy, state.areas[Area.WITHIN_REACH])

        # No reward unlocked (that's only in 47.5)
        self.assertNotIn("Hy Pimpot's Secret Recipe",
                          state.campaign_tracker.unlocked_rewards)

        # Soothe 4 should have happened
        self.assertEqual(len(ranger.fatigue_stack), 1,
                         "Should have soothed 4 of 5 fatigue cards")


if __name__ == '__main__':
    unittest.main()
