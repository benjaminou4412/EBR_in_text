# Campaign System Design

## Overview

This document describes the Campaign Guide, Campaign Tracker, and Mission card systems that provide narrative structure and gameplay objectives to Earthborne Rangers.

## Core Concepts

### Campaign Guide
The Campaign Guide is a collection of narrative entries that:
- Display story text to the player
- Check conditionals based on game state and campaign tracker
- Manipulate game state (spawn cards, discard cards, etc.)
- Record Notable Events to the Campaign Tracker
- Recursively trigger other entries

In the physical game, this is a thick guidebook with hundreds of entries. In our implementation, each entry is a method in the `CampaignGuide` class with full `GameEngine` access.

### Campaign Tracker
The Campaign Tracker is the persistent save state between in-game days. It records:
- Day number
- Current location and terrain type
- Active missions (with progress bubbles if needed)
- Completed missions
- Unlocked reward cards
- Notable events (for conditional checks)

This is the only game state that persists when a day ends.

### Mission Cards
Mission cards are special cards that:
- Enter play in the Surroundings (like Weather and Location cards)
- Cannot be moved from the Surroundings
- Have mission objectives implemented as EventListeners
- Some missions record to Campaign Tracker (persist between days)
- Some missions (like "Helping Hand") do NOT record and expire at end of day

## Architecture

### 1. CampaignTracker Class

**Location:** `models.py`

```python
@dataclass
class CampaignTracker:
    """Persistent save state between in-game days"""
    day_number: int = 1
    current_location: str = "White Sky"
    current_terrain: str = "grassland"
    active_missions: List[str] = field(default_factory=list)  # Mission card IDs
    mission_progress: Dict[str, int] = field(default_factory=dict)  # mission_id -> progress bubbles
    completed_missions: List[str] = field(default_factory=list)
    unlocked_rewards: List[str] = field(default_factory=list)
    notable_events: Set[str] = field(default_factory=set)

    def has_event(self, event_id: str) -> bool:
        """Check if a notable event has occurred"""
        return event_id in self.notable_events

    def add_event(self, event_id: str):
        """Record a notable event"""
        self.notable_events.add(event_id)

    def is_mission_active(self, mission_id: str) -> bool:
        """Check if a mission is currently active"""
        return mission_id in self.active_missions

    def complete_mission(self, mission_id: str):
        """Mark a mission as completed"""
        if mission_id in self.active_missions:
            self.active_missions.remove(mission_id)
            self.completed_missions.append(mission_id)
            if mission_id in self.mission_progress:
                del self.mission_progress[mission_id]

    def add_mission_progress(self, mission_id: str, amount: int = 1):
        """Add progress bubbles to a mission in the tracker"""
        if mission_id not in self.mission_progress:
            self.mission_progress[mission_id] = 0
        self.mission_progress[mission_id] += amount

    def get_mission_progress(self, mission_id: str) -> int:
        """Get progress bubbles for a mission"""
        return self.mission_progress.get(mission_id, 0)
```

**Important:** Mission progress bubbles in the tracker are **distinct** from progress tokens on Mission cards in play:
- Progress bubbles in tracker persist between days
- Progress tokens on Mission cards are cleared when the day ends
- Both are valid ways to track mission objectives depending on the mission's design

### 2. CampaignGuide Class

**Location:** New file `src/campaign_guide.py`

```python
from typing import Optional
from src.engine import GameEngine

class CampaignGuide:
    """
    Campaign Guide entry system.

    Each entry is a method named 'entry_{id}' or 'entry_{id}_{subentry}'.
    Entries have full GameEngine access and can:
    - Display narrative text via engine.queue_message()
    - Check conditionals via engine.campaign_tracker
    - Manipulate game state (spawn cards, discard, etc.)
    - Recursively trigger other entries
    - Record notable events
    """

    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.tracker = engine.campaign_tracker

    def trigger_entry(self, entry_id: str, subentry: Optional[str] = None):
        """
        Main entry point - routes to specific entry methods.

        Args:
            entry_id: The main entry identifier (e.g., "ws_1")
            subentry: Optional subentry identifier (e.g., "elder_dialogue")

        Raises:
            ValueError: If the entry method is not implemented
        """
        method_name = f"entry_{entry_id}"
        if subentry:
            method_name += f"_{subentry}"

        method = getattr(self, method_name, None)
        if method:
            method()
        else:
            raise ValueError(f"Campaign entry {entry_id}/{subentry} not implemented")

    # =========================================================================
    # EXAMPLE ENTRIES (to be replaced with actual campaign content)
    # =========================================================================

    def entry_ws_1(self):
        """White Sky arrival - Day 1"""
        self.engine.queue_message("You arrive at White Sky as the sun rises over the Valley...")

        if self.tracker.day_number == 1:
            # First day setup
            self.engine.spawn_mission("mission_the_valley_calls")
            self.tracker.add_event("arrived_white_sky")

    def entry_ws_2(self):
        """White Sky - Met the elder"""
        if self.tracker.has_event("met_elder"):
            self.engine.queue_message("The elder nods knowingly as you approach again.")
        else:
            self.engine.queue_message("An elder Ranger greets you warmly...")
            self.tracker.add_event("met_elder")
            self.trigger_entry("ws_2", "elder_dialogue")

    def entry_ws_2_elder_dialogue(self):
        """Subentry - elder gives you a mission"""
        self.engine.queue_message("'Will you help us investigate the tremors to the north?'")
        self.engine.spawn_mission("mission_investigate_tremors")
```

**Design Notes:**
- All entries are methods in one `CampaignGuide` class (mirrors the physical book being one book)
- Entry naming convention: `entry_{id}` or `entry_{id}_{subentry}`
- Full `GameEngine` access allows arbitrary game state manipulation
- Story text uses `queue_message()` for now (UI improvements can come later)
- No separate JSON file defining entries; method names are the source of truth

### 3. Mission Card Implementation

**Location:** New file `src/cards/mission_cards.py`

```python
from src.models import Card, CardType, Area, EventListener, EventType, TimingType, Trait
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine import GameEngine

class MissionCard(Card):
    """
    Base class for Mission cards.

    Mission cards:
    - Enter play in the Surroundings
    - Cannot be moved
    - Use EventListeners for mission objectives
    - Optionally record to Campaign Tracker (default: True)
    """

    def __init__(self, should_record: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.card_type = CardType.MISSION
        self.area = Area.SURROUNDINGS
        self.should_record = should_record  # False for missions like "Helping Hand"

    def enters_play(self, engine: 'GameEngine'):
        """Add mission to campaign tracker when entering play"""
        super().enters_play(engine)
        if self.should_record and self.card_id not in engine.campaign_tracker.active_missions:
            engine.campaign_tracker.active_missions.append(self.card_id)

    def on_cleared(self, engine: 'GameEngine'):
        """
        Called when mission completes (reaches progress threshold).
        Override in subclasses for mission-specific completion effects.
        """
        if self.should_record:
            engine.campaign_tracker.complete_mission(self.card_id)
        self.display_completion_text(engine)

    def display_completion_text(self, engine: 'GameEngine'):
        """Override in subclasses for mission-specific completion text"""
        engine.queue_message(f"Mission Complete: {self.name}")


# =========================================================================
# EXAMPLE MISSION IMPLEMENTATION
# =========================================================================

class TheValleyCalls(MissionCard):
    """
    Starting mission: Explore 3 locations.

    Adds 1 progress when you travel to a new location.
    Completes when it has 3 progress.
    """

    def __init__(self):
        super().__init__(
            card_id="mission_the_valley_calls",
            name="The Valley Calls",
            traits=[Trait.MISSION, Trait.STORY],
            progress_threshold=3,
            harm_threshold=-2,  # Cannot be harmed
            should_record=True,
        )

    def get_listeners(self) -> List[EventListener]:
        """Add progress when you travel to a new location"""
        return [
            EventListener(
                event_type=EventType.TRAVEL,  # Will need to add this event type
                timing=TimingType.AFTER,
                active=lambda eng: self.card_id in [c.card_id for c in eng.get_cards_in_area(Area.SURROUNDINGS)],
                effect_fn=self._on_travel,
                source_card_id=self.card_id,
            )
        ]

    def _on_travel(self, engine: 'GameEngine', event_data: dict):
        """Add progress when traveling to new location"""
        engine.add_progress(self.card_id, 1)
        engine.queue_message(f"Mission progress: {self.name} ({engine.get_card_by_id(self.card_id).progress}/3)")

    def display_completion_text(self, engine: 'GameEngine'):
        engine.queue_message("═" * 50)
        engine.queue_message("MISSION COMPLETE: The Valley Calls")
        engine.queue_message("You've proven yourself as a Ranger of the Valley.")
        engine.queue_message("═" * 50)
        # Could trigger campaign guide entry here
        engine.campaign_guide.trigger_entry("valley_calls_complete")
```

### 4. GameEngine Integration

**Location:** `src/engine.py`

Add to `GameEngine.__init__`:
```python
from src.campaign_guide import CampaignGuide

# In __init__:
self.campaign_tracker = CampaignTracker()
self.campaign_guide = CampaignGuide(self)
```

Add helper method:
```python
def spawn_mission(self, mission_id: str):
    """
    Spawn a mission card into the Surroundings.

    Args:
        mission_id: The card_id of the mission to spawn
    """
    from src.cards.mission_cards import create_mission_card

    mission_card = create_mission_card(mission_id)
    self.state.surroundings.append(mission_card)
    mission_card.enters_play(self)
    self.queue_message(f"New Mission: {mission_card.name}")
```

### 5. Save/Load System

**Location:** New file `src/save_system.py`

```python
import json
from typing import TYPE_CHECKING
from src.models import CampaignTracker

if TYPE_CHECKING:
    from src.engine import GameEngine

def save_campaign(game_engine: 'GameEngine', filepath: str):
    """
    Save campaign tracker to JSON file.

    This is the only persistent state between days.
    """
    save_data = {
        'day_number': game_engine.campaign_tracker.day_number,
        'current_location': game_engine.campaign_tracker.current_location,
        'current_terrain': game_engine.campaign_tracker.current_terrain,
        'active_missions': game_engine.campaign_tracker.active_missions,
        'mission_progress': game_engine.campaign_tracker.mission_progress,
        'completed_missions': game_engine.campaign_tracker.completed_missions,
        'unlocked_rewards': game_engine.campaign_tracker.unlocked_rewards,
        'notable_events': list(game_engine.campaign_tracker.notable_events),
    }

    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)

def load_campaign(filepath: str) -> CampaignTracker:
    """
    Load campaign tracker from JSON file.

    Returns a CampaignTracker instance that can be assigned to GameEngine.
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    return CampaignTracker(
        day_number=data['day_number'],
        current_location=data['current_location'],
        current_terrain=data['current_terrain'],
        active_missions=data['active_missions'],
        mission_progress=data.get('mission_progress', {}),
        completed_missions=data['completed_missions'],
        unlocked_rewards=data['unlocked_rewards'],
        notable_events=set(data['notable_events']),
    )
```

## Implementation Notes

### Mission Card Factory

We'll need a factory function to instantiate mission cards by ID:

```python
# In src/cards/mission_cards.py

def create_mission_card(mission_id: str) -> MissionCard:
    """Factory function to create mission cards by ID"""
    mission_classes = {
        "mission_the_valley_calls": TheValleyCalls,
        # Add more as implemented
    }

    cls = mission_classes.get(mission_id)
    if cls is None:
        raise ValueError(f"Unknown mission ID: {mission_id}")

    return cls()
```

### New Event Types Needed

To support mission objectives, we'll need to add new event types to `EventType` enum in `models.py`:

```python
class EventType(Enum):
    # ... existing events ...
    TRAVEL = "travel"
    MISSION_COMPLETE = "mission_complete"
    LOCATION_CLEARED = "location_cleared"
    # Add more as needed for mission objectives
```

These can be added incrementally as missions require them.

### End of Day Handling

When a day ends, we need to:
1. Save campaign tracker state
2. Clear all cards from play (except those recorded in tracker)
3. For active missions that should persist, they'll be respawned at start of next day based on `campaign_tracker.active_missions`

This will be implemented as part of the Day system (separate from this design doc).

### Display Formatting

For now, all story text uses `queue_message()`. Future UI improvements could include:
- Special formatting for story text (different color, borders)
- Pausing for user confirmation before continuing
- Formatted mission completion notifications

## Future Considerations

### Campaign Guide Entry Organization

As the campaign grows, we may want to organize entries into separate modules or use a more sophisticated routing system. For now, one big `CampaignGuide` class mirrors the physical book structure.

### Dynamic Entry Loading

If we later want to support user-created campaigns or modding, we could add JSON-based entry definitions that get parsed into callable logic. This is not a current priority.

### Mission Progress UI

Mission cards in the Surroundings should display prominently in the UI, potentially with their own dedicated section showing:
- Mission name
- Objective description
- Progress (both card progress and tracker progress bubbles if applicable)
- Story trait indicator

## Testing Strategy

### Unit Tests
- `CampaignTracker` methods (event tracking, mission completion, etc.)
- Mission card `enters_play()` and `on_cleared()` behavior
- Mission factory function

### Integration Tests
- Campaign Guide entry triggering and recursion
- Mission objectives via EventListeners
- End of day persistence (mission state saved to tracker)
- Load/save round-trip (tracker state preserved)

### Example Test
```python
def test_mission_completes_and_records():
    engine = create_test_engine()
    engine.spawn_mission("mission_the_valley_calls")

    # Simulate 3 travels
    for _ in range(3):
        trigger_event(engine, EventType.TRAVEL, {})

    mission = engine.get_card_by_id("mission_the_valley_calls")
    assert mission.progress >= 3
    assert "mission_the_valley_calls" in engine.campaign_tracker.completed_missions
    assert "mission_the_valley_calls" not in engine.campaign_tracker.active_missions
```

## Summary

This design provides:
- **CampaignTracker**: Persistent save state between days
- **CampaignGuide**: Narrative entry system with full engine access
- **MissionCard**: Special card type for gameplay objectives
- **Save/Load**: JSON-based campaign persistence

The system is designed to be simple and extensible, allowing campaign content to be added incrementally as methods in `CampaignGuide` and subclasses of `MissionCard`.
