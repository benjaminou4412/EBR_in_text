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

def get_pivotal_cards(location: Card) -> list[Card]:
    from .cards import HyPimpotChef
    if location.title == "Lone Tree Station":
        return [HyPimpotChef()] #TODO: Add other Lone Tree Station cards
    else:
        raise RuntimeError("Pivotal location not yet implemented; can't fetch Pivotal set!")

def get_available_travel_destinations(current_location: Card) -> list[Card]:
    """Return the available travel destinations from the current location.

    Currently implements a triangle of three locations:
    Lone Tree Station <-> Boulder Field <-> Ancestor's Grove <-> Lone Tree Station
    """
    # Import inside function to avoid circular import
    from .cards import BoulderField, AncestorsGrove, LoneTreeStation

    # All three locations form a connected triangle
    all_locations = {
        "Lone Tree Station": LoneTreeStation,
        "Boulder Field": BoulderField,
        "Ancestor's Grove": AncestorsGrove,
    }

    # Return all locations except the current one
    return [loc_class() for title, loc_class in all_locations.items()
            if title != current_location.title]

def get_location_by_id(location_id: str) -> Card:
    """Get a location card by its ID. Returns Lone Tree Station as default if unknown."""
    # Import inside function to avoid circular import
    from .cards import BoulderField, AncestorsGrove, LoneTreeStation

    location_registry = {
        "Boulder Field": BoulderField,
        "Ancestor's Grove": AncestorsGrove,
        "Lone Tree Station": LoneTreeStation
    }

    if location_id in location_registry:
        return location_registry[location_id]()
    else:
        # Default to Lone Tree Station for unknown locations (campaign start)
        return LoneTreeStation()

def get_current_weather(weather_title: str) -> Card:
    from .cards import APerfectDay, Downpour, HowlingWinds

    weather_registry = {
        "A Perfect Day": APerfectDay,
        "Downpour": Downpour,
        "Howling Winds": HowlingWinds,
    }
    if weather_title in weather_registry:
        return weather_registry[weather_title]()
    else:
        raise RuntimeError(f"Weather not found: {weather_title}")


from .models import Mission
def get_current_missions(active_missions: list[Mission]) -> list[Card]:
    from .cards import BiscuitDelivery

    mission_registry = {
        "Biscuit Delivery": BiscuitDelivery
    }

    result = []
    for mission in active_missions:
        if mission.name in mission_registry:
            result.append(mission_registry[mission.name]())
        else:
            raise RuntimeError("Mission not found!")
        
    return result