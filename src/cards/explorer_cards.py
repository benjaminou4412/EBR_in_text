"""
Explorer card implementations
"""
from ..models import GameState, Card, EventListener, EventType, TimingType
from ..json_loader import load_card_fields #type:ignore


class WalkWithMe(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Walk With Me", "Explorer")) #type:ignore

    def enters_hand(self) -> EventListener | None:
        return EventListener(EventType.TEST_SUCCEED, self.play, self.id, TimingType.AFTER, "Traverse")

    def play(self, state: GameState) -> None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test
        TODO: Implement Being selection and progress-adding
        """
        #move card to discard and do nothing for simple timing verification
        state.ranger.discard.append(self)
        state.ranger.hand.remove(self)
        state.add_message(f"Played Walk With Me automatically after traverse test success for testing purposes.")
