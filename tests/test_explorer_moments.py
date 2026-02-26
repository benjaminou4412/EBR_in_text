#type:ignore
import unittest
from ebr.models import *
from ebr.engine import GameEngine
from ebr.cards import ShareintheValleysSecrets, CradledbytheEarth, AffordedByNature
from tests.test_utils import MockChallengeDeck, make_challenge_card


class ShareInTheValleysSecretsTests(unittest.TestCase):
    """Tests for Share in the Valley's Secrets non-response moment"""

    def test_exhausts_obstacles_and_fatigues_equal_amount(self):
        """Test that Share in the Valley's Secrets exhausts all obstacles and fatigues equal to count"""
        svs = ShareintheValleysSecrets()

        # Create three obstacle cards (obstacles are path cards with Obstacle keyword)
        obstacle1 = Card(
            title="Obstacle 1",
            id="obs1",
            card_types={CardType.PATH},
            keywords={Keyword.OBSTACLE}
        )
        obstacle2 = Card(
            title="Obstacle 2",
            id="obs2",
            card_types={CardType.PATH},
            keywords={Keyword.OBSTACLE}
        )
        obstacle3 = Card(
            title="Obstacle 3",
            id="obs3",
            card_types={CardType.PATH},
            keywords={Keyword.OBSTACLE}
        )

        # Create non-obstacle card
        feature = Card(
            title="Feature",
            id="feat1",
            card_types={CardType.PATH, CardType.FEATURE}
        )

        # Create ranger with 10 cards in deck
        ranger = RangerState(
            name="Test Ranger",
            hand=[svs],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [obstacle1],
                Area.ALONG_THE_WAY: [obstacle2, feature],
                Area.WITHIN_REACH: [obstacle3],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Verify obstacles start ready
        self.assertTrue(obstacle1.is_ready())
        self.assertTrue(obstacle2.is_ready())
        self.assertTrue(obstacle3.is_ready())
        self.assertFalse(feature.is_exhausted())

        # Play Share in the Valley's Secrets (no targeting)
        svs.play(eng, target=None)

        # Verify all obstacles are exhausted
        self.assertTrue(obstacle1.is_exhausted())
        self.assertTrue(obstacle2.is_exhausted())
        self.assertTrue(obstacle3.is_exhausted())

        # Verify non-obstacle is not exhausted
        self.assertFalse(feature.is_exhausted())

        # Verify ranger suffered 3 fatigue (equal to obstacles exhausted)
        self.assertEqual(len(ranger.fatigue_stack), 3)
        self.assertEqual(len(ranger.deck), 7)

        # Verify card was discarded
        self.assertNotIn(svs, ranger.hand)
        self.assertIn(svs, ranger.discard)

    def test_no_obstacles_means_no_fatigue(self):
        """Test that if no obstacles exist, no fatigue is suffered"""
        svs = ShareintheValleysSecrets()

        feature = Card(
            title="Feature",
            id="feat1",
            card_types={CardType.PATH, CardType.FEATURE}
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[svs],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        svs.play(eng, target=None)

        # Verify no fatigue was suffered
        self.assertEqual(len(ranger.fatigue_stack), 0)
        self.assertEqual(len(ranger.deck), 10)

    def test_already_exhausted_obstacles_not_counted(self):
        """Test that already-exhausted obstacles are not exhausted again and don't count for fatigue"""
        svs = ShareintheValleysSecrets()

        obstacle1 = Card(
            title="Obstacle 1",
            id="obs1",
            card_types={CardType.PATH},
            keywords={Keyword.OBSTACLE}
        )
        obstacle2 = Card(
            title="Obstacle 2",
            id="obs2",
            card_types={CardType.PATH},
            keywords={Keyword.OBSTACLE}
        )

        # Exhaust obstacle1 before the test
        obstacle1.exhaust()

        ranger = RangerState(
            name="Test Ranger",
            hand=[svs],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [obstacle1],
                Area.ALONG_THE_WAY: [obstacle2],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        svs.play(eng, target=None)

        # Verify only 1 fatigue (obstacle2 was the only one exhausted)
        self.assertEqual(len(ranger.fatigue_stack), 1)

        # Both should be exhausted now
        self.assertTrue(obstacle1.is_exhausted())
        self.assertTrue(obstacle2.is_exhausted())


class CradledByTheEarthTests(unittest.TestCase):
    """Tests for Cradled by the Earth non-response moment"""

    def test_soothes_fatigue_equal_to_trail_progress(self):
        """Test that Cradled by the Earth soothes fatigue equal to trail progress"""
        cbe = CradledbytheEarth()

        # Create a trail with 3 progress
        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=3
        )

        # Create ranger with fatigue
        fatigue_cards = [Card(title=f"Fatigue {i}", id=f"fat{i}") for i in range(5)]
        ranger = RangerState(
            name="Test Ranger",
            hand=[cbe],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)],
            fatigue_stack=fatigue_cards
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Verify starting fatigue
        self.assertEqual(len(ranger.fatigue_stack), 5)
        self.assertEqual(len(ranger.hand), 1)  # Just the moment card

        # Play Cradled by the Earth targeting the trail
        cbe.play(eng, target=trail)

        # Verify 3 fatigue was soothed (moved to hand)
        self.assertEqual(len(ranger.fatigue_stack), 2)
        # Hand should have 3 cards from soothing (moment was discarded)
        self.assertEqual(len(ranger.hand), 3)

        # Verify the card was discarded
        self.assertNotIn(cbe, ranger.hand)
        self.assertIn(cbe, ranger.discard)

    def test_trail_with_zero_progress_soothes_zero(self):
        """Test that a trail with 0 progress soothes 0 fatigue"""
        cbe = CradledbytheEarth()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=0
        )

        fatigue_cards = [Card(title=f"Fatigue {i}", id=f"fat{i}") for i in range(3)]
        ranger = RangerState(
            name="Test Ranger",
            hand=[cbe],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)],
            fatigue_stack=fatigue_cards
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        cbe.play(eng, target=trail)

        # Verify no fatigue was soothed
        self.assertEqual(len(ranger.fatigue_stack), 3)
        self.assertEqual(len(ranger.hand), 0)  # Moment was discarded

    def test_handles_no_target_gracefully(self):
        """Test that playing with no target doesn't crash"""
        cbe = CradledbytheEarth()

        ranger = RangerState(
            name="Test Ranger",
            hand=[cbe],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)],
            fatigue_stack=[Card(title=f"Fatigue {i}", id=f"fat{i}") for i in range(3)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play with no target
        cbe.play(eng, target=None)

        # Verify no fatigue was soothed
        self.assertEqual(len(ranger.fatigue_stack), 3)

        # Verify card was still discarded
        self.assertNotIn(cbe, ranger.hand)
        self.assertIn(cbe, ranger.discard)

    def test_soothes_limited_by_fatigue_stack(self):
        """Test that soothing is limited by available fatigue"""
        cbe = CradledbytheEarth()

        # Trail with 5 progress but only 2 fatigue available
        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=5
        )

        fatigue_cards = [Card(title=f"Fatigue {i}", id=f"fat{i}") for i in range(2)]
        ranger = RangerState(
            name="Test Ranger",
            hand=[cbe],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)],
            fatigue_stack=fatigue_cards
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        cbe.play(eng, target=trail)

        # Verify only 2 fatigue was soothed (all available)
        self.assertEqual(len(ranger.fatigue_stack), 0)
        self.assertEqual(len(ranger.hand), 2)


class AffordedByNatureTests(unittest.TestCase):
    """Tests for Afforded by Nature non-response moment"""

    def test_moves_progress_to_harm(self):
        """Test that Afforded by Nature moves progress from trail to harm on being"""
        abn = AffordedByNature()

        # Trail with 4 progress
        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=4
        )

        # Being with 0 harm
        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Use default choosers: max amount (4), first being
        eng = GameEngine(state)

        # Verify initial state
        self.assertEqual(trail.progress, 4)
        self.assertEqual(being.harm, 0)

        # Play Afforded by Nature
        abn.play(eng, target=trail)

        # Verify progress removed from trail
        self.assertEqual(trail.progress, 0)

        # Verify harm added to being
        self.assertEqual(being.harm, 4)

        # Verify card was discarded
        self.assertNotIn(abn, ranger.hand)
        self.assertIn(abn, ranger.discard)

    def test_can_choose_partial_amount(self):
        """Test that player can choose to move less than maximum progress"""
        abn = AffordedByNature()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=5
        )

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Custom amount chooser that chooses 2 instead of max
        def choose_2(_eng, _min, _max, _prompt):
            return 2

        eng = GameEngine(state, amount_chooser=choose_2)

        # Play the card
        abn.play(eng, target=trail)

        # Verify only 2 progress moved
        self.assertEqual(trail.progress, 3)
        self.assertEqual(being.harm, 2)

    def test_can_choose_zero_amount(self):
        """Test that player can choose to move 0 progress"""
        abn = AffordedByNature()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=3
        )

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Custom amount chooser that chooses 0
        def choose_0(_eng, _min, _max, _prompt):
            return 0

        eng = GameEngine(state, amount_chooser=choose_0)

        # Play the card
        abn.play(eng, target=trail)

        # Verify no progress moved
        self.assertEqual(trail.progress, 3)
        self.assertEqual(being.harm, 0)

        # Card still gets discarded
        self.assertNotIn(abn, ranger.hand)
        self.assertIn(abn, ranger.discard)

    def test_multiple_beings_choice(self):
        """Test that player can choose which being to harm when multiple exist"""
        abn = AffordedByNature()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=3
        )

        being1 = Card(
            title="Being 1",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        being2 = Card(
            title="Being 2",
            id="being2",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [being1, being2],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        # Custom card chooser that chooses being2
        def choose_being2(_eng, cards):
            return [c for c in cards if c.title == "Being 2"][0]

        eng = GameEngine(state, card_chooser=choose_being2)

        # Play the card
        abn.play(eng, target=trail)

        # Verify harm went to being2, not being1
        self.assertEqual(being1.harm, 0)
        self.assertEqual(being2.harm, 3)

    def test_no_beings_available(self):
        """Test that card handles no beings gracefully"""
        abn = AffordedByNature()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=5
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        abn.play(eng, target=trail)

        # Verify trail progress unchanged (no being to harm)
        self.assertEqual(trail.progress, 5)

        # Card still gets discarded
        self.assertNotIn(abn, ranger.hand)
        self.assertIn(abn, ranger.discard)

    def test_no_trail_target(self):
        """Test that card handles no trail target gracefully"""
        abn = AffordedByNature()

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play with no target
        abn.play(eng, target=None)

        # Verify being unchanged
        self.assertEqual(being.harm, 0)

        # Card still gets discarded
        self.assertNotIn(abn, ranger.hand)
        self.assertIn(abn, ranger.discard)

    def test_trail_with_zero_progress(self):
        """Test that trail with 0 progress means 0 harm can be dealt"""
        abn = AffordedByNature()

        trail = Card(
            title="Test Trail",
            id="trail1",
            card_types={CardType.PATH, CardType.MISSION},
            traits={"trail"},
            progress_threshold=10,
            progress=0
        )

        being = Card(
            title="Test Being",
            id="being1",
            card_types={CardType.PATH, CardType.BEING},
            harm_threshold=5,
            harm=0
        )

        ranger = RangerState(
            name="Test Ranger",
            hand=[abn],
            aspects={Aspect.AWA: 5, Aspect.FIT: 5, Aspect.SPI: 5, Aspect.FOC: 5},
            deck=[Card(title=f"Card {i}", id=f"card{i}") for i in range(10)]
        )

        state = GameState(
            ranger=ranger,
            areas={
                Area.SURROUNDINGS: [trail],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: []
            }
        )

        eng = GameEngine(state)

        # Play the card
        abn.play(eng, target=trail)

        # Verify no harm added (trail had 0 progress)
        self.assertEqual(being.harm, 0)
        self.assertEqual(trail.progress, 0)


if __name__ == '__main__':
    unittest.main()
