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

def get_location_by_id(location_id: str) -> Card:
    """Get a location card by its ID. Returns Ancestor's Grove as default if unknown."""
    # Import inside function to avoid circular import
    from .cards import BoulderField, AncestorsGrove

    location_registry = {
        "Boulder Field": BoulderField,
        "Ancestor's Grove": AncestorsGrove,
    }

    if location_id in location_registry:
        return location_registry[location_id]()
    else:
        # Default to Ancestor's Grove for unknown locations
        return AncestorsGrove()

def get_current_weather() -> Card:
    #TODO: Reference campaign log for today's weather
    from .cards import APerfectDay
    return APerfectDay()