"""
Conciliator card implementations
"""
from ..models import AttachmentCard, GameState
from ..json_loader import load_ranger_card_fields #type:ignore


class ADearFriend(AttachmentCard):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_ranger_card_fields("A Dear Friend", "Conciliator")) #type:ignore

    def can_play(self, state: GameState) -> bool:
        """
        A Dear Friend can be played from hand like other attachments.
        TODO: Check if there are valid human targets in path deck/discard
        """
        return False

    def play(self, state: GameState) -> None:
        """
        Effect: Search path deck and discard for a human, put into play with this attached.
        TODO: Implement deck search and attachment logic
        """
        pass
