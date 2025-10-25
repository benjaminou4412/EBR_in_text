"""
Explorer card implementations
"""
from ..models import Card, EventListener, EventType, TimingType, Aspect
from ..engine import GameEngine
from ..json_loader import load_card_fields #type:ignore


class WalkWithMe(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Walk With Me", "Explorer")) #type:ignore
        self.art_description = "A detailed sketch of a canine in a snowy, hilly clearing. The canine looks " \
        "back, and in the distance you see the small figures of the rest of its pack just exiting a copse " \
        "of snow-topped firs."

    def enters_hand(self, engine: GameEngine) -> EventListener | None:
        """Override to add listener. Call super() to show art description."""
        super().enters_hand(engine)
        return EventListener(EventType.TEST_SUCCEED, self.play, self.id, TimingType.AFTER, "Traverse")

    def play(self, engine: GameEngine, effort: int) -> None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test
        """
        targets_list = engine.state.beings_in_play()
        if not targets_list:
            engine.add_message("No Beings in play; Walk With Me cannot be played.")
            return
        decision = engine.response_decider(engine, "You succeeded at a Traverse test. Will you play Walk With Me for 1 SPI?")
        if decision:
            success, error = engine.state.ranger.spend_energy(1, Aspect.SPI)
            if success:
                engine.add_message(f"Please choose a Being to add {effort} [Progress] to.")
                target = engine.card_chooser(engine, targets_list)
                # Move Walk With Me to discard and clean up listener
                engine.discard_from_hand(self)
                msg = target.add_progress(effort)
                engine.add_message(f"Played Walk With Me: {msg}")
            elif error:
                engine.add_message(error)
