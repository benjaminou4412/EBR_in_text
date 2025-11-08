#type:ignore
"""
Tests for the attachment system and Caustic Mulcher card.
"""
import unittest
from src.models import *
from src.engine import GameEngine
from src.cards import CausticMulcher, OvergrownThicket, PeerlessPathfinder


def make_test_ranger():
    """Helper to create a basic test ranger"""
    return RangerState(
        name="Test Ranger",
        aspects={Aspect.AWA: 2, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 2}
    )


class AttachmentMechanicsTests(unittest.TestCase):
    """Tests for basic attach/unattach functionality."""

    def test_attach_moves_card_to_same_area(self):
        """Test that attaching a card moves it to the same area as the target."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        # Create attachment and target
        attachment = Card(
            id="attachment_1",
            title="Test Attachment",
            card_types={CardType.ATTACHMENT},
            keywords=set()
        )
        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )

        # Place target in play, attachment in hand
        state.areas[Area.WITHIN_REACH].append(target)
        state.ranger.hand.append(attachment)

        # Attach - attachment stays in hand but is attached
        engine.attach(attachment, target)

        # Verify attachment tracking (attachment can stay in hand while attached)
        self.assertEqual(attachment.attached_to_id, target.id)
        self.assertEqual(target.attached_card_ids, [attachment.id])

    def test_attach_already_in_same_area(self):
        """Test attaching when both cards are already in the same area."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        attachment = Card(
            id="attachment_1",
            title="Test Attachment",
            card_types={CardType.ATTACHMENT},
            keywords=set()
        )
        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )

        # Both cards start in path_play
        state.areas[Area.WITHIN_REACH].extend([attachment, target])

        engine.attach(attachment, target)

        # Verify both still in path_play
        self.assertIn(attachment, state.areas[Area.WITHIN_REACH])
        self.assertIn(target, state.areas[Area.WITHIN_REACH])
        self.assertEqual(attachment.attached_to_id, target.id)
        self.assertEqual(target.attached_card_ids, [attachment.id])

    def test_unattach_auto_discards_attachment_type(self):
        """Test that unattaching an ATTACHMENT card type auto-discards it."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        attachment = Card(
            id="attachment_1",
            title="Test Attachment",
            card_types={CardType.RANGER, CardType.ATTACHMENT},
            keywords=set()
        )
        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )

        state.areas[Area.WITHIN_REACH].extend([attachment, target])
        engine.attach(attachment, target)

        # Unattach
        engine.unattach(attachment)

        # Verify attachment was auto-discarded
        self.assertNotIn(attachment, state.areas[Area.WITHIN_REACH])
        self.assertIn(attachment, state.ranger.discard)
        self.assertIsNone(attachment.attached_to_id)
        self.assertNotIn(attachment.id, target.attached_card_ids)

    def test_unattach_non_attachment_type_stays_in_play(self):
        """Test that unattaching a non-ATTACHMENT card keeps it in play."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        # Being card (not ATTACHMENT type)
        being = Card(
            id="being_1",
            title="Test Being",
            card_types={CardType.BEING}
        )
        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )

        state.areas[Area.WITHIN_REACH].extend([being, target])
        engine.attach(being, target)

        # Unattach
        engine.unattach(being)

        # Verify being stays in play
        self.assertIn(being, state.areas[Area.WITHIN_REACH])
        self.assertNotIn(being, state.path_discard)
        self.assertIsNone(being.attached_to_id)
        self.assertNotIn(being.id, target.attached_card_ids)

    def test_recursive_discard_cascade(self):
        """Test that discarding a card with attachments recursively discards them."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )
        attachment1 = Card(
            id="attachment_1",
            title="Attachment 1",
            card_types={CardType.RANGER, CardType.ATTACHMENT},
            keywords=set()
        )
        attachment2 = Card(
            id="attachment_2",
            title="Attachment 2",
            card_types={CardType.RANGER, CardType.ATTACHMENT},
            keywords=set()
        )

        state.areas[Area.WITHIN_REACH].extend([target, attachment1, attachment2])
        engine.attach(attachment1, target)
        engine.attach(attachment2, target)

        # Discard target
        target.discard_from_play(engine)

        # Verify all were discarded
        self.assertIn(target, state.path_discard)
        self.assertIn(attachment1, state.ranger.discard)
        self.assertIn(attachment2, state.ranger.discard)
        self.assertEqual(len(state.areas[Area.WITHIN_REACH]), 0)

    def test_multiple_attachments_on_one_card(self):
        """Test multiple cards can attach to the same target."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        target = Card(
            id="target_1",
            title="Test Target",
            card_types={CardType.PATH},
            keywords=set()
        )
        attachment1 = Card(id="att_1", title="Att 1", card_types={CardType.ATTACHMENT}, keywords=set())
        attachment2 = Card(id="att_2", title="Att 2", card_types={CardType.ATTACHMENT}, keywords=set())
        attachment3 = Card(id="att_3", title="Att 3", card_types={CardType.ATTACHMENT}, keywords=set())

        state.areas[Area.WITHIN_REACH].extend([target, attachment1, attachment2, attachment3])

        engine.attach(attachment1, target)
        engine.attach(attachment2, target)
        engine.attach(attachment3, target)

        self.assertEqual(target.attached_card_ids, ["att_1", "att_2", "att_3"])
        self.assertEqual(attachment1.attached_to_id, target.id)
        self.assertEqual(attachment2.attached_to_id, target.id)
        self.assertEqual(attachment3.attached_to_id, target.id)


class CausticMulcherConstantAbilitiesTests(unittest.TestCase):
    """Tests for Caustic Mulcher's constant abilities."""

    def test_attached_beings_do_not_ready(self):
        """Test that beings attached to Caustic Mulcher cannot ready."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Test Being",
            card_types={CardType.BEING}
        )

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Attach being to mulcher
        engine.attach(being, mulcher)
        being.exhausted = True

        # Try to ready
        being.ready(engine)

        # Should still be exhausted
        self.assertTrue(being.exhausted)

    def test_non_attached_beings_ready_normally(self):
        """Test that beings not attached to Caustic Mulcher can ready normally."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Test Being",
            card_types={CardType.BEING}
        )

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Don't attach - just exhaust being
        being.exhausted = True

        # Try to ready
        being.ready(engine)

        # Should be ready
        self.assertFalse(being.exhausted)

    def test_ranger_token_prevents_travel_when_on_mulcher(self):
        """Test that ranger token on Caustic Mulcher prevents travel."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Move ranger token to mulcher
        engine.move_ranger_token_to_card(mulcher)

        # Check if travel is prevented
        prevention_abilities = engine.get_constant_abilities_by_type(
            ConstantAbilityType.PREVENT_TRAVEL
        )

        # Should have one active prevention ability
        self.assertEqual(len(prevention_abilities), 1)
        self.assertTrue(prevention_abilities[0].is_active(state, mulcher))

    def test_ranger_token_allows_travel_when_not_on_mulcher(self):
        """Test that travel is allowed when ranger token is not on Caustic Mulcher."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Ranger token starts on role (not on mulcher)

        # Check if travel is prevented
        prevention_abilities = engine.get_constant_abilities_by_type(
            ConstantAbilityType.PREVENT_TRAVEL
        )

        # Should have one ability but it should not be active
        self.assertEqual(len(prevention_abilities), 1)
        self.assertFalse(prevention_abilities[0].is_active(state, mulcher))

    def test_ranger_token_cannot_move_from_mulcher(self):
        """Test that ranger token cannot move from Caustic Mulcher."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        other_card = Card(
            id="other_card",
            title="Other Card",
            card_types={CardType.PATH},
            keywords=set()
        )
        state.areas[Area.WITHIN_REACH].extend([mulcher, other_card])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Move ranger token to mulcher
        engine.move_ranger_token_to_card(mulcher)

        # Check if token movement is prevented
        prevention_abilities = engine.get_constant_abilities_by_type(
            ConstantAbilityType.PREVENT_RANGER_TOKEN_MOVE
        )

        # Should have one active prevention ability
        self.assertEqual(len(prevention_abilities), 1)
        self.assertTrue(prevention_abilities[0].is_active(state, mulcher))

    def test_ranger_token_movement_blocked_from_mulcher(self):
        """Test that attempting to move ranger token from Caustic Mulcher actually fails."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        other_card = Card(
            id="other_card",
            title="Other Card",
            card_types={CardType.PATH},
            keywords=set()
        )
        state.areas[Area.WITHIN_REACH].extend([mulcher, other_card])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Move ranger token to mulcher
        engine.move_ranger_token_to_card(mulcher)
        self.assertEqual(state.ranger.ranger_token_location, mulcher.id)

        # Attempt to move ranger token to other card - should fail
        result = engine.move_ranger_token_to_card(other_card)
        self.assertFalse(result, "Ranger token movement should be blocked")
        self.assertEqual(state.ranger.ranger_token_location, mulcher.id,
                        "Ranger token should still be on mulcher")

    def test_ranger_token_movement_blocked_even_when_exhausted(self):
        """Test that ranger token cannot move from Caustic Mulcher even when exhausted.

        The ranger token movement prevention ability is ALWAYS active, not conditional
        on the mulcher being ready.
        """
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        other_card = Card(
            id="other_card",
            title="Other Card",
            card_types={CardType.PATH},
            keywords=set()
        )
        state.areas[Area.WITHIN_REACH].extend([mulcher, other_card])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Move ranger token to mulcher and exhaust it
        engine.move_ranger_token_to_card(mulcher)
        mulcher.exhaust()
        self.assertTrue(mulcher.is_exhausted())

        # Attempt to move ranger token - should still be blocked even when exhausted
        result = engine.move_ranger_token_to_card(other_card)
        self.assertFalse(result, "Ranger token movement should be blocked even when mulcher is exhausted")
        self.assertEqual(state.ranger.ranger_token_location, mulcher.id,
                        "Ranger token should still be on mulcher")

    def test_ranger_token_can_move_when_not_on_mulcher(self):
        """Test that ranger token CAN move normally when not on Caustic Mulcher."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        card1 = Card(
            id="card1",
            title="Card 1",
            card_types={CardType.PATH},
            keywords=set()
        )
        card2 = Card(
            id="card2",
            title="Card 2",
            card_types={CardType.PATH},
            keywords=set()
        )
        state.areas[Area.WITHIN_REACH].extend([mulcher, card1, card2])

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Move ranger token to card1 (not the mulcher)
        engine.move_ranger_token_to_card(card1)
        self.assertEqual(state.ranger.ranger_token_location, card1.id)

        # Should be able to move to card2 - mulcher's ability doesn't apply
        result = engine.move_ranger_token_to_card(card2)
        self.assertTrue(result, "Ranger token movement should succeed when not on mulcher")
        self.assertEqual(state.ranger.ranger_token_location, card2.id)


class CausticMulcherWrestTests(unittest.TestCase):
    """Tests for Caustic Mulcher's Wrest test."""

    def test_wrest_success_with_token_only(self):
        """Test Wrest success when only token is present (no beings)."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)
        engine.move_ranger_token_to_card(mulcher)

        tests = mulcher.get_tests()
        wrest_test = tests[0]

        # Perform success callback
        wrest_test.on_success(engine, 0, mulcher)

        # Mulcher should be exhausted
        self.assertTrue(mulcher.exhausted)

        # Token should be returned to role
        self.assertEqual(state.ranger.ranger_token_location, role.id)

    def test_wrest_success_with_beings_only(self):
        """Test Wrest success when only beings are present (no token)."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING}
        )

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])
        engine.attach(being, mulcher)

        tests = mulcher.get_tests()
        wrest_test = tests[0]

        # Perform success callback
        wrest_test.on_success(engine, 0, mulcher)

        # Mulcher should be exhausted
        self.assertTrue(mulcher.exhausted)

        # Being should be unattached
        self.assertIsNone(being.attached_to_id)
        self.assertNotIn(being.id, mulcher.attached_card_ids)

    def test_wrest_success_with_neither(self):
        """Test Wrest success when neither token nor beings are present."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        tests = mulcher.get_tests()
        wrest_test = tests[0]

        # Perform success callback
        wrest_test.on_success(engine, 0, mulcher)

        # Mulcher should be exhausted
        self.assertTrue(mulcher.exhausted)


class CausticMulcherChallengeEffectsTests(unittest.TestCase):
    """Tests for Caustic Mulcher's Sun and Crest challenge effects."""

    def test_sun_effect_with_being_in_play(self):
        """Test Sun effect when a being is in the path."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING}
        )

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])

        # Execute Sun effect
        cleared = mulcher._sun_effect(engine)

        # Being should be attached to mulcher
        self.assertEqual(being.attached_to_id, mulcher.id)
        self.assertIn(being.id, mulcher.attached_card_ids)

        # Should return True (effect resolved)
        self.assertTrue(cleared)

    def test_sun_effect_with_no_beings(self):
        """Test Sun effect when no beings are in play."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        # Execute Sun effect
        cleared = mulcher._sun_effect(engine)

        # Ranger token should move to mulcher
        self.assertEqual(state.ranger.ranger_token_location, mulcher.id)

        # Should return True (effect resolved)
        self.assertTrue(cleared)

    def test_sun_effect_with_being_and_token_already_on_mulcher(self):
        """Test Sun effect when being exists and token is already on mulcher."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING}
        )

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])
        engine.move_ranger_token_to_card(mulcher)

        # Execute Sun effect
        cleared = mulcher._sun_effect(engine)

        # Being should be attached (preference over moving token)
        self.assertEqual(being.attached_to_id, mulcher.id)
        self.assertIn(being.id, mulcher.attached_card_ids)

        # Token should still be on mulcher
        self.assertEqual(state.ranger.ranger_token_location, mulcher.id)

        self.assertTrue(cleared)

    def test_crest_effect_with_attached_beings(self):
        """Test Crest effect harms attached beings."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        being1 = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING}
        )
        being2 = Card(
            id="being_2",
            title="Being 2",
            card_types={CardType.BEING}
        )

        being1.harm = 0
        being2.harm = 0

        state.areas[Area.WITHIN_REACH].extend([mulcher, being1, being2])
        engine.attach(being1, mulcher)
        engine.attach(being2, mulcher)

        # Execute Crest effect
        cleared = mulcher._crest_effect(engine)

        # Both beings should have 1 harm
        self.assertEqual(being1.harm, 1)
        self.assertEqual(being2.harm, 1)

        self.assertTrue(cleared)

    def test_crest_effect_with_ranger_token(self):
        """Test Crest effect injures ranger when token is on mulcher."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)
        engine.move_ranger_token_to_card(mulcher)

        initial_injury_count = state.ranger.injury

        # Execute Crest effect
        cleared = mulcher._crest_effect(engine)

        # Ranger should have gained 1 injury
        self.assertEqual(state.ranger.injury, initial_injury_count + 1)

        self.assertTrue(cleared)

    def test_crest_effect_with_both_beings_and_token(self):
        """Test Crest effect with both attached beings and ranger token."""
        role = PeerlessPathfinder()
        ranger = make_test_ranger()
        state = GameState(ranger=ranger, role_card=role)
        engine = GameEngine(state)

        # Add role to player area so it can be found
        state.areas[Area.PLAYER_AREA].append(role)

        mulcher = CausticMulcher()
        being = Card(
            id="being_1",
            title="Being 1",
            card_types={CardType.BEING}
        )
        being.harm = 0

        state.areas[Area.WITHIN_REACH].extend([mulcher, being])
        engine.attach(being, mulcher)
        engine.move_ranger_token_to_card(mulcher)

        initial_injury_count = state.ranger.injury

        # Execute Crest effect
        cleared = mulcher._crest_effect(engine)

        # Being should have harm
        self.assertEqual(being.harm, 1)

        # Ranger should have injury
        self.assertEqual(state.ranger.injury, initial_injury_count + 1)

        self.assertTrue(cleared)

    def test_crest_effect_with_neither(self):
        """Test Crest effect when neither beings nor token are present."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        initial_injury_count = state.ranger.injury

        # Execute Crest effect
        cleared = mulcher._crest_effect(engine)

        # No changes expected
        self.assertEqual(state.ranger.injury, initial_injury_count)

        self.assertFalse(cleared)


class CausticMulcherCleanupTests(unittest.TestCase):
    """Tests for Caustic Mulcher ability cleanup on discard."""

    def test_abilities_removed_when_mulcher_discarded(self):
        """Test that constant abilities are removed when Caustic Mulcher is discarded."""
        ranger = make_test_ranger()
        state = GameState(ranger=ranger)
        engine = GameEngine(state)

        mulcher = CausticMulcher()
        state.areas[Area.WITHIN_REACH].append(mulcher)

        # Register abilities
        mulcher.enters_play(engine, Area.WITHIN_REACH)

        # Verify abilities are registered
        self.assertGreater(len(engine.get_constant_abilities_by_type(ConstantAbilityType.PREVENT_READYING)), 0)
        self.assertGreater(len(engine.get_constant_abilities_by_type(ConstantAbilityType.PREVENT_TRAVEL)), 0)
        self.assertGreater(len(engine.get_constant_abilities_by_type(ConstantAbilityType.PREVENT_RANGER_TOKEN_MOVE)), 0)

        # Discard mulcher
        mulcher.discard_from_play(engine)

        # Abilities should be removed
        self.assertEqual(len([a for a in engine.constant_abilities if a.source_card_id == mulcher.id]), 0)


if __name__ == "__main__":
    unittest.main()
