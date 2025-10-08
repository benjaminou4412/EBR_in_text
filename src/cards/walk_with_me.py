"""
Walk With Me - Moment card implementation
"""

from ..models import MomentCard, GameState


class WalkWithMe(MomentCard):
    def __init__(self):
        # TODO: Load from JSON
        super().__init__(id="stub", title="Stub")

    def can_play(self, state: GameState) -> bool:
        """
        Walk With Me can be played after a successful Traverse test.
        TODO: Implement traverse success tracking
        """
        return False

    def play(self, state: GameState) -> None:
        """
        Effect: Ready an exhausted card.
        TODO: Implement card selection and readying
        """
        pass
