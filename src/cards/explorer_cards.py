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

    def enters_hand(self) -> EventListener | None:
        return EventListener(EventType.TEST_SUCCEED, self.play, self.id, TimingType.AFTER, "Traverse")

    def play(self, engine: GameEngine) -> None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test
        TODO: Implement Being selection and progress-adding
        """
        #move card to discard and do nothing for simple timing verification
        decision = engine.response_decider(engine.state, "You succeeded at a Traverse test. Will you play Walk With Me for 1 SPI?")
        if decision:
            if engine.state.ranger.spend_energy(engine.state, 1, Aspect.SPI):
                engine.state.ranger.discard.append(self)
                engine.state.ranger.hand.remove(self)
                engine.state.add_message(f"Played Walk With Me with no effects after traverse test success for testing purposes.")
