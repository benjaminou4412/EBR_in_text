import unittest
from src.models import GameState, RangerState, Entity
from src.engine import GameEngine


def fixed_draw(mod, sym):
    return lambda: (mod, sym)


class EngineTests(unittest.TestCase):
    def test_thicket_progress_and_energy(self):
        # Setup state: one feature (thicket), ranger with two exploration cards in hand
        thicket = Entity(id="woods-011-overgrown-thicket", title="Overgrown Thicket", entity_type="Feature", presence=1, progress_threshold=2)
        ranger = RangerState(name="Ranger", hand=[], energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
        # Create two pseudo cards with Exploration+1 each
        from src.models import Card, ApproachIcons
        ranger.hand = [
            Card(id="c1", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
            Card(id="c2", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
        ]
        state = GameState(ranger=ranger, entities=[thicket])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, 'sun'))

        # Monkeypatch prompt_commit to auto-pick 1,2
        def fake_prompt(_r, _a):
            return [1, 2]

        # Perform action using the engine API directly
        from src.models import Action
        act = Action(
            id="t1",
            name="thicket",
            aspect="AWA",
            approach="Exploration",
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
        eng.perform_action(act, decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision([0, 1]), target_id=None)

        self.assertEqual(state.ranger.energy["AWA"], 2)
        self.assertEqual(thicket.progress, 3)
        self.assertEqual(len(state.ranger.hand), 0)
    
    def test_single_energy(self):
        # Setup state: one feature (thicket), ranger with no cards in hand
        thicket = Entity(id="woods-011-overgrown-thicket", title="Overgrown Thicket", entity_type="Feature", presence=1, progress_threshold=2)
        ranger = RangerState(name="Ranger", hand=[], energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
        # Create two pseudo cards with Exploration+1 each
        state = GameState(ranger=ranger, entities=[thicket])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, 'sun'))

        # Perform action using the engine API directly
        from src.models import Action
        act = Action(
            id="t1",
            name="thicket",
            aspect="AWA",
            approach="Exploration",
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: thicket.add_progress(eff),
        )
        eng.perform_action(act, decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id=None)

        self.assertEqual(state.ranger.energy["AWA"], 2)
        self.assertEqual(thicket.progress, 1)
        self.assertEqual(len(state.ranger.hand), 0)

    def test_traverse_feature(self):
        feat = Entity(id="feat1", title="Feature A", entity_type="Feature", presence=1, progress_threshold=3)
        ranger = RangerState(name="Ranger", hand=[], energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
        from src.models import Card, ApproachIcons
        ranger.hand = [Card(id="e1", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1}))]
        state = GameState(ranger=ranger, entities=[feat])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, 'crest'))

        from src.models import Action
        act = Action(
            id="t2",
            name="traverse",
            aspect="FIT",
            approach="Exploration",
            difficulty_fn=lambda _s, _t: max(1, feat.presence),
            on_success=lambda s, eff, _t: feat.add_progress(eff),
            on_fail=lambda s, _t: setattr(state.ranger, "injury", state.ranger.injury + 1),
        )
        eng.perform_action(act, decision=__import__('src.models', fromlist=['CommitDecision']).CommitDecision([0]), target_id=None)

        self.assertEqual(state.ranger.energy["FIT"], 1)
        self.assertEqual(feat.progress, 2)
        self.assertEqual(state.ranger.injury, 0)


if __name__ == '__main__':
    unittest.main()
