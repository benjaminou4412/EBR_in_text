"""
Conciliator card implementations
"""
from ..models import GameState, Card
from ..json_loader import load_card_fields #type:ignore


class ADearFriend(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("A Dear Friend", "Conciliator")) #type:ignore
        self.art_description = "Two figures stand facing the horizon, with an arm each on each other's backs. " \
        "The figure on the right is fully colored and detailed, with slick black hair tied in a bushy ponytail, goggles, " \
        "a red-orange billowing cloak, and their gloved hand pointing out into the distance. The figure on the left, " \
        "along with the background landscape, are greyscale sketches. The figure on the left has goggles, a bladed staff, " \
        "and a shoulder bag, each also a greyscale sketch."

    def can_play(self, state: GameState) -> bool:
        """
        A Dear Friend can be played from hand like other attachments.
        TODO: Check if there are valid human targets in path deck/discard
        """
        return False

