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

### Reusing the Action Class

Exhaust abilities will reuse the existing `Action` class with a new `is_exhaust` flag. This keeps the codebase simple and leverages existing infrastructure for display and selection.

#### Why Reuse Action?

**Pragmatic Benefits:**
- ✅ Homogeneous display - everything is still `list[Action]`
- ✅ Existing infrastructure - view.py already handles Actions
- ✅ Precedent exists - Rest and End Day already use Action with `is_test=False`
- ✅ Simpler integration - no new class to wire into selection logic

**Pattern Already Exists:**
```python
# Rest action (current codebase)
Action(
    id="rest",
    name="Rest",
    is_test=False,
    on_success=lambda e, eff, t: e.rest_ranger(),
)
```

**Potential Future Use Case:**
Some abilities might both exhaust AND perform a test (e.g., "Exhaust: Perform a FOC+Reason test"). Having both `is_test` and `is_exhaust` as independent flags supports this.

#### Action Class Changes

Add `is_exhaust` field to the existing Action dataclass:

```python
@dataclass
class Action:
    # ... existing fields ...
    is_test: bool = True
    is_exhaust: bool = False  # NEW: marks exhaust abilities

    # Note: Both can be true! (exhaust AND test)
    # Both false = phase action (Rest, End Day)
```

#### Exhaust Abilities as Actions

```python
# Example exhaust ability action
Action(
    id="peerless-pathfinder-exhaust",
    name="Move Ranger Token to Feature",
    verb="Move Ranger Token",  # For display
    is_test=False,
    is_exhaust=True,  # NEW FLAG
    target_provider=lambda state: state.features_in_play(),
    on_success=lambda engine, effort, target: move_token_handler(engine, target),
    source_id="peerless-pathfinder-role-id",
    source_title="Peerless Pathfinder",
)
```

**Unused Fields:**
- `difficulty_fn` - Not called when `is_test=False`
- `on_fail` - Not called when `is_test=False`
- `aspect`/`approach` - Can be `None` for non-tests
- These are sentinel values meaning "not applicable"

---

## 2. Card Methods

### Add to Card class:

```python
def get_exhaust_abilities(self) -> list[Action] | None:
    """
    Returns exhaust abilities this card provides as Actions.
    Override in subclasses that have exhaust abilities.

    Returns:
        List of Action objects with is_exhaust=True, or None if no exhaust abilities
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

    def get_exhaust_abilities(self) -> list[Action]:
        """Exhaust: Move ranger token to feature, that feature fatigues you"""
        return [
            Action(
                id=f"exhaust-{self.id}",
                name="Move Ranger Token to Feature",
                verb="Move Ranger Token",
                is_test=False,
                is_exhaust=True,
                target_provider=lambda state: state.features_in_play(),
                on_success=self._move_token_to_feature,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _move_token_to_feature(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        """Handler for the exhaust ability"""
        if target is None:
            engine.add_message("No target selected for ranger token movement.")
            return

        # Exhaust this role card as the cost
        engine.add_message(self.exhaust())

        # Move ranger token to the target feature
        engine.move_ranger_token_to_card(target)

        # Target feature fatigues you
        presence = target.get_current_presence()
        if presence is not None and presence > 0:
            engine.fatigue_ranger(engine.state.ranger, presence)
```

---

## 4. Game Loop Integration

### Collecting Available Exhaust Abilities

Exhaust abilities are collected as Actions with `is_exhaust=True`:

```python
def get_available_exhaust_abilities(self) -> list[Action]:
    """
    Collect all exhaust abilities from ready cards in play.

    Returns:
        List of Action objects with is_exhaust=True that can currently be activated
    """
    abilities = []

    # Check all cards in play (including role card in Player Area)
    for card in self.state.all_cards_in_play():
        if not card.is_exhausted():  # Use getter to check exhaustion
            card_abilities = card.get_exhaust_abilities()
            if card_abilities:
                abilities.extend(card_abilities)

    return abilities
```

### Turn Action Selection

During a turn, the player can choose from a unified list of Actions:

```python
def get_available_turn_actions(self) -> list[Action]:
    """
    Get all available actions for the current turn.
    Returns a single flat list of Actions (tests, exhaust abilities, and phase actions).
    """
    actions = []

    # Add tests (is_test=True, is_exhaust=False)
    actions.extend(self.get_available_tests())

    # Add exhaust abilities (is_test=False, is_exhaust=True)
    actions.extend(self.get_available_exhaust_abilities())

    # Add phase actions (is_test=False, is_exhaust=False)
    actions.append(self.create_rest_action())

    return actions
```

**Note:** All actions are now in a single homogeneous list. The view layer can use `is_test` and `is_exhaust` flags to format display differently if desired.

### UI Display

The view can optionally group by action type:

```
Available Actions:
  1. [Test] Traverse (FIT + Exploration) -> Overgrown Thicket A
  2. [Test] Hunt for a way through -> Overgrown Thicket A
  3. [Exhaust] Move Ranger Token to Feature (Peerless Pathfinder)
  4. Rest
```

Or display as a flat list (current approach):
```
Available Actions:
  1. Traverse
  2. Hunt for a way through
  3. Move Ranger Token to Feature
  4. Rest
```

---

## 5. Activating Exhaust Abilities

### Activation Flow

Exhaust abilities use the same `perform_action()` flow as tests and other actions:

```python
# In perform_action()
def perform_action(self, action: Action, decision: CommitDecision, target_id: Optional[str]) -> ChallengeOutcome:
    # Resolve target once
    target_card: Card | None = self.state.get_card_by_id(target_id) if target_id else None

    # For exhaust abilities, exhaust the source card first
    if action.is_exhaust and action.source_id:
        source_card = self.state.get_card_by_id(action.source_id)
        if source_card:
            if source_card.is_exhausted():
                self.add_message(f"Cannot activate - {source_card.title} is already exhausted.")
                return ChallengeOutcome(difficulty=0, base_effort=0, modifier=0,
                                       symbol=ChallengeIcon.SUN, resulting_effort=0, success=False)
            self.add_message(source_card.exhaust())

    # Non-test actions (exhaust abilities, Rest, End Day) skip challenge resolution
    if not action.is_test:
        action.on_success(self, 0, target_card)
        return ChallengeOutcome(difficulty=0, base_effort=0, modifier=0,
                               symbol=ChallengeIcon.SUN, resulting_effort=0, success=True)

    # ... rest of test logic ...
```

**Key Points:**
- Exhaust abilities have `is_exhaust=True` and `is_test=False`
- Source card is exhausted **before** executing the ability
- No challenge resolution, just execute `on_success` handler directly
- Uses the same unified flow as Rest/End Day

### Key Differences from Tests

**Tests (`is_test=True`):**
1. Choose action
2. Choose commit
3. Draw challenge
4. Resolve challenge effects
5. Check success/fail
6. Apply consequences

**Exhaust Abilities (`is_test=False`, `is_exhaust=True`):**
1. Choose ability (and target if needed)
2. Exhaust source card (cost paid)
3. Execute `on_success` handler
4. Done!

Much simpler, much faster.

**Phase Actions (`is_test=False`, `is_exhaust=False`):**
1. Choose action (Rest, End Day)
2. Execute `on_success` handler
3. Done!

No exhaustion cost, no test.

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
