import unittest
from main import GameState, RangerState, Entity, GameEngine


def fixed_draw(mod, sym):
    return lambda: (mod, sym)


class EngineTests(unittest.TestCase):
    def test_thicket_progress_and_energy(self):
        # Setup state: one feature (thicket), ranger with two exploration cards in hand
        thicket = Entity(id="woods-011-overgrown-thicket", title="Overgrown Thicket", entity_type="Feature", presence=1, progress_threshold=2)
        ranger = RangerState(name="Ranger", hand=[], energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
        # Create two pseudo cards with Exploration+1 each
        from main import Card, ApproachIcons
        ranger.hand = [
            Card(id="c1", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
            Card(id="c2", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
        ]
        state = GameState(ranger=ranger, entities=[thicket])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, 'sun'))

        # Monkeypatch prompt_commit to auto-pick 1,2
        def fake_prompt(_r, _a):
            return [1, 2]

        from main import prompt_commit as real_prompt
        from main import prompt_commit as mod_prompt
        import main as mainmod
        mainmod.prompt_commit = fake_prompt
        try:
            eng.perform_test(
                aspect="AWA",
                approach="Exploration",
                difficulty=1,
                on_success=lambda effort: thicket.add_progress(effort),
            )
        finally:
            mainmod.prompt_commit = real_prompt

        self.assertEqual(state.ranger.energy["AWA"], 2)
        self.assertEqual(thicket.progress, 2)
        self.assertEqual(len(state.ranger.hand), 0)

    def test_traverse_feature(self):
        feat = Entity(id="feat1", title="Feature A", entity_type="Feature", presence=1, progress_threshold=3)
        ranger = RangerState(name="Ranger", hand=[], energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
        from main import Card, ApproachIcons
        ranger.hand = [Card(id="e1", title="E+1", card_type="moment", approach=ApproachIcons({"Exploration": 1}))]
        state = GameState(ranger=ranger, entities=[feat])
        eng = GameEngine(state, challenge_drawer=fixed_draw(0, 'crest'))

        import main as mainmod
        real_prompt = mainmod.prompt_commit
        mainmod.prompt_commit = lambda _r, _a: [1]
        try:
            eng.perform_test(
                aspect="FIT",
                approach="Exploration",
                difficulty=max(1, feat.presence),
                on_success=lambda effort: feat.add_progress(effort),
                on_fail=lambda: setattr(state.ranger, "injury", state.ranger.injury + 1),
            )
        finally:
            mainmod.prompt_commit = real_prompt

        self.assertEqual(state.ranger.energy["FIT"], 1)
        self.assertEqual(feat.progress, 1)
        self.assertEqual(state.ranger.injury, 0)


if __name__ == '__main__':
    unittest.main()

