# Save/Load System Design

## Overview

This document describes the approach for serializing and deserializing game state. The core insight is that **game state is data + behavior**, but only data needs to be saved. Behavior (listeners, abilities, lambdas) is reconstructed from the cards present in the loaded state.

## Design Decision: Custom Serialization

We use custom serialization rather than making GameState directly serializable because:
- Cards are rich objects with methods that return listeners/abilities containing lambdas
- Circular references exist (Card.backside)
- The engine already has `reconstruct()` which rebuilds listeners from cards in play
- Minimal refactoring required

## UI: "Menu" option in Phase 2
- Currently, players mainly make decisions during Phase 2: Ranger Turns.
- These options include playing cards, taking tests, resting, and ending the day.
- We'll add a "Menu" option here, at the bottom, having it lead to choices to save the gamestate, load a gamestate, or "return to title"

## What Gets Saved

### Pure Data (Serialize As-Is)

```
SaveData
├── version: str                          # Schema version for migration
├── round_number: int
├── day_has_ended: bool
│
├── ranger:
│   ├── name: str
│   ├── aspects: dict[Aspect, int]        # Base values
│   ├── energy: dict[Aspect, int]         # Current energy pool
│   ├── injury: int
│   ├── ranger_token_location: str        # Card ID
│   ├── deck: list[CardData]
│   ├── hand: list[CardData]
│   ├── discard: list[CardData]
│   └── fatigue_stack: list[CardData]
│
├── campaign_tracker:
│   ├── day_number: int
│   ├── notable_events: list[str]
│   ├── unlocked_rewards: list[str]
│   ├── active_missions: list[MissionData]
│   ├── cleared_missions: list[MissionData]
│   ├── ranger_deck_card_ids: list[str]
│   ├── ranger_name: str
│   ├── ranger_aspects: dict[Aspect, int]
│   ├── current_location_id: str
│   └── current_terrain_type: str
│
├── role_card_id: str
├── location_id: str
├── weather_id: str | None
├── mission_ids: list[str]
│
├── areas:
│   ├── SURROUNDINGS: list[CardData]
│   ├── ALONG_THE_WAY: list[CardData]
│   ├── WITHIN_REACH: list[CardData]
│   └── PLAYER_AREA: list[CardData]
│
├── path_deck: list[CardData]
├── path_discard: list[CardData]
│
└── challenge_deck:
    ├── deck: list[ChallengeCardData]
    └── discard: list[ChallengeCardData]
```

### CardData Structure

Each card is saved as:

```
CardData
├── card_class: str              # e.g., "BiscuitBasket", "SitkaDoe", "Card"
├── id: str                      # Unique instance ID
│
├── # Mutable state only:
├── exhausted: bool
├── progress: int
├── harm: int
├── unique_tokens: dict[str, int]
├── modifiers: list[ModifierData]
├── attached_to_id: str | None
├── attached_card_ids: list[str]
│
└── backside_id: str | None      # For double-sided cards
```

Note: We do NOT save immutable card data (title, traits, thresholds, etc.) since that comes from the card class definition and JSON. We only save instance-specific mutable state.

### What We Do NOT Save

- `GameEngine.listeners` - Rebuilt by `reconstruct()`
- `GameEngine.constant_abilities` - Rebuilt by `reconstruct()`
- `GameEngine.campaign_guide` - Fresh instance created
- Callback functions (card_chooser, response_decider, etc.) - Provided at engine creation
- Card methods and lambdas - Intrinsic to card classes

## Loading Process

### Step 1: Instantiate Cards

For each CardData in the save:
```python
def instantiate_card(card_data: CardData) -> Card:
    # Look up the card class
    card_class = get_card_class(card_data.card_class)  # e.g., BiscuitBasket

    # Create instance (this loads immutable data from JSON)
    card = card_class()

    # Override the generated ID with saved ID
    card.id = card_data.id

    # Apply mutable state
    card.exhausted = card_data.exhausted
    card.progress = card_data.progress
    card.harm = card_data.harm
    card.unique_tokens = card_data.unique_tokens.copy()
    card.modifiers = [deserialize_modifier(m) for m in card_data.modifiers]

    return card
```

### Step 2: Build Card Registry

Create a dict mapping card IDs to card instances for reference resolution:
```python
card_registry: dict[str, Card] = {}
for card_data in all_cards_in_save:
    card = instantiate_card(card_data)
    card_registry[card.id] = card
```

### Step 3: Resolve References

After all cards are instantiated, resolve ID references:
```python
for card_id, card in card_registry.items():
    card_data = get_card_data(card_id)

    # Resolve attachment references
    card.attached_to_id = card_data.attached_to_id
    card.attached_card_ids = card_data.attached_card_ids

    # Resolve backside reference
    if card_data.backside_id:
        card.backside = card_registry[card_data.backside_id]
```

### Step 4: Build GameState

Populate GameState by placing cards in their saved locations:
```python
state = GameState(
    ranger=RangerState(
        name=save.ranger.name,
        aspects=save.ranger.aspects,
        deck=[card_registry[c.id] for c in save.ranger.deck],
        hand=[card_registry[c.id] for c in save.ranger.hand],
        # ... etc
    ),
    areas={
        Area.SURROUNDINGS: [card_registry[c.id] for c in save.areas.SURROUNDINGS],
        # ... etc
    },
    # ... etc
)
state.ranger.energy = save.ranger.energy  # Set after init
```

### Step 5: Create Engine and Reconstruct

```python
engine = GameEngine(state)
engine.reconstruct()  # Rebuilds listeners and constant abilities
```

**Important**: `reconstruct()` must NOT call `enters_play()` on cards. It should only:
1. Call `get_listeners()` on cards in play and register them
2. Call `enters_hand()` on cards in hand and register returned listeners
3. Call `get_constant_abilities()` on cards in play and register them

## Card Class Registry

We need a mapping from class name strings to actual classes:

```python
CARD_CLASSES = {
    "Card": Card,
    "BiscuitDelivery": BiscuitDelivery,
    "BiscuitBasket": BiscuitBasket,
    "SitkaDoe": SitkaDoe,
    "SitkaBuck": SitkaBuck,
    "HyPimpotChef": HyPimpotChef,
    "QuisiVosRascal": QuisiVosRascal,
    # ... all card classes
}

def get_card_class(class_name: str) -> type[Card]:
    return CARD_CLASSES[class_name]
```

This could be auto-generated by scanning the cards module.

## Handling Double-Sided Cards

Double-sided cards (like BiscuitDelivery/BiscuitBasket) have mutual backside references. When saving:
- Save both sides as separate CardData entries
- Each references the other via `backside_id`

When loading:
- Instantiate both cards
- After all cards exist, link their `backside` references

## Handling Generic Cards

Cards loaded from JSON without a custom class (using base `Card`) need special handling:
- Save: `card_class = "Card"`, plus all the JSON-derived fields
- Load: Create `Card()` with those fields

For these, we may need to save more fields (title, traits, thresholds, etc.) since they aren't defined by a class.

Alternative: Save the JSON source identifier instead:
```
CardData
├── card_class: "Card"
├── json_source: {"title": "Overgrown Thicket", "set": "Woods"}
└── # mutable state...
```

Then on load, call `load_card_fields("Overgrown Thicket", "Woods")` to get base data.

## reconstruct() Enhancements Needed

The current `reconstruct()` only handles:
- Hand cards (enters_hand listeners)
- Constant abilities from in-play cards

It needs to also handle:
- Listeners from in-play cards via `get_listeners()`

```python
def reconstruct(self) -> None:
    self.listeners.clear()
    self.constant_abilities.clear()

    # Listeners from hand
    for card in self.state.ranger.hand:
        listeners = card.enters_hand(self)
        if listeners:
            self.listeners.extend(listeners)

    # Listeners from cards in play
    for card in self.state.all_cards_in_play():
        listeners = card.get_listeners()
        if listeners:
            self.listeners.extend(listeners)

        abilities = card.get_constant_abilities()
        if abilities:
            self.constant_abilities.extend(abilities)
```

## File Format

Use JSON for human-readability and debugging:

```json
{
  "version": "1.0",
  "round_number": 3,
  "day_has_ended": false,
  "ranger": {
    "name": "Test Ranger",
    "aspects": {"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1},
    "energy": {"AWA": 1, "FIT": 2, "SPI": 0, "FOC": 1},
    "deck": [...],
    ...
  },
  ...
}
```

## Demo Scenarios

With save/load implemented, demo scenarios are simply save files:
1. Play to desired state
2. Save
3. Use that save as a "scenario"

No separate scenario format needed.

## Migration Strategy

Include a version field. When loading:
1. Check version
2. If old version, run migration functions to update schema
3. Load normalized data

## Open Questions (Answered)

1. **FacedownCard handling**: Cards placed facedown have a special wrapper. How to serialize?
   - We'll go with this solution: Save the frontside card ID + a `facedown: true` flag

2. **Challenge deck state**: The physical deck order matters. We'll save full deck and discard state.

3. **Message queue**: Do we save pending messages? Yes, eventually I want a always-on log of the last N messages so players can "scroll up" and get a reminder for what happened recently.

4. **last_test_target**: I think we should actually only allow saving between, not during, tests. Alongside the gameplay options of cards to play, tests to take, and ending the day, we can implement saving and loading as a "Menu" option that leads to a submenu with save/load/quit-to-title options.
