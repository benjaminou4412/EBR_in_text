from __future__ import annotations
from .models import Card


def build_woods_path_deck() -> list[Card]:
    # Import inside function to avoid circular import
    from .cards import (ProwlingWolhund, SitkaBuck, SitkaDoe, CausticMulcher,
                        SunberryBramble, OvergrownThicket)

    return [ProwlingWolhund(), ProwlingWolhund(), ProwlingWolhund(),
                     SitkaBuck(), SitkaBuck(), SitkaBuck(),
                     SitkaDoe(),
                     CausticMulcher(),
                     SunberryBramble(), SunberryBramble(),
                     OvergrownThicket(), OvergrownThicket()]

def select_three_random_valley_cards() -> list[Card]:
    # Import inside function to avoid circular import
    from .cards import CalypsaRangerMentor, QuisiVosRascal, TheFundamentalist

    #TODO: actually select three random valley cards
    return [CalypsaRangerMentor(), QuisiVosRascal(), TheFundamentalist()]

def get_new_location(current_location: Card) -> Card:
    # Import inside function to avoid circular import
    from .cards import BoulderField, AncestorsGrove

    return BoulderField() if current_location.title == "Ancestor's Grove" else AncestorsGrove()
