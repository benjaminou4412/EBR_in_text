from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any


# Core data structures: pure state and card data

@dataclass
class ApproachIcons:
    counts: Dict[str, int] = field(default_factory=dict)

    def get(self, approach: str) -> int:
        return int(self.counts.get(approach, 0) or 0)


@dataclass
class Card:
    id: str
    title: str
    card_type: str
    rules_texts: List[str] = field(default_factory=list)
    approach: ApproachIcons = field(default_factory=ApproachIcons)


@dataclass
class Entity:
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
    hand: List[Card] = field(default_factory=list)
    energy: Dict[str, int] = field(default_factory=lambda: {"AWA": 0, "FIT": 0, "SPI": 0, "FOC": 0})
    injury: int = 0


@dataclass
class GameState:
    ranger: RangerState
    entities: List[Entity]


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
    aspect: str  # required energy type
    approach: str  # legal approach icons to commit
    # If the action requires a target, provide candidate targets based on state
    target_provider: Optional[Callable[[GameState], List[ActionTarget]]] = None
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
    # Indices into the ranger.hand to commit for icons
    hand_indices: List[int] = field(default_factory=list)

