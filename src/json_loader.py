"""
Utility functions for loading card data from JSON files
"""

import json
from pathlib import Path
from typing import Optional
from .models import Aspect
from .models import Approach

# Map card set to their JSON files
CARD_JSON_FILES = {
    "explorer": "reference JSON/Ranger Cards/explorer_cards.json",
    "conciliator": "reference JSON/Ranger Cards/conciliator_cards.json",
    "valley": "reference JSON/Path Sets/valley.json",
    "woods": "reference JSON/Path Sets/Terrain sets/woods.json"
    # Add more as needed
}


def get_project_root() -> Path:
    """Get the project root directory"""
    # Assumes this file is in src/, so parent is project root
    return Path(__file__).parent.parent


def load_card_json_by_title(title: str, card_set: str) -> dict:
    """
    Load a card's JSON data by its title and type.

    Args:
        title: The card's title (e.g., "Walk With Me")
        set: The card's origin set (e.g., "Explorer", "Valley")

    Returns:
        Dictionary containing the card's JSON data

    Raises:
        ValueError: If card not found or file doesn't exist
    """
    json_file = CARD_JSON_FILES.get(card_set.lower())
    if not json_file:
        raise ValueError(f"Unknown card set: {card_set}")

    json_path = get_project_root() / json_file
    if not json_path.exists():
        raise ValueError(f"JSON file not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # JSON is either a list or a dict with "cards" key
    if isinstance(data, list):
        cards = data
    else:
        cards = data.get("cards", [])

    # Search for the card by title
    for card in cards:
        if card.get("title") == title:
            return card

    raise ValueError(f"Card '{title}' not found in {json_file}")


def parse_energy_cost(card_data: dict) -> dict[Aspect, int]:
    """
    Parse energy cost from JSON format to internal dict format.

    JSON format: {"amount": 1, "aspect": "SPI"}
    Internal format: {Aspect.SPI: 1}
    """
    

    energy_cost_data = card_data.get("energy_cost")
    if not energy_cost_data:
        return {}

    aspect_str = energy_cost_data.get("aspect", "")
    amount = energy_cost_data.get("amount", 0)

    if aspect_str and amount:
        try:
            aspect = Aspect(aspect_str)
            return {aspect: amount}
        except ValueError:
            return {}

    return {}


def parse_approach_icons(card_data: dict) -> dict[Approach, int]:
    """
    Parse approach icons from JSON format to internal dict format.

    JSON format: [{"approach": "Connection", "count": 1}]
    Internal format: {Approach.CONNECTION: 1}
    """
    

    approach_icons = {}
    approach_data = card_data.get("approach_icons", [])

    for icon in approach_data:
        approach_str = icon.get("approach")
        count = icon.get("count", 0)

        if approach_str and count:
            try:
                approach = Approach(approach_str)
                approach_icons[approach] = approach_icons.get(approach, 0) + count
            except ValueError:
                pass

    return approach_icons


def parse_aspect_requirement(card_data: dict) -> tuple[Aspect | None, int]:
    """
    Parse aspect requirement from JSON.
    Returns: (aspect, min_value)
    """

    aspect_req = card_data.get("aspect_requirement")
    if not aspect_req:
        return (None, 0)

    aspect_str = aspect_req.get("aspect")
    min_value = aspect_req.get("min", 0)

    aspect = None
    if aspect_str:
        try:
            aspect = Aspect(aspect_str)
        except ValueError:
            pass

    return (aspect, min_value)


def parse_traits(card_data: dict) -> list[str]:
    """Parse traits list from JSON"""
    return card_data.get("traits", [])


def generate_card_id(title: str, card_set: str) -> str:
    """
    Generate a card ID from title and set.
    Format: set-title (lowercase, hyphens for spaces)
    """
    set_part = card_set.lower().replace(" ", "-")
    title_part = title.lower().replace(" ", "-")
    return f"{set_part}-{title_part}"


def load_ranger_card_fields(title: str, card_set: str) -> dict:
    """
    Load common RangerCard fields from JSON.

    Returns a dict with all common fields that can be unpacked into super().__init__()
    for any RangerCard subclass.

    Args:
        title: The card's title
        card_set: The card's set name

    Returns:
        Dictionary with common RangerCard fields ready to unpack
    """
    data = load_card_json_by_title(title, card_set)  # type: ignore

    # Parse all common fields (no id - will be auto-generated)
    parsed_card_set = str(data.get("set", ""))
    energy_cost = parse_energy_cost(data)
    approach_icons = parse_approach_icons(data)
    aspect_tuple = parse_aspect_requirement(data)
    traits = parse_traits(data)
    flavor_text = str(data.get("flavor_text", ""))

    # Extract rules text for abilities_text
    abilities: list[str] = []
    for rule in data.get("rules", []):
        text = rule.get("text", "")
        if text:
            abilities.append(text)

    return {
        "title": title,
        "card_set": parsed_card_set,
        "traits": traits,
        "abilities_text": abilities,
        "energy_cost": energy_cost,
        "approach_icons": approach_icons,
        "aspect": aspect_tuple[0],
        "requirement": aspect_tuple[1],
        "flavor_text": flavor_text
    }


def parse_threshold_value(value) -> tuple[int | None, bool]:
    """
    Parse threshold from JSON (handles int, string like "2R", or None).
    Returns: (threshold_value, is_nulled)

    Examples:
        3 -> (3, False)
        "2R" -> (2, False)
        None -> (None, False)
        -1 -> (None, False) for missing
        -2 -> (None, True) for nulled
    """
    if value is None or value == -1:
        return (None, False)  # Missing threshold
    if value == -2:
        return (None, True)  # Nulled threshold
    if isinstance(value, int):
        return (value, False)
    # Parse string like "2R" - extract just the number
    s = ''.join(ch for ch in str(value) if ch.isdigit())
    return (int(s) if s else None, False)


def parse_zone(enters_play: str | None) -> 'Zone':
    """Parse enters_play field to Zone enum"""
    from .models import Zone

    if enters_play == "within_reach":
        return Zone.WITHIN_REACH
    elif enters_play == "along_the_way":
        return Zone.ALONG_THE_WAY
    else:
        return Zone.WITHIN_REACH  # Default


def parse_challenge_effects(card_data: dict) -> dict:
    """
    Parse challenge effects from rules that have challenge_symbol.
    Returns dict mapping Symbol -> effect text
    """
    from .models import Symbol

    challenge_effects = {}
    for rule in card_data.get("rules", []):
        if rule.get("kind") == "challenge":
            symbol_str = rule.get("challenge_symbol")
            text = rule.get("text", "")
            if symbol_str and text:
                try:
                    symbol = Symbol(symbol_str)
                    challenge_effects[symbol] = text
                except ValueError:
                    pass
    return challenge_effects


def load_path_card_fields(title: str, card_set: str) -> dict:
    """
    Load common PathCard fields from JSON.

    Returns a dict with all common fields that can be unpacked into super().__init__()
    for any PathCard subclass (BeingCard, FeatureCard, etc.).

    Args:
        title: The card's title
        card_set: The card's set name

    Returns:
        Dictionary with common PathCard fields ready to unpack
    """
    data = load_card_json_by_title(title, card_set)  # type: ignore

    # Parse all common fields (no id - will be auto-generated)
    parsed_card_set = str(data.get("card_set", card_set))  # Use card_set param as fallback
    traits = parse_traits(data)
    presence = int(data.get("presence", 1))

    # Parse thresholds
    harm_value, harm_nulled = parse_threshold_value(data.get("harm_threshold"))
    progress_value, progress_nulled = parse_threshold_value(data.get("progress_threshold"))

    # Parse zone
    area = parse_zone(data.get("enters_play"))

    # Parse challenge effects
    challenge_effects = parse_challenge_effects(data)

    # Extract all rules text for abilities_text
    abilities: list[str] = []
    for rule in data.get("rules", []):
        text = rule.get("text", "")
        if text:
            abilities.append(text)

    return {
        "title": title,
        "card_set": parsed_card_set,
        "traits": traits,
        "abilities_text": abilities,
        "area": area,
        "harm_threshold": harm_value,
        "progress_threshold": progress_value,
        "harm_nulled": harm_nulled,
        "progress_nulled": progress_nulled,
        "presence": presence,
        "challenge_effects_text": challenge_effects
    }
