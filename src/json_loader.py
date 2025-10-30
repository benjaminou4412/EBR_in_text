"""
Utility functions for loading card data from JSON files
"""

import json
from pathlib import Path
from .models import Aspect, Approach, Area, CardType

#Gonna be a lot of type-ignore in this file because JSON's wonky

# Map card set to their JSON files
CARD_JSON_FILES = {
    "explorer": "reference JSON/Ranger Cards/explorer_cards.json",
    "conciliator": "reference JSON/Ranger Cards/conciliator_cards.json",
    "valley": "reference JSON/Path Sets/valley.json",
    "woods": "reference JSON/Path Sets/Terrain sets/woods.json",
    "locations": "reference JSON/locations.json"
    # Add more as needed
}


def get_project_root() -> Path:
    """Get the project root directory"""
    # Assumes this file is in src/, so parent is project root
    return Path(__file__).parent.parent

def load_card_fields(title: str, card_set: str) -> dict: # type: ignore
    """
    Load common Card fields from JSON.

    Returns a dict with all common fields that can be unpacked with ** into super().__init__()
    for any Card subclass.

    Args:
        title: The card's title
        card_set: The card's set name

    Returns:
        Dictionary with common Card fields ready to unpack
    """
    data = load_card_json_by_title(title, card_set)  # type: ignore

    #title, id, and card_set all taken care of by parameters or post_init

    flavor_text = str(data.get("flavor_text", "")) #type:ignore
    card_types : set[CardType]= parse_card_types(card_set, str(data.get("card_type", ""))) #type:ignore
    traits = set(parse_traits(data))
    abilities = parse_card_abilities(data)
    starting_tokens = parse_starting_tokens(data)
    starting_area = parse_area(data.get("enters_play"), card_types) #type:ignore
    aspect_tuple = parse_aspect_requirement(data)
    energy_cost = parse_energy_cost(data)
    approach_icons = parse_approach_icons(data)
    equip_value = data.get("equip_value") #type: ignore
    harm_value, harm_forbidden, harm_clears_by_ranger_token = parse_threshold_value(data.get("harm_threshold")) #type: ignore
    progress_value, progress_forbidden, progress_clears_by_ranger_token = parse_threshold_value(data.get("progress_threshold")) #type: ignore
    presence = data.get("presence") #type: ignore

    on_enter_log = data.get("campaign_log_entry") #type: ignore
    logs = parse_clear_logs(data)
    on_progress_clear_log = logs[0]
    on_harm_clear_log = logs[1]

    description = data.get("description") #type: ignore
    locations = data.get("mission_locations") #type: ignore
    objective = data.get("mission_objective") #type: ignore
    mission_clear_log = parse_mission_objective_log(data) #type: ignore


    return { #type: ignore
        "title": title,
        "card_set": card_set,
        "flavor_text": flavor_text,
        "card_types": card_types,
        "traits": traits,
        "abilities_text": abilities,
        "starting_tokens": starting_tokens,
        "starting_area": starting_area,
        "aspect": aspect_tuple[0],
        "requirement": aspect_tuple[1],
        "energy_cost": energy_cost,
        "approach_icons": approach_icons,
        "equip_value": equip_value,
        "harm_threshold": harm_value,
        "progress_threshold": progress_value,
        "harm_forbidden": harm_forbidden,
        "progress_forbidden": progress_forbidden,
        "harm_clears_by_ranger_tokens": harm_clears_by_ranger_token,
        "progress_clears_by_ranger_tokens": progress_clears_by_ranger_token,
        "presence": presence,
        "on_enter_log": on_enter_log,
        "on_progress_clear_log": on_progress_clear_log,
        "on_harm_clear_log": on_harm_clear_log,
        "mission_description": description,
        "mission_locations": locations,
        "mission_objective": objective,
        "mission_clear_log": mission_clear_log
    }




def load_card_json_by_title(title: str, card_set: str) -> dict: #type: ignore
    """
    Load a card's JSON data by its title and set.

    Args:
        title: The card's title (e.g., "Walk With Me")
        set: The card's origin set (e.g., "Explorer", "Valley")

    Returns:
        Dictionary containing the card's JSON data. Type ignore because JSON dicts are complex

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
        cards = data #type:ignore
    else:
        cards = data.get("cards", [])

    # Search for the card by title
    for card in cards: #type:ignore
        if card.get("title") == title: #type:ignore
            return card #type:ignore

    raise ValueError(f"Card '{title}' not found in {json_file}")

def parse_starting_tokens(card_data : dict) -> tuple[str,int]: #type:ignore
    enters_play_with = card_data.get("enters_play_with", {}) #type:ignore
    if enters_play_with:
        token_type = enters_play_with.get("type", "") #type:ignore
        token_amount = enters_play_with.get("amount", 0) #type:ignore
        return (token_type, token_amount) #type:ignore
    return ("", 0)


def parse_card_abilities(card_data : dict) -> list[str]: #type:ignore
    abilities: list[str] = []
    for rule in card_data.get("rules", []): #type:ignore
            text = rule.get("text", "") #type:ignore
            if text:
                if rule.get("kind", "") == "challenge": #type:ignore
                    abilities.append(rule.get("challenge_symbol", "NO_SYMBOL_FOUND") + ": " + text) #type:ignore
                else:
                    abilities.append(text) #type:ignore
    return abilities


def parse_card_types(card_set : str, card_type: str) -> set[CardType]:
    ranger_sets = {"artificer", "artisan", "conciliator", "explorer", "forager", "personality", "shaper", "shepherd", "traveler"}
    path_sets = {"branch", "fractured wall", "lone tree station", "marsh of rebirth", "meadow", "northern outpost", "spire",
                 "tumbledown", "white sky", "grassland", "lakeshore", "mountain pass", "old growth", "ravine", "river", "swamp",
                 "woods", "general", "valley"}
    
    #first, set up the base card category: Ranger, Path, or neither
    card_types : set[CardType] = set()
    if card_set.lower() in ranger_sets:
        card_types.add(CardType.RANGER)
    elif card_set.lower() in path_sets:
        card_types.add(CardType.PATH)
    #stays empty if weather/mission/location set

    parsed_card_type : str = card_type.lower().replace(" ", "").replace("_", "").replace("-", "") #type:ignore
    if parsed_card_type == "gear":
        card_types.add(CardType.GEAR)
    elif parsed_card_type == "moment":
        card_types.add(CardType.MOMENT)
    elif parsed_card_type == "attachment":
        card_types.add(CardType.ATTACHMENT)
    elif parsed_card_type == "attribute":
        card_types.add(CardType.ATTRIBUTE)
    elif parsed_card_type == "being":
        card_types.add(CardType.BEING)
    elif parsed_card_type == "feature":
        card_types.add(CardType.FEATURE)
    elif parsed_card_type == "weather":
        card_types.add(CardType.WEATHER)
    elif parsed_card_type == "location":
        card_types.add(CardType.LOCATION)
    elif parsed_card_type == "mission":
        card_types.add(CardType.MISSION)
    elif parsed_card_type == "role":
        card_types.add(CardType.ROLE)
    
    return card_types

def parse_energy_cost(card_data: dict) -> int | None: #type:ignore
    """
    Parse energy cost from JSON format to internal dict format.

    JSON format: {"amount": 1, "aspect": "SPI"}
    Internal format: separate aspect field (Aspect) and energy_cost field (int)
    """
    

    energy_cost_data = card_data.get("energy_cost") #type:ignore
    if not energy_cost_data:
        return None

    amount = int(energy_cost_data.get("amount", 0)) #type:ignore

    if amount:
        try:
            return amount
        except ValueError:
            return None

    return None


def parse_approach_icons(card_data: dict) -> dict[Approach, int]: #type:ignore
    """
    Parse approach icons from JSON format to internal dict format.

    JSON format: [{"approach": "Connection", "count": 1}]
    Internal format: {Approach.CONNECTION: 1}
    """
    

    approach_icons : dict[Approach, int]= {}
    approach_data = card_data.get("approach_icons", []) #type:ignore

    for icon in approach_data: #type:ignore
        approach_str = icon.get("approach") #type:ignore
        count = icon.get("count", 0) #type:ignore

        if approach_str and count:
            try:
                approach = Approach(approach_str)
                approach_icons[approach] = approach_icons.get(approach, 0) + count #type:ignore
            except ValueError:
                pass

    return approach_icons 


def parse_aspect_requirement(card_data: dict) -> tuple[Aspect | None, int]: #type: ignore
    """
    Parse aspect requirement from JSON.
    Returns: (aspect, min_value)
    """

    aspect_req = card_data.get("aspect_requirement") #type: ignore
    if not aspect_req:
        return (None, 0)

    aspect_str = aspect_req.get("aspect") #type: ignore
    min_value = aspect_req.get("min", 0) #type: ignore

    aspect = None
    if aspect_str:
        try:
            aspect = Aspect(aspect_str)
        except ValueError:
            pass

    return (aspect, min_value) #type: ignore


def parse_traits(card_data: dict) -> list[str]:  #type: ignore
    """Parse traits list from JSON"""
    return card_data.get("traits", []) #type: ignore


def generate_card_id(title: str, card_set: str) -> str:
    """
    Generate a card ID from title and set.
    Format: set-title (lowercase, hyphens for spaces)
    """
    set_part = card_set.lower().replace(" ", "-")
    title_part = title.lower().replace(" ", "-")
    return f"{set_part}-{title_part}"




def parse_threshold_value(value) -> tuple[int | None, bool, bool]: #type:ignore
    """
    Parse threshold from JSON (handles int, string like "2R", or None).
    Returns: (threshold_value, is_nulled, clears_by_ranger_token)

    Examples:
        3 -> (3, False, False)
        "2R" -> (2, False, False)
        None -> (None, False, False)
        -1 -> (None, False, False) for missing
        -2 -> (None, True, False) for nulled
        "Ranger Token" -> (None, False, True) for ranger token thresholds.
    """
    if value is None or value == -1:
        return (None, False, False)  # Missing threshold
    if value == -2:
        return (None, True, False)  # Nulled threshold
    if isinstance(value, int):
        return (value, False, False)
    if isinstance(value, str) and value.casefold() == "Ranger Token".casefold():
        return (None, False, True)
    # Parse string like "2R" - extract just the number
    s = ''.join(ch for ch in str(value) if ch.isdigit()) #type:ignore
    return (int(s) if s else None, False, False)


def parse_area(enters_play: str | None, card_types: set[CardType]) -> Area | None:
    """Parse enters_play field to Area enum"""
    if enters_play is None:
        return None

    if CardType.WEATHER in card_types or CardType.LOCATION in card_types or CardType.MISSION in card_types:
        return Area.SURROUNDINGS
    elif CardType.GEAR in card_types:
        return Area.PLAYER_AREA
    elif CardType.MOMENT in card_types or CardType.ATTRIBUTE in card_types or CardType.ATTACHMENT in card_types:
        return None
    else:
        enters_play_cleaned = enters_play.lower().replace(" ", "").replace("_", "").replace("-", "") #type:ignore
        if enters_play_cleaned == "withinreach":
            return Area.WITHIN_REACH
        elif enters_play_cleaned == "alongtheway":
            return Area.ALONG_THE_WAY
        else:
            return None  # Default


def parse_clear_logs(card_data: dict) -> tuple[str | None, str | None]: #type:ignore
    """Returns (progress_clear_log, harm_clear_log)"""
    progress_log = None
    harm_log = None
    
    for rule in card_data.get("rules", []):#type:ignore
        text = rule.get("text", "")#type:ignore
        
        # Look for clear rules
        if "clear" not in text.lower() or "campaign log entry" not in text.lower():#type:ignore
            continue
        
        # Extract the number after "campaign log entry" (handles "89" or "110.15")
        import re
        match = re.search(r'campaign log entry\]\s*([\d.]+)', text, re.IGNORECASE)#type:ignore
        if not match:
            continue
        
        log_number = match.group(1)
        
        # Check if it's progress or harm
        if "[progress]" in text.lower():#type:ignore
            progress_log = log_number
        if "[harm]" in text.lower():#type:ignore
            harm_log = log_number
    
    return (progress_log, harm_log)


def parse_mission_objective_log(card_data: dict) -> str | None:#type:ignore
    """Extract campaign log entry from mission objective text"""
    # Check if there's a mission_objective field
    objective = card_data.get("mission_objective", "")#type:ignore
    if not objective:
        return None
    
    # Look for [Campaign Log Entry] followed by number (handles "89" or "110.15")
    import re
    match = re.search(r'campaign log entry\]\s*([\d.]+)', objective, re.IGNORECASE)#type:ignore
    if match:
        return match.group(1)
    
    return None



