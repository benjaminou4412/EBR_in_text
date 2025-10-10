"""
Explorer card implementations
"""
from ..models import GameState, Card
from ..json_loader import load_card_fields #type:ignore


class WalkWithMe(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Walk With Me", "Explorer")) #type:ignore

    def can_play(self, state: GameState) -> bool:
        """
        Walk With Me can be played after a successful Traverse test.
        TODO: Implement traverse success tracking
        """
        return False

    def play(self, state: GameState) -> None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test
        TODO: Implement Being selection and progress-adding
        """
        pass
