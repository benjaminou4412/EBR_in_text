from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, cast
from enum import Enum


# Enums for fixed game constants

class Aspect(str, Enum):
    """Energy types in Earthborne Rangers."""
    AWA = "AWA"
    FIT = "FIT"
    SPI = "SPI"
    FOC = "FOC"


class Symbol(str, Enum):
    """Challenge deck symbols."""
    SUN = "sun"
    MOUNTAIN = "mountain"
    CREST = "crest"


class Approach(str, Enum):
    """Approach types for tests."""
    CONFLICT = "Conflict"
    EXPLORATION = "Exploration"
    REASON = "Reason"
    CONNECTION = "Connection"

class Zone(str, Enum):
    SURROUNDINGS = "Surroundings"
    ALONG_THE_WAY = "Along the Way"
    WITHIN_REACH = "Within Reach"
    PLAYER_AREA = "Player Area"


# Core data structures: pure state and card data


@dataclass
class Card:
    title: str
    id: str
    traits: list[str] = field(default_factory=lambda: cast(list[str], []))

    card_set: str = ""
    abilities_text: list[str] = field(default_factory=lambda: cast(list[str], []))
    starting_tokens: dict[str, int] = field(default_factory=lambda: cast(dict[str, int], {}))
    
    def get_types(self, location: str | None = None) -> set[type]:
        """Override for context-dependent typing"""
        return {type(self)}

@dataclass
class RangerCard(Card):
    energy_cost: dict[Aspect, int] = field(default_factory=lambda: cast(dict[Aspect, int], {}))
    aspect: Aspect | None = None
    approach_icons: dict[Approach, int] = field(default_factory=lambda: cast(dict[Approach, int], {}))

@dataclass
class PathCard(Card):
    area: str = "" # "Within Reach" or "Along the Way"
    harm_threshold: int | None = None
    progress_threshold: int | None = None
    harm_nulled : bool = False
    progress_nulled : bool = False
    presence: int = 0
    challenge_effects_text: dict[Symbol, str] = field(default_factory=lambda: cast(dict[Symbol, str], {}))
    progress: int = 0
    harm: int = 0
    
    # Optional campaign log entries
    on_enter_log: str | None = None
    on_progress_clear_log: str | None = None
    on_harm_clear_log: str | None = None

    # state modification

    def add_progress(self, amount: int) -> None:
        if not self.progress_nulled:
            self.progress = max(0, self.progress + max(0, amount))

    def add_harm(self, amount: int) -> None:
        if not self.harm_nulled:
            self.harm = max(0, self.harm + max(0, amount))

    def clear_if_threshold(self) -> Optional[str]:
        if self.progress_threshold is not None and self.progress >= self.progress_threshold:
            return "progress"
        if self.harm_threshold is not None and self.harm >= self.harm_threshold:
            return "harm"
        return None
    

@dataclass
class GearCard(RangerCard):
    equip_slots: int = 0

@dataclass
class MomentCard(RangerCard):
    pass

@dataclass
class AttributeCard(RangerCard):
    pass
    # Note: cannot be played, only committed

@dataclass
class AttachmentCard(RangerCard):
    equip_slots: int | None = None
    # TODO: attachment target logic

@dataclass
class BeingCard(PathCard):
    pass  # Distinguished primarily by type checks

@dataclass
class FeatureCard(PathCard):
    pass  # Distinguished primarily by type checks

@dataclass
class RangerBeingCard(RangerCard):
    """Ranger Being - has ranger fields + path card fields"""
    # Path-like fields
    area: str = "Within Reach"  # or "Along the Way"
    harm_threshold: int | None = None
    progress_threshold: int | None = None
    presence: int = 0
    
    def get_types(self, location: str | None = None) -> set[type]:
        if location == "hand":
            return {RangerCard}
        else:  # in play
            return {RangerCard, BeingCard}

@dataclass
class RangerFeatureCard(RangerCard):
    """Ranger Feature - similar structure to Ranger Being"""
    area: str = "Within Reach"
    harm_threshold: int | None = None
    progress_threshold: int | None = None
    presence: int = 0
    
    def get_types(self, location: str | None = None) -> set[type]:
        if location == "hand":
            return {RangerCard}
        else:  # in play
            return {RangerCard, FeatureCard}

# Other cards - direct from Card
@dataclass
class WeatherCard(Card):
    # TODO: weather-specific fields
    pass

@dataclass
class LocationCard(Card):
    # TODO: location-specific fields
    pass

@dataclass
class MissionCard(Card):
    # TODO: mission-specific fields
    pass


@dataclass
class LegacyEntity:
    id: str
    title: str
    entity_type: str  # Feature | Being | Weather | Location | Mission
    presence: int = 1
    progress_threshold: int = -1
    harm_threshold: int = -1
    area: str = "within_reach"  # within_reach | along_the_way | player_area | global
    exhausted: bool = False
    progress: int = 0
    harm: int = 0
    # Weather tokens (simple demo: clouds)
    clouds: int = 0

    def add_progress(self, amount: int) -> None:
        self.progress = max(0, self.progress + max(0, amount))

    def add_harm(self, amount: int) -> None:
        self.harm = max(0, self.harm + max(0, amount))

    def clear_if_threshold(self) -> Optional[str]:
        if self.progress_threshold != -1 and self.progress >= self.progress_threshold:
            return "progress"
        if self.harm_threshold != -1 and self.harm >= self.harm_threshold:
            return "harm"
        return None
    



@dataclass
class RangerState:
    name: str
    hand: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    energy: dict[Aspect, int] = field(default_factory=lambda: {Aspect.AWA: 0, Aspect.FIT: 0, Aspect.SPI: 0, Aspect.FOC: 0})
    injury: int = 0


@dataclass
class GameState:
    ranger: RangerState
    zones: dict[Zone, list[Card]] = field(
        default_factory=lambda: cast(
            dict[Zone, list[Card]], 
            {zone: [] for zone in Zone}
        )
    )
    round_number: int = 1
    # Path deck for Phase 1 draws
    path_deck: list[PathCard] = field(default_factory=lambda: cast(list[PathCard], []))
    path_discard: list[PathCard] = field(default_factory=lambda: cast(list[PathCard], []))


# Action system: derived from state; executed by engine.

@dataclass
class ActionTarget:
    # An action may or may not require a target. If required, the view will present these.
    id: str
    title: str


@dataclass
class Action:
    id: str  # stable identifier for the action option
    name: str  # human-readable label
    aspect: Aspect | str  # required energy type (if is_test), str for non-test actions like Rest
    approach: Approach | str  # legal approach icons to commit (if is_test), str for non-test actions
    is_test: bool = True
    # If the action requires a target, provide candidate targets based on state
    target_provider: Optional[Callable[[GameState], list[ActionTarget]]] = None
    # Computes difficulty for the chosen target (or state)
    difficulty_fn: Callable[[GameState, Optional[str]], int] = lambda _s, _t: 1
    # Effects
    on_success: Callable[[GameState, int, Optional[str]], None] = lambda _s, _e, _t: None
    on_fail: Optional[Callable[[GameState, Optional[str]], None]] = None
    # Source metadata (for display/tracking)
    source_id: Optional[str] = None  # card/entity id or "common"
    source_title: Optional[str] = None


@dataclass
class CommitDecision:
    # Amount of energy committed
    energy: int = 1
    # Indices into the ranger.hand to commit for icons
    hand_indices: list[int] = field(default_factory=lambda: cast(list[int], []))
