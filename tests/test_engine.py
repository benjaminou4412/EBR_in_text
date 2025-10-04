import unittest
from src.models import GameState, RangerState, Entity, Aspect, Symbol, Approach
from src.engine import GameEngine


def fixed_draw(mod : int, sym: Symbol):
    return lambda: (mod, sym)


class EngineTests(unittest.TestCase):
    def test_thicket_progress_and_energy(self):
        # Setup state: one feature (thicket), ranger with two exploration cards in hand
        thicket = Entity(id="woods-011-overgrown-thicket", title="Overgrown Thicket", entity_type="Feature", presence=1, progress_threshold=2)
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Create two pseudo cards with Exploration+1 each
        from src.models import Card, ApproachIcons
        ranger.hand = [
            Card(id="c1", title="E+1", card_type="moment", approach=ApproachIcons({Approach.EXPLORATION: 1})),
            Card(id="c2", title="E+1", card_type="moment", approach=ApproachIcons({Approach.EXPLORATION: 1})),
        ]
        state = GameState(ranger=ranger, entities=[thicket])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))


        # Perform action using the engine API directly
        from src.models import Action
        act = Action(
            id="t1",
            name="thicket",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
        eng.perform_action(
            act, 
            decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision(energy = 1,hand_indices = [0, 1]), 
            target_id=None)

        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(thicket.progress, 3)
        self.assertEqual(len(state.ranger.hand), 0)
    
    def test_single_energy(self):
        # Setup state: one feature (thicket), ranger with no cards in hand
        thicket = Entity(id="woods-011-overgrown-thicket", title="Overgrown Thicket", entity_type="Feature", presence=1, progress_threshold=2)
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        # Create two pseudo cards with Exploration+1 each
        state = GameState(ranger=ranger, entities=[thicket])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action using the engine API directly
        from src.models import Action
        act = Action(
            id="t1",
            name="thicket",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
        eng.perform_action(
            act, 
            decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision(energy = 1, hand_indices = []), 
            target_id=None)

        self.assertEqual(state.ranger.energy[Aspect.AWA], 2)
        self.assertEqual(thicket.progress, 1)
        self.assertEqual(len(state.ranger.hand), 0)

    def test_traverse_feature(self):
        feat = Entity(id="feat1", title="Feature A", entity_type="Feature", presence=1, progress_threshold=3)
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        from src.models import Card, ApproachIcons
        ranger.hand = [Card(id="e1", title="E+1", card_type="moment", approach=ApproachIcons({Approach.EXPLORATION: 1}))]
        state = GameState(ranger=ranger, entities=[feat])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.CREST))

        from src.models import Action
        act = Action(
            id="t2",
            name="traverse",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: max(1, feat.presence),
            on_success=lambda s, eff, _t: feat.add_progress(eff),
            on_fail=lambda s, _t: setattr(state.ranger, "injury", state.ranger.injury + 1),
        )
        eng.perform_action(
            act, 
            decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision(energy = 1, hand_indices = [0]), 
            target_id=None)

        self.assertEqual(state.ranger.energy[Aspect.FIT], 1)
        self.assertEqual(feat.progress, 2)
        self.assertEqual(state.ranger.injury, 0)

    def test_clear_on_progress_threshold(self):
        # Setup: Feature with progress_threshold=2
        feature = Entity(
            id="test-feature",
            title="Test Feature",
            entity_type="Feature",
            presence=1,
            progress_threshold=2,
        )
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(ranger=ranger, entities=[feature])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action that adds exactly enough progress to clear (1 energy + 1 icon = 2 effort)
        from src.models import Action, Card, ApproachIcons, CommitDecision
        ranger.hand = [Card(id="c1", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1}))]
        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: feature.add_progress(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Feature should be removed from entities and moved to path_discard
        self.assertEqual(len(state.entities), 0, "Feature should be removed from entities")
        self.assertEqual(len(state.path_discard), 1, "Feature should be in path_discard")
        self.assertEqual(state.path_discard[0].id, "test-feature", "Cleared feature should be the one we added progress to")

    def test_clear_on_harm_threshold(self):
        # Setup: Being with harm_threshold=2
        being = Entity(
            id="test-being",
            title="Test Being",
            entity_type="Being",
            presence=1,
            harm_threshold=2,
        )
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 5, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        from src.models import Card, ApproachIcons
        # Add a card with +1 Conflict icon so we get 2 total effort (1 energy + 1 icon)
        ranger.hand = [Card(id="c1", title="Conflict+1", card_type="moment", approach=ApproachIcons({Approach.CONFLICT: 1}))]
        state = GameState(ranger=ranger, entities=[being])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Perform action that adds exactly enough harm to clear (1 energy + 1 icon = 2 effort = 2 harm)
        from src.models import Action, CommitDecision
        act = Action(
            id="test-harm",
            name="test harm",
            aspect=Aspect.AWA,
            approach=Approach.CONFLICT,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: being.add_harm(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[0]), target_id=None)

        # Assert: Being should be removed from entities and moved to path_discard
        self.assertEqual(len(state.entities), 0, "Being should be removed from entities")
        self.assertEqual(len(state.path_discard), 1, "Being should be in path_discard")
        self.assertEqual(state.path_discard[0].id, "test-being", "Cleared being should be the one we added harm to")

    def test_no_clear_below_threshold(self):
        # Setup: Feature with progress_threshold=3
        feature = Entity(
            id="test-feature-2",
            title="Test Feature 2",
            entity_type="Feature",
            presence=1,
            progress_threshold=3,
        )
        ranger = RangerState(name="Ranger", hand=[], energy={Aspect.AWA: 3, Aspect.FIT: 2, Aspect.SPI: 2, Aspect.FOC: 1})
        state = GameState(ranger=ranger, entities=[feature])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, Symbol.SUN))

        # Add progress that doesn't reach threshold (only 1 effort)
        from src.models import Action, CommitDecision
        act = Action(
            id="test-action",
            name="test",
            aspect=Aspect.AWA,
            approach=Approach.EXPLORATION,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: feature.add_progress(eff),
        )
        eng.perform_action(act, decision=CommitDecision(energy=1, hand_indices=[]), target_id=None)

        # Assert: Feature should still be in entities (not cleared)
        self.assertEqual(len(state.entities), 1, "Feature should still be in play")
        self.assertEqual(len(state.path_discard), 0, "Nothing should be discarded")
        self.assertEqual(feature.progress, 1, "Feature should have 1 progress")


if __name__ == '__main__':
    unittest.main()
