# Exhaust Abilities Design

## Overview
Exhaust abilities are "testless" actions that can be activated by exhausting a card. They're fast, safe, and don't trigger interaction fatigue or challenge effects. This document outlines the design for implementing exhaust abilities alongside the ranger token system.

## Core Concepts

### What Makes Exhaust Abilities Special

**Testless & Safe:**
- No difficulty check
- No risk of failure
- No interaction fatigue
- No challenge effects triggered
- "Fast" - you just do the thing

**Cost:**
- Exhausting the card is the cost
- Once exhausted, can't use again until Refresh
- This is paid upfront, not as part of a test

**Not Turn Actions:**
- Technically, exhaust abilities aren't turn actions (in multiplayer rules)
- Can be activated at start/end of turn, any number in a row
- For solo implementation: treat like Rest action (special action type, not a test)

### Example: Peerless Pathfinder
- **Exhaust ability**: "Move your ranger token to a feature. That feature fatigues you."
- **Effect**: Testless ranger token movement + fatigue
- **No targeting risk**: You choose the feature, no test involved

---

## 1. Data Model

### ExhaustAbility Class

Instead of using `Action`, create a dedicated class for exhaust abilities:

```python
@dataclass
class ExhaustAbility:
    """Represents an exhaust ability on a card"""
    id: str  # Unique identifier
    card_id: str  # Card this ability comes from
    name: str  # Display name
    description: str  # What the ability does
    handler: Callable[[GameEngine, str | None], None]  # (engine, target_id) -> None
    target_provider: Callable[[GameState], list[Card]] | None = None  # Optional targeting
    requires_target: bool = False  # Whether this ability needs a target

    def can_activate(self, engine: GameEngine) -> bool:
        """Check if this ability can be activated (card must be ready)"""
        card = engine.state.get_card_by_id(self.card_id)
        return card is not None and not card.exhausted
```

### Why Not Action?

`Action` is designed for tests:
- Has `difficulty_fn` (not needed for exhaust abilities)
- Has `on_success` and `on_fail` (no success/fail for exhaust abilities)
- Has `approach` and `aspect` (exhaust abilities don't test aspects)
- Implies challenge resolution

`ExhaustAbility` is simpler and more explicit.

---

## 2. Card Methods

### Add to Card class:

```python
def get_exhaust_abilities(self) -> list[ExhaustAbility] | None:
    """
    Returns exhaust abilities this card provides.
    Override in subclasses that have exhaust abilities.

    Returns:
        List of ExhaustAbility objects, or None if no exhaust abilities
    """
    return None
```

---

## 3. Role Card Implementation

### Role Cards in GameState

Role cards live in the Player Area zone alongside equipped gear:

```python
@dataclass
class GameState:
    # ... existing fields ...

    # Role card reference for easy access
    # (Also exists in zones[Zone.PLAYER_AREA])
    role_card: Card | None = None
```

**Note:** The role card is ALSO in `zones[Zone.PLAYER_AREA]`. The `role_card` field is just a convenient reference pointer.

### Peerless Pathfinder Implementation

```python
class PeerlessPathfinder(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Peerless Pathfinder", "Explorer"))
        # Role cards have no cost, no aspect requirement
        # They start in play and never leave

    def get_exhaust_abilities(self) -> list[ExhaustAbility]:
        """Exhaust: Move ranger token to feature, that feature fatigues you"""
        return [
            ExhaustAbility(
                id=f"exhaust-{self.id}",
                card_id=self.id,
                name="Move Ranger Token to Feature",
                description="Move your ranger token to a feature. That feature fatigues you.",
                handler=self._move_token_to_feature,
                target_provider=lambda state: state.features_in_play(),
                requires_target=True
            )
        ]

    def _move_token_to_feature(self, engine: GameEngine, target_id: str | None) -> None:
        """Handler for the exhaust ability"""
        if target_id is None:
            engine.add_message("No target selected for ranger token movement.")
            return

        target_card = engine.state.get_card_by_id(target_id)
        if target_card is None:
            engine.add_message("Invalid target for ranger token movement.")
            return

        # Move ranger token to the target feature
        engine.move_ranger_token_to_card(target_card)

        # Target feature fatigues you
        presence = target_card.get_current_presence()
        if presence is not None and presence > 0:
            engine.fatigue_ranger(engine.state.ranger, presence)
```

---

## 4. Game Loop Integration

### Collecting Available Exhaust Abilities

```python
def get_available_exhaust_abilities(self) -> list[ExhaustAbility]:
    """
    Collect all exhaust abilities from ready cards in play.

    Returns:
        List of ExhaustAbility objects that can currently be activated
    """
    abilities = []

    # Check all cards in play (including role card in Player Area)
    for card in self.state.all_cards_in_play():
        if not card.exhausted:
            card_abilities = card.get_exhaust_abilities()
            if card_abilities:
                abilities.extend(card_abilities)

    return abilities
```

### Turn Action Selection

During a turn, the player can choose from:
1. **Tests** (from common tests + card-specific tests)
2. **Exhaust abilities** (from ready cards)
3. **Rest** (special action to end phase)

```python
def get_available_turn_actions(self) -> dict[str, list]:
    """
    Get all available actions for the current turn.

    Returns:
        Dictionary with keys: 'tests', 'exhaust_abilities', 'rest'
    """
    return {
        'tests': self.get_available_tests(),
        'exhaust_abilities': self.get_available_exhaust_abilities(),
        'rest': [self.create_rest_action()]  # Always available
    }
```

### UI Display

```
Available Actions:
  Test: Traverse (FIT + Exploration) [X=presence] -> Overgrown Thicket A
  Test: Hunt for a way through the dense foliage -> Overgrown Thicket A
  Exhaust: Move Ranger Token to Feature (Peerless Pathfinder)
  Rest: End your turn and refresh
```

---

## 5. Activating Exhaust Abilities

### Activation Flow

```python
def activate_exhaust_ability(self, ability: ExhaustAbility, target_id: str | None = None) -> None:
    """
    Activate an exhaust ability.

    Args:
        ability: The ExhaustAbility to activate
        target_id: Optional target for the ability
    """
    # Verify ability can still be activated
    if not ability.can_activate(self):
        self.add_message(f"Cannot activate {ability.name} - card is exhausted or unavailable.")
        return

    # Get the card and exhaust it (cost paid upfront)
    card = self.state.get_card_by_id(ability.card_id)
    if card is None:
        return

    self.add_message(f"Exhausting {card.title} to activate: {ability.name}")
    card.exhausted = True

    # If ability requires a target, ensure one is provided
    if ability.requires_target and target_id is None:
        # This shouldn't happen if UI is correct, but handle gracefully
        self.add_message("Error: Ability requires a target but none provided.")
        return

    # Execute the ability handler
    ability.handler(self, target_id)

    # No challenge resolution, no test - just done!
```

### Key Differences from Tests

**Tests:**
1. Choose action
2. Choose commit
3. Draw challenge
4. Resolve challenge effects
5. Check success/fail
6. Apply consequences

**Exhaust Abilities:**
1. Choose ability (and target if needed)
2. Exhaust card (cost paid)
3. Execute handler
4. Done!

Much simpler, much faster.

---

## 6. Ranger Token System Integration

### GameEngine Methods (from RANGER_TOKEN_DESIGN.md)

```python
def move_ranger_token_to_card(self, card: Card) -> str:
    """Move the ranger token onto a card"""
    self.state.ranger_token_location = card.id
    return f"Your Ranger token moved onto {card.title}."

def move_ranger_token_to_role(self) -> str:
    """Move the ranger token to the ranger's role (default position)"""
    self.state.ranger_token_location = "role"
    return f"Your Ranger token moved to your role."

def get_ranger_token_card(self) -> Card | None:
    """Get the card the ranger token is currently on, if any"""
    if self.state.ranger_token_location is None or self.state.ranger_token_location == "role":
        return None
    return self.state.get_card_by_id(self.state.ranger_token_location)
```

### Initialization

```python
def setup_new_game(ranger_name: str, role_card: Card) -> GameState:
    """Set up a new game with the given ranger and role"""
    ranger = RangerState(...)

    state = GameState(
        ranger=ranger,
        zones={
            Zone.SURROUNDINGS: [],
            Zone.ALONG_THE_WAY: [],
            Zone.WITHIN_REACH: [],
            Zone.PLAYER_AREA: [role_card],  # Role starts in play
        },
        role_card=role_card,  # Convenient reference
        ranger_token_location="role"  # Token starts on role
    )

    return state
```

---

## 7. View Changes

### Displaying Ranger Token Location

```python
def render_state(state: GameState):
    """Render current game state"""

    # ... existing zone rendering ...

    # Ranger Token Status
    print("\n=== Ranger Token ===")
    if state.ranger_token_location == "role":
        print(f"  On your role: {state.role_card.title if state.role_card else 'Unknown'}")
    else:
        token_card = state.get_card_by_id(state.ranger_token_location)
        if token_card:
            print(f"  On: {token_card.title}")
        else:
            print("  Location: Unknown")
```

### Action Selection UI

```python
def choose_turn_action(engine: GameEngine) -> tuple[str, Action | ExhaustAbility | None]:
    """
    Prompt player to choose a turn action.

    Returns:
        Tuple of (action_type, action_object)
        action_type: 'test', 'exhaust', or 'rest'
    """
    actions = engine.get_available_turn_actions()

    print("\nAvailable Actions:")
    index = 1
    action_map = {}

    # Display tests
    for test in actions['tests']:
        print(f"  {index}. Test: {test.name}")
        action_map[index] = ('test', test)
        index += 1

    # Display exhaust abilities
    for ability in actions['exhaust_abilities']:
        card = engine.state.get_card_by_id(ability.card_id)
        card_name = card.title if card else "Unknown"
        print(f"  {index}. Exhaust: {ability.name} ({card_name})")
        action_map[index] = ('exhaust', ability)
        index += 1

    # Display rest
    print(f"  {index}. Rest: End your turn and refresh")
    action_map[index] = ('rest', None)

    # Get player choice
    choice = input("> ").strip()
    # ... handle choice ...
```

---

## 8. Testing Strategy

### Unit Tests Needed

**Ranger Token Movement:**
- Move token to card
- Move token to role
- Get token location
- Token starts on role

**Exhaust Ability Basics:**
- Can't activate when card exhausted
- Can activate when card ready
- Card exhausts after activation
- Can't activate again until refresh

**Peerless Pathfinder:**
- Exhaust ability moves token to target feature
- Target feature fatigues ranger
- Ability requires valid feature target
- Token location updates correctly

**Game Loop Integration:**
- Exhaust abilities appear in available actions
- Only ready cards' abilities appear
- Activating ability doesn't trigger tests/challenges
- Turn continues after activating ability

---

## 9. Implementation Priority

### Phase 1: Ranger Token Basics
1. Add `ranger_token_location` to GameState initialization (default to "role")
2. Implement token movement methods in GameEngine
3. Add view rendering for token location
4. Write tests for token movement

### Phase 2: Exhaust Ability Framework
1. Create `ExhaustAbility` dataclass
2. Add `get_exhaust_abilities()` to Card
3. Implement `get_available_exhaust_abilities()` in engine
4. Implement `activate_exhaust_ability()` in engine

### Phase 3: Peerless Pathfinder
1. Create PeerlessPathfinder class in explorer_cards.py
2. Implement exhaust ability with token movement
3. Add role_card to GameState
4. Update game initialization to include role

### Phase 4: UI Integration
1. Update turn action selection to include exhaust abilities
2. Add "Exhaust:" prefix for clarity
3. Handle targeting for exhaust abilities
4. Display ranger token location in state

### Phase 5: Testing
1. Unit tests for all ranger token methods
2. Unit tests for exhaust ability activation
3. Integration tests for Peerless Pathfinder
4. End-to-end test of full turn with exhaust ability

---

## 10. Future Exhaust Abilities

This framework supports various exhaust ability patterns:

**No Target:**
```python
# Example: "Exhaust: Gain 2 energy of any aspect"
ExhaustAbility(
    id=f"exhaust-{self.id}",
    card_id=self.id,
    name="Gain Energy",
    description="Gain 2 energy of any aspect",
    handler=self._gain_energy,
    requires_target=False
)
```

**Custom Target Provider:**
```python
# Example: "Exhaust: Move a being to an adjacent area"
ExhaustAbility(
    id=f"exhaust-{self.id}",
    card_id=self.id,
    name="Move Being",
    description="Move a being to an adjacent area",
    handler=self._move_being,
    target_provider=lambda state: state.beings_in_play(),
    requires_target=True
)
```

**Complex Effects:**
```python
def _complex_effect(self, engine: GameEngine, target_id: str | None) -> None:
    """Handler can do multiple things"""
    # Draw cards
    engine.state.ranger.draw_card()
    # Move token
    engine.move_ranger_token_to_role()
    # Add progress
    if target_id:
        card = engine.state.get_card_by_id(target_id)
        if card:
            card.add_progress(2)
```

---

## Summary

Exhaust abilities are:
- **Simple**: No tests, no challenges, just execute
- **Safe**: No risk, no reaction from game
- **Powerful**: Often move tokens, manipulate state
- **Costly**: Exhausting is the cost, limits uses per day
- **Distinct**: Separate from Action framework, closer to Rest

This design integrates cleanly with the ranger token system and provides a solid foundation for role cards and other cards with exhaust abilities.
