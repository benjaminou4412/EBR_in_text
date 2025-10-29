#type:ignore
"""
Tests for exhaust abilities, ranger tokens, and Peerless Pathfinder role card
"""
import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import PeerlessPathfinder, OvergrownThicket, SunberryBramble


class RangerTokenTests(unittest.TestCase):
    """Tests for ranger token movement and tracking"""

    def test_ranger_token_starts_on_role_card(self):
        """Ranger token should initialize on the role card"""
        role = PeerlessPathfinder()
        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(ranger=ranger, role_card=role)

        # Token should be on role card
        self.assertEqual(state.ranger.ranger_token_location, role.id)

    def test_move_ranger_token_to_card(self):
        """Test moving ranger token to a feature"""
        role = PeerlessPathfinder()
        feature = OvergrownThicket()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Move token to feature
        engine.move_ranger_token_to_card(feature)

        # Token should now be on feature
        self.assertEqual(state.ranger.ranger_token_location, feature.id)

        # get_ranger_token_card should return the feature
        token_card = engine.get_ranger_token_card()
        self.assertEqual(token_card.id, feature.id)

    def test_move_ranger_token_to_role(self):
        """Test moving ranger token back to role card"""
        role = PeerlessPathfinder()
        feature = OvergrownThicket()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Move to feature, then back to role
        engine.move_ranger_token_to_card(feature)
        self.assertEqual(state.ranger.ranger_token_location, feature.id)

        engine.move_ranger_token_to_role()
        self.assertEqual(state.ranger.ranger_token_location, role.id)

    def test_ranger_token_returns_when_card_discarded(self):
        """When a card with the ranger token is discarded, token returns to role"""
        role = PeerlessPathfinder()
        feature = OvergrownThicket()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Move token to feature
        engine.move_ranger_token_to_card(feature)
        self.assertEqual(state.ranger.ranger_token_location, feature.id)

        # Discard the feature
        feature.discard_from_play(engine)

        # Token should have returned to role
        self.assertEqual(state.ranger.ranger_token_location, role.id)

    def test_get_ranger_token_card_returns_correct_card(self):
        """get_ranger_token_card should return the card the token is on"""
        role = PeerlessPathfinder()
        feature1 = OvergrownThicket()
        feature2 = SunberryBramble()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature1],
                Area.WITHIN_REACH: [feature2],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Initially on role
        self.assertEqual(engine.get_ranger_token_card().id, role.id)

        # Move to feature1
        engine.move_ranger_token_to_card(feature1)
        self.assertEqual(engine.get_ranger_token_card().id, feature1.id)

        # Move to feature2
        engine.move_ranger_token_to_card(feature2)
        self.assertEqual(engine.get_ranger_token_card().id, feature2.id)


class ExhaustAbilityTests(unittest.TestCase):
    """Tests for exhaust ability mechanics"""

    def test_role_card_has_exhaust_ability(self):
        """Peerless Pathfinder should have an exhaust ability"""
        role = PeerlessPathfinder()
        abilities = role.get_exhaust_abilities()

        self.assertIsNotNone(abilities)
        self.assertEqual(len(abilities), 1)

        ability = abilities[0]
        self.assertFalse(ability.is_test)
        self.assertTrue(ability.is_exhaust)
        self.assertEqual(ability.source_id, role.id)

    def test_exhaust_ability_requires_target(self):
        """Peerless Pathfinder exhaust ability should have target_provider"""
        role = PeerlessPathfinder()
        abilities = role.get_exhaust_abilities()
        ability = abilities[0]

        self.assertIsNotNone(ability.target_provider)

    def test_exhaust_ability_targets_features_only(self):
        """Peerless Pathfinder should only target features"""
        role = PeerlessPathfinder()
        feature = OvergrownThicket()
        being = Card(
            title="Test Being",
            card_types={CardType.BEING},
            presence=2
        )

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [being],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )

        abilities = role.get_exhaust_abilities()
        ability = abilities[0]

        # Should only return features
        targets = ability.target_provider(state)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].id, feature.id)

    def test_ready_card_provides_exhaust_abilities(self):
        """Ready cards should provide their exhaust abilities"""
        from src.registry import provide_exhaust_abilities

        role = PeerlessPathfinder()
        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [role]
            }
        )

        # Ready role should provide ability
        abilities = provide_exhaust_abilities(state)
        self.assertEqual(len(abilities), 1)

    def test_exhausted_card_does_not_provide_exhaust_abilities(self):
        """Exhausted cards should not provide their exhaust abilities"""
        from src.registry import provide_exhaust_abilities

        role = PeerlessPathfinder()
        role.exhausted = True  # Exhaust the role

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [],
                Area.PLAYER_AREA: [role]
            }
        )

        # Exhausted role should NOT provide ability
        abilities = provide_exhaust_abilities(state)
        self.assertEqual(len(abilities), 0)


class PeerlessPathfinderTests(unittest.TestCase):
    """Integration tests for Peerless Pathfinder exhaust ability"""

    def test_peerless_pathfinder_moves_token_and_fatigues(self):
        """Using Peerless Pathfinder should move token and apply fatigue"""
        role = PeerlessPathfinder()
        feature = OvergrownThicket()  # presence = 1

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2},
            deck=[Card(title=f"Card {i}") for i in range(10)]
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Get the exhaust ability
        abilities = role.get_exhaust_abilities()
        ability = abilities[0]

        # Initial state
        self.assertFalse(role.is_exhausted())
        self.assertEqual(state.ranger.ranger_token_location, role.id)
        self.assertEqual(len(state.ranger.fatigue_pile), 0)
        self.assertEqual(len(state.ranger.deck), 10)

        # Activate the ability
        ability.on_success(engine, 0, feature)

        # Role should be exhausted
        self.assertTrue(role.is_exhausted())

        # Token should be on feature
        self.assertEqual(state.ranger.ranger_token_location, feature.id)

        # Should have suffered fatigue equal to feature's presence (1)
        self.assertEqual(len(state.ranger.fatigue_pile), 1)
        self.assertEqual(len(state.ranger.deck), 9)

    def test_peerless_pathfinder_with_high_presence_feature(self):
        """Test with a feature that has higher presence"""
        role = PeerlessPathfinder()
        feature = Card(
            title="Dense Forest",
            card_types={CardType.FEATURE},
            presence=3
        )

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2},
            deck=[Card(title=f"Card {i}") for i in range(10)]
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [],
                Area.WITHIN_REACH: [feature],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Get and activate ability
        abilities = role.get_exhaust_abilities()
        ability = abilities[0]
        ability.on_success(engine, 0, feature)

        # Should suffer 3 fatigue
        self.assertEqual(len(state.ranger.fatigue_pile), 3)
        self.assertEqual(len(state.ranger.deck), 7)

    def test_peerless_pathfinder_multiple_activations(self):
        """Test that exhausted role cannot activate again until readied"""
        role = PeerlessPathfinder()
        feature1 = OvergrownThicket()
        feature2 = SunberryBramble()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2},
            deck=[Card(title=f"Card {i}") for i in range(10)]
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature1],
                Area.WITHIN_REACH: [feature2],
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        from src.registry import provide_exhaust_abilities

        # Should have 1 ability available (role is ready)
        abilities = provide_exhaust_abilities(state)
        self.assertEqual(len(abilities), 1)

        # Activate once
        ability = abilities[0]
        ability.on_success(engine, 0, feature1)
        self.assertTrue(role.is_exhausted())
        self.assertEqual(state.ranger.ranger_token_location, feature1.id)

        # Should have 0 abilities available now (role is exhausted)
        abilities = provide_exhaust_abilities(state)
        self.assertEqual(len(abilities), 0)

        # Ready the role
        role.ready()
        self.assertFalse(role.is_exhausted())

        # Should have 1 ability available again
        abilities = provide_exhaust_abilities(state)
        self.assertEqual(len(abilities), 1)

        # Activate again
        ability = abilities[0]
        ability.on_success(engine, 0, feature2)
        self.assertEqual(state.ranger.ranger_token_location, feature2.id)


class ExhaustAbilityTargetingTests(unittest.TestCase):
    """Tests for exhaust ability targeting (should ignore obstacles)"""

    def test_exhaust_abilities_ignore_obstacles(self):
        """Exhaust abilities should not be blocked by obstacle keyword"""
        role = PeerlessPathfinder()
        obstacle = OvergrownThicket()  # Has Obstacle keyword
        feature = SunberryBramble()

        ranger = RangerState(
            name="Test Ranger",
            aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
        )
        state = GameState(
            ranger=ranger,
            role_card=role,
            areas={
                Area.SURROUNDINGS: [],
                Area.ALONG_THE_WAY: [feature],
                Area.WITHIN_REACH: [obstacle],  # Obstacle is between player and feature
                Area.PLAYER_AREA: [role]
            }
        )
        engine = GameEngine(state)

        # Get exhaust ability
        abilities = role.get_exhaust_abilities()
        ability = abilities[0]

        # Get valid targets (should NOT filter by obstacles for exhaust abilities)
        targets = engine.get_valid_targets(ability)

        # Both features should be valid targets (obstacle doesn't block exhaust)
        self.assertEqual(len(targets), 2)
        target_ids = [t.id for t in targets]
        self.assertIn(obstacle.id, target_ids)
        self.assertIn(feature.id, target_ids)


if __name__ == "__main__":
    unittest.main()
