"""
Walk With Me - Moment card implementation
"""
from typing import cast
from ..models import MomentCard, GameState, Aspect
from ..json_loader import (
    load_card_json_by_title,
    parse_energy_cost,
    parse_approach_icons,
    parse_aspect_requirement,
    parse_traits,
    generate_card_id
)


class WalkWithMe(MomentCard):
    def __init__(self):
        # Load card data from JSON
        data = load_card_json_by_title("Walk With Me", "Explorer") #type: ignore

        # Parse fields
        card_set : str = str(data.get("set", ""))
        card_id : str = str(data.get("id", ""))
        energy_cost : dict[Aspect, int]= parse_energy_cost(data)
        approach_icons = parse_approach_icons(data)
        aspect = parse_aspect_requirement(data)
        traits = parse_traits(data)
        flavor_text: str = str(data.get("flavor_text", ""))

        # Extract rules text for abilities_text
        abilities : list[str]= []
        for rule in data.get("rules", []):
            text = rule.get("text", "")
            if text:
                abilities.append(text)

        # Initialize parent with all parsed data
        super().__init__(
            id=card_id,
            title="Walk With Me",
            card_set=card_set, 
            traits=traits,
            abilities_text=abilities,
            energy_cost=energy_cost,
            approach_icons=approach_icons,
            aspect=aspect[0],
            requirement=aspect[1],
            flavor_text=flavor_text
        )

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
