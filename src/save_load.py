"""
Save/Load System for Earthborne Rangers

This module provides serialization and deserialization of game state.
The core insight is that game state is data + behavior, but only data needs
to be saved. Behavior (listeners, abilities, lambdas) is reconstructed from
the cards present in the loaded state.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Any, TYPE_CHECKING
from pathlib import Path

from .models import (
    Card, RangerState, GameState, CampaignTracker, ChallengeDeck, ChallengeCard,
    Aspect, Area, ChallengeIcon, CardType, Mission, FacedownCard, ValueModifier
)

if TYPE_CHECKING:
    from .engine import GameEngine

# Version for save file migration
SAVE_VERSION = "1.0"


# ============================================================================
# Serialization Data Structures
# ============================================================================

@dataclass
class ModifierData:
    """Serializable representation of a ValueModifier"""
    target: str
    amount: int
    source_id: str
    minimum_result: int


@dataclass
class CardData:
    """Serializable representation of a Card's mutable state"""
    card_class: str  # e.g., "BiscuitBasket", "SitkaDoe", "Card"
    id: str  # Unique instance ID

    # Mutable state
    exhausted: bool = False
    progress: int = 0
    harm: int = 0
    unique_tokens: dict[str, int] = field(default_factory=dict)
    modifiers: list[ModifierData] = field(default_factory=list)
    attached_to_id: str | None = None
    attached_card_ids: list[str] = field(default_factory=list)

    # For double-sided cards
    backside_class: str | None = None

    # For facedown cards
    is_facedown: bool = False
    frontside_id: str | None = None  # If facedown, the ID of the face-up side

    # For generic Card instances loaded from JSON
    json_source_title: str | None = None
    json_source_set: str | None = None


@dataclass
class ChallengeCardData:
    """Serializable representation of a ChallengeCard"""
    icon: str  # ChallengeIcon value
    mods: dict[str, int]  # Aspect -> modifier
    reshuffle: bool


@dataclass
class MissionData:
    """Serializable representation of a Mission"""
    name: str
    left_bubble: bool = False
    middle_bubble: bool = False
    right_bubble: bool = False


@dataclass
class RangerData:
    """Serializable representation of RangerState"""
    name: str
    aspects: dict[str, int]  # Aspect.value -> int
    energy: dict[str, int]
    injury: int
    ranger_token_location: str
    deck: list[CardData] = field(default_factory=list)
    hand: list[CardData] = field(default_factory=list)
    discard: list[CardData] = field(default_factory=list)
    fatigue_stack: list[CardData] = field(default_factory=list)


@dataclass
class CampaignTrackerData:
    """Serializable representation of CampaignTracker"""
    day_number: int
    notable_events: list[str] = field(default_factory=list)
    unlocked_rewards: list[str] = field(default_factory=list)
    active_missions: list[MissionData] = field(default_factory=list)
    cleared_missions: list[MissionData] = field(default_factory=list)
    ranger_deck_card_ids: list[str] = field(default_factory=list)
    ranger_name: str = ""
    ranger_aspects: dict[str, int] = field(default_factory=dict)
    current_location_id: str = "Lone Tree Station"
    current_terrain_type: str = "Woods"


@dataclass
class ChallengeDeckData:
    """Serializable representation of ChallengeDeck"""
    deck: list[ChallengeCardData] = field(default_factory=list)
    discard: list[ChallengeCardData] = field(default_factory=list)


@dataclass
class SaveData:
    """Complete serializable game state"""
    version: str
    round_number: int

    ranger: RangerData
    campaign_tracker: CampaignTrackerData

    role_card_id: str
    location_id: str
    weather_id: str | None
    mission_ids: list[str]

    areas: dict[str, list[CardData]]  # Area.value -> cards

    path_deck: list[CardData] = field(default_factory=list)
    path_discard: list[CardData] = field(default_factory=list)

    challenge_deck: ChallengeDeckData = field(default_factory=ChallengeDeckData)


# ============================================================================
# Card Class Registry
# ============================================================================

def _build_card_class_registry() -> dict[str, type[Card]]:
    """
    Build mapping from class name strings to actual classes.

    Automatically discovers all Card subclasses from the cards module,
    so new cards are automatically available for save/load without
    manual registration.
    """
    import inspect
    from . import cards as cards_module

    registry: dict[str, type[Card]] = {
        "Card": Card,
        "FacedownCard": FacedownCard,
    }

    # Auto-discover all classes exported from cards module that are Card subclasses
    for name in dir(cards_module):
        obj = getattr(cards_module, name)
        if (inspect.isclass(obj)
            and issubclass(obj, Card)
            and obj is not Card
            and obj is not FacedownCard):
            registry[name] = obj

    return registry


CARD_CLASSES: dict[str, type[Card]] | None = None


def get_card_class(class_name: str) -> type[Card]:
    """Look up a card class by name"""
    global CARD_CLASSES
    if CARD_CLASSES is None:
        CARD_CLASSES = _build_card_class_registry()

    if class_name not in CARD_CLASSES:
        raise ValueError(f"Unknown card class: {class_name}")
    return CARD_CLASSES[class_name]


# ============================================================================
# Serialization Functions
# ============================================================================

def serialize_modifier(mod: ValueModifier) -> ModifierData:
    """Convert a ValueModifier to serializable form"""
    return ModifierData(
        target=mod.target,
        amount=mod.amount,
        source_id=mod.source_id,
        minimum_result=mod.minimum_result
    )


def serialize_card(card: Card) -> CardData:
    """Convert a Card to serializable form"""
    # Determine the card class name
    class_name = card.__class__.__name__

    # Check if it's a facedown card
    is_facedown = isinstance(card, FacedownCard)
    frontside_id = None
    if is_facedown and card.backside:
        frontside_id = card.backside.id

    # Check for double-sided cards (has a non-FacedownCard backside)
    backside_class = None
    if card.backside and not isinstance(card.backside, FacedownCard):
        backside_class = card.backside.__class__.__name__

    # For generic Card instances, save JSON source info
    json_source_title = None
    json_source_set = None
    if class_name == "Card" and card.title:
        json_source_title = card.title
        json_source_set = card.card_set if card.card_set else None

    return CardData(
        card_class=class_name,
        id=card.id,
        exhausted=card.exhausted,
        progress=card.progress,
        harm=card.harm,
        unique_tokens=dict(card.unique_tokens),
        modifiers=[serialize_modifier(m) for m in card.modifiers],
        attached_to_id=card.attached_to_id,
        attached_card_ids=list(card.attached_card_ids),
        backside_class=backside_class,
        is_facedown=is_facedown,
        frontside_id=frontside_id,
        json_source_title=json_source_title,
        json_source_set=json_source_set
    )


def serialize_challenge_card(card: ChallengeCard) -> ChallengeCardData:
    """Convert a ChallengeCard to serializable form"""
    return ChallengeCardData(
        icon=card.icon.value,
        mods={aspect.value: mod for aspect, mod in card.mods.items()},
        reshuffle=card.reshuffle
    )


def serialize_mission(mission: Mission) -> MissionData:
    """Convert a Mission to serializable form"""
    return MissionData(
        name=mission.name,
        left_bubble=mission.left_bubble,
        middle_bubble=mission.middle_bubble,
        right_bubble=mission.right_bubble
    )


def serialize_game_state(engine: GameEngine) -> SaveData:
    """Convert full game state to serializable form"""
    state = engine.state

    # Serialize ranger state
    ranger_data = RangerData(
        name=state.ranger.name,
        aspects={aspect.value: val for aspect, val in state.ranger.aspects.items()},
        energy={aspect.value: val for aspect, val in state.ranger.energy.items()},
        injury=state.ranger.injury,
        ranger_token_location=state.ranger.ranger_token_location,
        deck=[serialize_card(c) for c in state.ranger.deck],
        hand=[serialize_card(c) for c in state.ranger.hand],
        discard=[serialize_card(c) for c in state.ranger.discard],
        fatigue_stack=[serialize_card(c) for c in state.ranger.fatigue_stack]
    )

    # Serialize campaign tracker
    campaign_data = CampaignTrackerData(
        day_number=state.campaign_tracker.day_number,
        notable_events=list(state.campaign_tracker.notable_events),
        unlocked_rewards=list(state.campaign_tracker.unlocked_rewards),
        active_missions=[serialize_mission(m) for m in state.campaign_tracker.active_missions],
        cleared_missions=[serialize_mission(m) for m in state.campaign_tracker.cleared_missions],
        ranger_deck_card_ids=list(state.campaign_tracker.ranger_deck_card_ids),
        ranger_name=state.campaign_tracker.ranger_name,
        ranger_aspects={aspect.value: val for aspect, val in state.campaign_tracker.ranger_aspects.items()},
        current_location_id=state.campaign_tracker.current_location_id,
        current_terrain_type=state.campaign_tracker.current_terrain_type
    )

    # Serialize challenge deck
    challenge_data = ChallengeDeckData(
        deck=[serialize_challenge_card(c) for c in state.challenge_deck.deck],
        discard=[serialize_challenge_card(c) for c in state.challenge_deck.discard]
    )

    # Serialize areas
    areas_data: dict[str, list[CardData]] = {}
    for area, cards in state.areas.items():
        areas_data[area.value] = [serialize_card(c) for c in cards]

    return SaveData(
        version=SAVE_VERSION,
        round_number=state.round_number,
        ranger=ranger_data,
        campaign_tracker=campaign_data,
        role_card_id=state.role_card.id,
        location_id=state.location.id,
        weather_id=state.weather.id if state.weather else None,
        mission_ids=[m.id for m in state.missions],
        areas=areas_data,
        path_deck=[serialize_card(c) for c in state.path_deck],
        path_discard=[serialize_card(c) for c in state.path_discard],
        challenge_deck=challenge_data
    )


def save_game(engine: GameEngine, filepath: str | Path) -> None:
    """Save the current game state to a JSON file"""
    save_data = serialize_game_state(engine)

    # Convert to dict for JSON serialization
    save_dict = _dataclass_to_dict(save_data)

    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_dict, f, indent=2)


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to dicts"""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    else:
        return obj


# ============================================================================
# Deserialization Functions
# ============================================================================

def deserialize_modifier(data: dict[str, Any]) -> ValueModifier:
    """Convert serialized modifier back to ValueModifier"""
    return ValueModifier(
        target=data['target'],
        amount=data['amount'],
        source_id=data['source_id'],
        minimum_result=data['minimum_result']
    )


def deserialize_challenge_card(data: dict[str, Any]) -> ChallengeCard:
    """Convert serialized challenge card back to ChallengeCard"""
    return ChallengeCard(
        icon=ChallengeIcon(data['icon']),
        mods={Aspect(k): v for k, v in data['mods'].items()},
        reshuffle=data['reshuffle']
    )


def deserialize_mission(data: dict[str, Any]) -> Mission:
    """Convert serialized mission back to Mission"""
    return Mission(
        name=data['name'],
        left_bubble=data.get('left_bubble', False),
        middle_bubble=data.get('middle_bubble', False),
        right_bubble=data.get('right_bubble', False)
    )


def instantiate_card(card_data: dict[str, Any]) -> Card:
    """
    Instantiate a Card from serialized data.

    For custom card classes: creates instance and applies mutable state.
    For generic Cards: loads from JSON source.
    For double-sided cards: creates both sides with fresh=False and links them.
    """
    class_name = card_data['card_class']

    # Handle facedown cards specially
    if card_data.get('is_facedown', False):
        # We'll resolve facedown cards after all cards are instantiated
        # For now, create a placeholder
        raise ValueError("Facedown cards should be handled in the card registry phase")

    # Check if it's a double-sided card
    backside_class_name = card_data.get('backside_class')

    if backside_class_name:
        # Double-sided card: instantiate both sides with fresh=False
        front_class = get_card_class(class_name)
        back_class = get_card_class(backside_class_name)

        # Create both sides without auto-linking
        front = front_class(fresh=False)
        back = back_class(fresh=False)

        # Override IDs
        front.id = card_data['id']
        back.id = f"{card_data['id']}-backside"

        # Link backsides
        front.backside = back
        back.backside = front

        # Apply mutable state to front (physical card state)
        _apply_mutable_state(front, card_data)

        return front

    # Handle generic Card loaded from JSON
    if class_name == "Card":
        json_title = card_data.get('json_source_title')
        json_set = card_data.get('json_source_set')

        if json_title and json_set:
            from .json_loader import load_card_fields
            card = Card(**load_card_fields(json_title, json_set))
        else:
            card = Card()

        card.id = card_data['id']
        _apply_mutable_state(card, card_data)
        return card

    # Standard card class
    card_class = get_card_class(class_name)

    # Check if class supports fresh parameter
    import inspect
    sig = inspect.signature(card_class.__init__)
    if 'fresh' in sig.parameters:
        card = card_class(fresh=False)
    else:
        card = card_class()

    # CRITICAL: Override the generated ID with saved ID
    card.id = card_data['id']

    # Apply mutable state
    _apply_mutable_state(card, card_data)

    return card


def _apply_mutable_state(card: Card, card_data: dict[str, Any]) -> None:
    """Apply mutable state fields to a card instance"""
    card.exhausted = card_data.get('exhausted', False)
    card.progress = card_data.get('progress', 0)
    card.harm = card_data.get('harm', 0)
    card.unique_tokens = dict(card_data.get('unique_tokens', {}))
    card.modifiers = [deserialize_modifier(m) for m in card_data.get('modifiers', [])]
    # attachment references are resolved later
    card.attached_to_id = card_data.get('attached_to_id')
    card.attached_card_ids = list(card_data.get('attached_card_ids', []))


def _validate_save_structure(save_dict: dict[str, Any]) -> None:
    """
    Validate that a save file contains all required keys.
    Raises ValueError with a descriptive message if validation fails.
    """
    required_top_level = ['version', 'round_number', 'ranger', 'campaign_tracker',
                          'role_card_id', 'location_id', 'areas', 'path_deck',
                          'path_discard', 'challenge_deck']

    missing_top = [key for key in required_top_level if key not in save_dict]
    if missing_top:
        raise ValueError(f"Save file missing required keys: {', '.join(missing_top)}")

    # Validate ranger structure
    if 'ranger' in save_dict:
        ranger_required = ['name', 'aspects', 'energy', 'ranger_token_location',
                          'deck', 'hand', 'discard', 'fatigue_stack']
        missing_ranger = [key for key in ranger_required if key not in save_dict['ranger']]
        if missing_ranger:
            raise ValueError(f"Save file 'ranger' missing required keys: {', '.join(missing_ranger)}")

    # Validate campaign_tracker structure
    if 'campaign_tracker' in save_dict:
        ct_required = ['day_number']
        missing_ct = [key for key in ct_required if key not in save_dict['campaign_tracker']]
        if missing_ct:
            raise ValueError(f"Save file 'campaign_tracker' missing required keys: {', '.join(missing_ct)}")

    # Validate challenge_deck structure
    if 'challenge_deck' in save_dict:
        cd_required = ['deck', 'discard']
        missing_cd = [key for key in cd_required if key not in save_dict['challenge_deck']]
        if missing_cd:
            raise ValueError(f"Save file 'challenge_deck' missing required keys: {', '.join(missing_cd)}")


def load_game(filepath: str | Path) -> GameEngine:
    """
    Load a game state from a JSON file and return a fully reconstructed GameEngine.
    """
    from .engine import GameEngine

    filepath = Path(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        save_dict = json.load(f)

    # Validate save file structure
    _validate_save_structure(save_dict)

    # Version check (for future migrations)
    version = save_dict.get('version', '1.0')
    if version != SAVE_VERSION:
        # Future: run migration functions here
        pass

    # Step 1 & 2: Instantiate all cards and build registry
    card_registry: dict[str, Card] = {}

    # Helper to process card list
    def process_card_list(cards_data: list[dict[str, Any]]) -> list[Card]:
        result = []
        for card_data in cards_data:
            # Skip facedown cards for now - they reference their frontside
            if card_data.get('is_facedown', False):
                continue

            card = instantiate_card(card_data)
            card_registry[card.id] = card

            # Also register backside if double-sided
            if card.backside and not isinstance(card.backside, FacedownCard):
                card_registry[card.backside.id] = card.backside

            result.append(card)
        return result

    # Process all card locations
    ranger_data = save_dict['ranger']
    ranger_deck = process_card_list(ranger_data['deck'])
    ranger_hand = process_card_list(ranger_data['hand'])
    ranger_discard = process_card_list(ranger_data['discard'])
    ranger_fatigue = process_card_list(ranger_data['fatigue_stack'])

    path_deck = process_card_list(save_dict['path_deck'])
    path_discard = process_card_list(save_dict['path_discard'])

    areas: dict[Area, list[Card]] = {}
    for area_name, cards_data in save_dict['areas'].items():
        area = Area(area_name)
        areas[area] = process_card_list(cards_data)

    # Now handle facedown cards - they reference already-instantiated frontsides
    def process_facedown_cards(cards_data: list[dict[str, Any]], card_list: list[Card]) -> None:
        for card_data in cards_data:
            if card_data.get('is_facedown', False):
                frontside_id = card_data.get('frontside_id')
                if frontside_id and frontside_id in card_registry:
                    frontside = card_registry[frontside_id]
                    # The facedown card IS the frontside's backside
                    facedown = frontside.backside
                    if facedown:
                        facedown.id = card_data['id']
                        _apply_mutable_state(facedown, card_data)
                        card_registry[facedown.id] = facedown
                        card_list.append(facedown)

    # Process facedown cards in each location
    process_facedown_cards(ranger_data['deck'], ranger_deck)
    process_facedown_cards(ranger_data['hand'], ranger_hand)
    process_facedown_cards(ranger_data['discard'], ranger_discard)
    process_facedown_cards(ranger_data['fatigue_stack'], ranger_fatigue)
    process_facedown_cards(save_dict['path_deck'], path_deck)
    process_facedown_cards(save_dict['path_discard'], path_discard)
    for area_name, cards_data in save_dict['areas'].items():
        area = Area(area_name)
        process_facedown_cards(cards_data, areas[area])

    # Step 3: Resolve attachment references (already set, just verify)
    # Attachment IDs are already set during instantiation

    # Step 4: Build GameState
    # Find special cards by ID
    role_card_id = save_dict['role_card_id']
    location_id = save_dict['location_id']
    weather_id = save_dict.get('weather_id')
    mission_ids = save_dict.get('mission_ids', [])

    role_card = card_registry.get(role_card_id)
    location = card_registry.get(location_id)
    weather = card_registry.get(weather_id) if weather_id else None
    missions = [card_registry[mid] for mid in mission_ids if mid in card_registry]

    if role_card is None:
        raise ValueError(f"Role card not found: {role_card_id}")
    if location is None:
        raise ValueError(f"Location not found: {location_id}")

    # Deserialize campaign tracker
    ct_data = save_dict['campaign_tracker']
    campaign_tracker = CampaignTracker(
        day_number=ct_data['day_number'],
        notable_events=list(ct_data.get('notable_events', [])),
        unlocked_rewards=list(ct_data.get('unlocked_rewards', [])),
        active_missions=[deserialize_mission(m) for m in ct_data.get('active_missions', [])],
        cleared_missions=[deserialize_mission(m) for m in ct_data.get('cleared_missions', [])],
        ranger_deck_card_ids=list(ct_data.get('ranger_deck_card_ids', [])),
        ranger_name=ct_data.get('ranger_name', ''),
        ranger_aspects={Aspect(k): v for k, v in ct_data.get('ranger_aspects', {}).items()},
        current_location_id=ct_data.get('current_location_id', 'Lone Tree Station'),
        current_terrain_type=ct_data.get('current_terrain_type', 'Woods')
    )

    # Create RangerState
    ranger_aspects = {Aspect(k): v for k, v in ranger_data['aspects'].items()}
    ranger = RangerState(
        name=ranger_data['name'],
        aspects=ranger_aspects,
        deck=ranger_deck,
        hand=ranger_hand,
        discard=ranger_discard,
        fatigue_stack=ranger_fatigue,
        injury=ranger_data.get('injury', 0),
        ranger_token_location=ranger_data['ranger_token_location']
    )
    # Override energy (RangerState.__post_init__ sets it to aspects)
    ranger.energy = {Aspect(k): v for k, v in ranger_data['energy'].items()}

    # Deserialize challenge deck
    cd_data = save_dict['challenge_deck']
    challenge_deck = ChallengeDeck(deck=[])  # Empty deck, we'll set it manually
    challenge_deck.deck = [deserialize_challenge_card(c) for c in cd_data['deck']]
    challenge_deck.discard = [deserialize_challenge_card(c) for c in cd_data['discard']]

    # Create GameState
    # Note: We need to prevent __post_init__ from modifying areas/ranger_token
    state = GameState.__new__(GameState)
    state.ranger = ranger
    state.campaign_tracker = campaign_tracker
    state.role_card = role_card
    state.location = location
    state.weather = weather if weather else Card()  # Placeholder if no weather
    state.missions = missions
    state.challenge_deck = challenge_deck
    state.areas = areas
    state.path_deck = path_deck
    state.path_discard = path_discard
    state.round_number = save_dict['round_number']

    # Ensure role card is in player area (may already be there from areas processing)
    if role_card not in state.areas[Area.PLAYER_AREA]:
        state.areas[Area.PLAYER_AREA].append(role_card)

    # Step 5: Create Engine and Reconstruct
    engine = GameEngine(state, skip_reconstruct=True)
    engine.reconstruct()  # Rebuilds listeners and constant abilities

    return engine
