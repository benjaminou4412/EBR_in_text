# Constant Abilities System Design

## Overview

Constant Abilities (borrowing terminology from Arkham Horror LCG) are **passive/static abilities that modify game rules while a card is in play**. They are characterized by "while" language rather than triggered "when/after" effects.

Examples from EBR cards:
- "While you perform a test that interacts with a card in the same area as this feature, reduce your effort by 1."
- "Reduce the presence of all other beings in the same area as this card by 1."
- "If the weather is inclement, you cannot interact with this feature."
- "While your ranger token is on this feature you can use the below ability"
- "While your ranger token is on this card, prevent all fatigue you would suffer from the weather."
- **Obstacle keyword**: "You cannot interact past this card."
- **Friendly keyword**: "This card doesn't fatigue you when you interact past it."

## Relationship to Existing Systems

### ValueModifier System
The existing `ValueModifier` system handles simple numeric modifications to card stats:
- Target: `presence`, `equip_value`, `energy_cost`
- Amount: integer delta
- Minimum result: floor value

**ValueModifier will remain** for these simple stat modifications. It's lightweight and sufficient for cards that just say "reduce the presence of X by 1" without complex conditions.

### ConstantAbility System (New)
ConstantAbilities handle more complex game rule modifications:
- Blocking actions (cannot interact, cannot travel)
- Conditional effects (only active when condition met)
- Context-dependent modifications (effort reduction only in same area)
- Granting/enabling abilities
- Complex fatigue exemptions

**When to use which:**
- Use `ValueModifier` for: Simple stat changes on other cards (presence, equip, cost)
- Use `ConstantAbility` for: Everything else (preventions, conditional effects, complex modifications)

### EventListener System
EventListeners remain for **reactive** abilities (triggered effects):
- "When X happens, do Y"
- "After you succeed at a test, you may..."
- "Response:" abilities

ConstantAbilities are for **passive** modifications to game rules, not reactions to events.

## Design

### Data Structures

```python
class ConstantAbilityType(Enum):
    """Types of passive abilities that modify game rules"""

    # Modifications (change values during calculation)
    MODIFY_EFFORT = "modify_effort"
    MODIFY_DIFFICULTY = "modify_difficulty"
    MODIFY_FATIGUE = "modify_fatigue"

    # Preventions (block actions from happening)
    PREVENT_INTERACTION = "prevent_interaction"
    PREVENT_INTERACTION_PAST = "prevent_interaction_past"  # Obstacle
    PREVENT_RANGER_TOKEN_MOVE = "prevent_ranger_token_move"
    PREVENT_TRAVEL = "prevent_travel"
    PREVENT_REST = "prevent_rest"
    PREVENT_PLAY_CARD = "prevent_play_card"

    # Exemptions (ignore normally-applied rules)
    EXEMPT_FROM_FATIGUE = "exempt_from_fatigue"  # Friendly
    EXEMPT_FROM_INTERACTION_FATIGUE = "exempt_from_interaction_fatigue"

    # Enablement (grant access to abilities)
    GRANT_ABILITY = "grant_ability"
    GRANT_KEYWORD = "grant_keyword"

@dataclass
class ConstantAbility:
    """A continuous/passive ability that modifies game rules while active"""
    ability_type: ConstantAbilityType
    source_card_id: str

    # Condition function: determines when this ability is "active"
    # Returns True if the ability should currently apply
    condition_fn: Callable[[GameState], bool]

    # Effect function: what the ability does (type depends on ability_type)
    # Context dict contains relevant game state for the current action
    # Return type varies by ability_type:
    #   - Modifications: int (delta to apply)
    #   - Preventions: tuple[bool, str | None] (should_block, error_message)
    #   - Exemptions: bool (should_exempt)
    #   - Enablement: bool (is_enabled)
    effect_fn: Callable[[GameState, dict], Any]

    # Optional: human-readable description for debugging
    description: str = ""

    def is_active(self, state: GameState) -> bool:
        """Check if this ability's condition is currently met"""
        return self.condition_fn(state)
```

### Context Dictionaries

Different ability types receive different context information:

**MODIFY_EFFORT:**
```python
{
    "base_effort": int,
    "test_action": Action,
    "target_id": str,
    "performing_ranger_id": str  # for multiplayer
}
```

**PREVENT_INTERACTION / PREVENT_INTERACTION_PAST:**
```python
{
    "target_id": str,
    "performing_ranger_id": str,
    "interaction_type": str  # "test", "exhaust_ability", etc.
}
```

**PREVENT_RANGER_TOKEN_MOVE:**
```python
{
    "current_location": str,
    "new_location": str,
    "move_source": str  # "test", "effect", etc.
}
```

**PREVENT_TRAVEL:**
```python
{
    "current_location_id": str,
    "destination_location_id": str | None
}
```

**EXEMPT_FROM_FATIGUE / EXEMPT_FROM_INTERACTION_FATIGUE:**
```python
{
    "amount": int,
    "source": str,  # "weather", "interaction", "card_effect", etc.
    "source_card_id": str | None,
    "performing_ranger_id": str
}
```

**MODIFY_FATIGUE:**
```python
{
    "base_amount": int,
    "source": str,
    "source_card_id": str | None,
    "performing_ranger_id": str
}
```

## Engine Integration

### GameEngine Changes

```python
class GameEngine:
    def __init__(self):
        # ... existing ...
        self.constant_abilities: list[ConstantAbility] = []

    def register_constant_ability(self, ability: ConstantAbility):
        """Register a constant ability from a card entering play"""
        self.constant_abilities.append(ability)
        if ability.description:
            self.add_message(f"  → {ability.description}")

    def remove_constant_abilities_by_source(self, card_id: str):
        """Remove all constant abilities from a specific card (for cleanup)"""
        self.constant_abilities = [
            a for a in self.constant_abilities
            if a.source_card_id != card_id
        ]

    def get_active_abilities(self, ability_type: ConstantAbilityType) -> list[ConstantAbility]:
        """Get all active abilities of a specific type"""
        return [
            ability for ability in self.constant_abilities
            if ability.ability_type == ability_type and ability.is_active(self.state)
        ]
```

### Helper Methods for Common Checks

#### Modifications

```python
def apply_effort_modifiers(self, base_effort: int, action: Action, target_id: str) -> int:
    """Apply all active effort modifications and return final effort"""
    modified = base_effort
    context = {
        "base_effort": base_effort,
        "test_action": action,
        "target_id": target_id,
        "performing_ranger_id": "player"  # TODO: multiplayer
    }

    for ability in self.get_active_abilities(ConstantAbilityType.MODIFY_EFFORT):
        delta = ability.effect_fn(self.state, context)
        if delta != 0:
            source_card = self.state.get_card_by_id(ability.source_card_id)
            source_name = source_card.title if source_card else "unknown"
            self.add_message(f"  {source_name}: effort {delta:+d} (now {modified + delta})")
            modified += delta

    return max(0, modified)  # effort can't go negative

def calculate_interaction_fatigue(self, target_id: str) -> int:
    """Calculate fatigue from interacting with target, including modifications"""
    # Get base fatigue from cards between you and target (existing logic)
    base_fatigue = self._calculate_base_interaction_fatigue(target_id)

    # Apply modifications
    context = {
        "base_amount": base_fatigue,
        "source": "interaction",
        "source_card_id": target_id,
        "performing_ranger_id": "player"
    }

    # Check exemptions first (Friendly keyword)
    for ability in self.get_active_abilities(ConstantAbilityType.EXEMPT_FROM_INTERACTION_FATIGUE):
        should_exempt = ability.effect_fn(self.state, context)
        if should_exempt:
            return 0  # completely exempt

    # Apply modifications
    modified_fatigue = base_fatigue
    for ability in self.get_active_abilities(ConstantAbilityType.MODIFY_FATIGUE):
        delta = ability.effect_fn(self.state, context)
        modified_fatigue += delta

    return max(0, modified_fatigue)
```

#### Preventions

```python
def check_can_interact_with(self, target_id: str) -> str | None:
    """
    Check if interaction with target is allowed.
    Returns error message if blocked, None if allowed.
    """
    context = {
        "target_id": target_id,
        "performing_ranger_id": "player",
        "interaction_type": "test"
    }

    for ability in self.get_active_abilities(ConstantAbilityType.PREVENT_INTERACTION):
        should_block, msg = ability.effect_fn(self.state, context)
        if should_block:
            return msg or "Cannot interact with this card."

    return None

def check_can_interact_past(self, card_id: str, target_id: str) -> str | None:
    """
    Check if you can interact past a card to reach target (Obstacle check).
    Returns error message if blocked, None if allowed.
    """
    context = {
        "target_id": target_id,
        "obstacle_card_id": card_id,
        "performing_ranger_id": "player"
    }

    for ability in self.get_active_abilities(ConstantAbilityType.PREVENT_INTERACTION_PAST):
        # Only check abilities from this specific card
        if ability.source_card_id == card_id:
            should_block, msg = ability.effect_fn(self.state, context)
            if should_block:
                return msg or "Cannot interact past this card."

    return None

def check_can_move_ranger_token(self, new_location_id: str) -> str | None:
    """
    Check if ranger token can be moved to new location.
    Returns error message if blocked, None if allowed.
    """
    context = {
        "current_location": self.state.ranger_token_location,
        "new_location": new_location_id,
        "move_source": "effect"  # or "test" depending on caller
    }

    for ability in self.get_active_abilities(ConstantAbilityType.PREVENT_RANGER_TOKEN_MOVE):
        should_block, msg = ability.effect_fn(self.state, context)
        if should_block:
            return msg or "Cannot move ranger token."

    return None

def check_can_travel(self, destination_id: str | None = None) -> str | None:
    """
    Check if travel is allowed.
    Returns error message if blocked, None if allowed.
    """
    context = {
        "current_location_id": "TODO",  # from location card
        "destination_location_id": destination_id
    }

    for ability in self.get_active_abilities(ConstantAbilityType.PREVENT_TRAVEL):
        should_block, msg = ability.effect_fn(self.state, context)
        if should_block:
            return msg or "Cannot travel."

    return None
```

## Card Implementation Examples

### Caustic Mulcher (Complex Prevention)

```python
class CausticMulcher(Card):
    def enters_play(self, engine: GameEngine, area: Area):
        super().enters_play(engine, area)

        # "Ranger tokens on this card can only be moved by the below test"
        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.PREVENT_RANGER_TOKEN_MOVE,
            source_card_id=self.id,
            condition_fn=lambda state: state.ranger_token_location == self.id,
            effect_fn=lambda state, ctx: (
                True,  # block the move
                "Your ranger token is stuck to Caustic Mulcher! Use its test to escape."
            ),
            description="Ranger token stuck to Caustic Mulcher"
        ))

        # "If your ranger token is on this card, you cannot travel"
        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.PREVENT_TRAVEL,
            source_card_id=self.id,
            condition_fn=lambda state: state.ranger_token_location == self.id,
            effect_fn=lambda state, ctx: (
                True,
                "Cannot travel while your ranger token is on Caustic Mulcher!"
            ),
            description="Travel blocked by Caustic Mulcher"
        ))

    def discard_from_play(self, engine: GameEngine):
        super().discard_from_play(engine)
        engine.remove_constant_abilities_by_source(self.id)
```

### Dense Undergrowth (Conditional Effort Modification)

```python
class DenseUndergrowth(Card):
    """
    "While you perform a test that interacts with a card in the same area as
    this feature, reduce your effort by 1."
    """
    def enters_play(self, engine: GameEngine, area: Area):
        super().enters_play(engine, area)

        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.MODIFY_EFFORT,
            source_card_id=self.id,
            # Active if: this card is ready
            condition_fn=lambda state: not self.exhausted,
            # Apply -1 if target is in same area as this card
            effect_fn=lambda state, ctx: (
                -1 if self._same_area_as_target(state, ctx.get("target_id")) else 0
            ),
            description="Dense Undergrowth impedes tests in its area (-1 effort)"
        ))

    def _same_area_as_target(self, state: GameState, target_id: str | None) -> bool:
        if not target_id:
            return False
        my_area = state.get_area_of_card(self.id)
        target_area = state.get_area_of_card(target_id)
        return my_area == target_area and my_area is not None

    def discard_from_play(self, engine: GameEngine):
        super().discard_from_play(engine)
        engine.remove_constant_abilities_by_source(self.id)
```

### Sheltering Canopy (Ranger Token Fatigue Protection)

```python
class ShelteringCanopy(Card):
    """
    "While your ranger token is on this card, prevent all fatigue you would
    suffer from the weather."
    """
    def enters_play(self, engine: GameEngine, area: Area):
        super().enters_play(engine, area)

        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.EXEMPT_FROM_FATIGUE,
            source_card_id=self.id,
            # Active if ranger token is here
            condition_fn=lambda state: state.ranger_token_location == self.id,
            # Exempt if source is weather
            effect_fn=lambda state, ctx: ctx.get("source") == "weather",
            description="Sheltering Canopy protects from weather fatigue"
        ))

    def discard_from_play(self, engine: GameEngine):
        super().discard_from_play(engine)
        engine.remove_constant_abilities_by_source(self.id)
```

### Hostile Being (Conditional Interaction Prevention)

```python
class HostileBeing(Card):
    """
    "If the weather is inclement, you cannot interact with this feature."
    """
    def enters_play(self, engine: GameEngine, area: Area):
        super().enters_play(engine, area)

        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.PREVENT_INTERACTION,
            source_card_id=self.id,
            # Always potentially active (condition checked in effect_fn)
            condition_fn=lambda state: True,
            effect_fn=lambda state, ctx: self._check_weather_block(state, ctx),
            description="Hostile Being blocks interaction in inclement weather"
        ))

    def _check_weather_block(self, state: GameState, ctx: dict) -> tuple[bool, str | None]:
        # Only block if targeting this card specifically
        if ctx.get("target_id") != self.id:
            return (False, None)

        # Check if weather is inclement
        weather_cards = state.get_cards_by_type(CardType.WEATHER)
        if weather_cards:
            weather = weather_cards[0]
            if "Inclement" in weather.traits:
                return (True, "Cannot interact with Hostile Being in inclement weather!")

        return (False, None)

    def discard_from_play(self, engine: GameEngine):
        super().discard_from_play(engine)
        engine.remove_constant_abilities_by_source(self.id)
```

## Refactoring Existing Keywords

### Obstacle Keyword

**Current implementation:** Hardcoded in engine's `get_valid_test_targets()` and travel logic

**New implementation:** Register as ConstantAbility in Card base class

```python
# In Card.enters_play()
def enters_play(self, engine: GameEngine, area: Area):
    # ... existing logic ...

    # Auto-register keyword abilities
    if Keyword.OBSTACLE in self.keywords:
        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.PREVENT_INTERACTION_PAST,
            source_card_id=self.id,
            # Only active when ready
            condition_fn=lambda state: not self.exhausted,
            effect_fn=lambda state, ctx: (
                True,
                f"Cannot interact past {self.title} (Obstacle)"
            ),
            description=f"{self.title} has Obstacle"
        ))

        # Also prevents travel
        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.PREVENT_TRAVEL,
            source_card_id=self.id,
            condition_fn=lambda state: not self.exhausted,
            effect_fn=lambda state, ctx: (
                True,
                f"Cannot travel while {self.title} is ready (Obstacle)"
            ),
            description=f"{self.title} blocks travel (Obstacle)"
        ))
```

### Friendly Keyword

**Current implementation:** Hardcoded in fatigue calculation

**New implementation:** Register as ConstantAbility

```python
# In Card.enters_play()
def enters_play(self, engine: GameEngine, area: Area):
    # ... existing logic ...

    if Keyword.FRIENDLY in self.keywords:
        engine.register_constant_ability(ConstantAbility(
            ability_type=ConstantAbilityType.EXEMPT_FROM_INTERACTION_FATIGUE,
            source_card_id=self.id,
            condition_fn=lambda state: True,  # always active
            # Exempt if the fatigue source is this card
            effect_fn=lambda state, ctx: ctx.get("source_card_id") == self.id,
            description=f"{self.title} is Friendly"
        ))
```

## Integration Points

### In perform_action()

```python
def perform_action(self, action: Action, decision: CommitDecision, target_id: str | None):
    # ... existing step 1: pay costs ...

    # Step 2: Commit effort
    base_effort = self._calculate_base_effort(decision)

    # NEW: Apply effort modifiers from constant abilities
    final_effort = self.apply_effort_modifiers(base_effort, action, target_id)

    # ... rest of test resolution ...
```

### In get_valid_test_targets()

```python
def get_valid_test_targets(self, action: Action) -> list[Card]:
    candidates = action.target_provider(self.state)
    valid = []

    for candidate in candidates:
        # NEW: Check if interaction is prevented
        prevention_error = self.check_can_interact_with(candidate.id)
        if prevention_error:
            continue

        # NEW: Check if any obstacles block interaction
        if self._has_blocking_obstacle(candidate.id):
            continue

        valid.append(candidate)

    return valid

def _has_blocking_obstacle(self, target_id: str) -> bool:
    """Check if any obstacles prevent interaction with target"""
    # Get all cards between you and target
    between_cards = self._get_cards_between_player_and_target(target_id)

    for card in between_cards:
        error = self.check_can_interact_past(card.id, target_id)
        if error:
            return True

    return False
```

### In travel logic (Phase 3)

```python
def phase3_travel(self):
    # Check if travel is allowed
    travel_error = self.check_can_travel()
    if travel_error:
        self.add_message(f"Cannot travel: {travel_error}")
        return

    # ... rest of travel logic ...
```

## Cleanup Pattern

All cards that register constant abilities **must** clean them up when leaving play:

```python
def discard_from_play(self, engine: GameEngine):
    super().discard_from_play(engine)
    engine.remove_constant_abilities_by_source(self.id)
```

Consider adding this to the base `Card.discard_from_play()` method to make it automatic.

## Testing Strategy

### Unit Tests

```python
def test_effort_modification():
    """Test that effort modifiers from constant abilities apply correctly"""
    engine = create_test_engine()
    dense_undergrowth = DenseUndergrowth()
    target = SitkaBuck()

    # Place both in same area
    engine.move_card(dense_undergrowth.id, Area.ALONG_THE_WAY)
    engine.move_card(target.id, Area.ALONG_THE_WAY)

    # Perform test with base effort 3
    decision = CommitDecision(energy=3, hand_indices=[])
    final_effort = engine.apply_effort_modifiers(3, test_action, target.id)

    assert final_effort == 2  # 3 - 1 from Dense Undergrowth

def test_obstacle_prevention():
    """Test that Obstacle keyword prevents interaction"""
    engine = create_test_engine()
    thicket = OvergrownThicket()  # has Obstacle
    target = SunberryBramble()

    # Place obstacle between player and target
    engine.move_card(thicket.id, Area.WITHIN_REACH)
    engine.move_card(target.id, Area.ALONG_THE_WAY)

    # Try to interact with target
    valid_targets = engine.get_valid_test_targets(target_test_action)

    assert target not in valid_targets  # blocked by obstacle

def test_friendly_exemption():
    """Test that Friendly keyword exempts from interaction fatigue"""
    engine = create_test_engine()
    calypsaRanger = CalypsaRangerMentor()  # has Friendly
    target = SitkaBuck()

    # Place friendly card between player and target
    engine.move_card(calypsaRanger.id, Area.WITHIN_REACH)
    engine.move_card(target.id, Area.ALONG_THE_WAY)

    # Calculate interaction fatigue
    fatigue = engine.calculate_interaction_fatigue(target.id)

    assert fatigue == 0  # Calypsaexempts
```

### Integration Tests

Test full turn sequences with multiple constant abilities active simultaneously.

## Implementation Plan

### Phase 1: Foundation (New Systems)
1. Add `ConstantAbilityType` enum to models.py
2. Add `ConstantAbility` dataclass to models.py
3. Add `constant_abilities` list to GameEngine
4. Add register/remove/get_active methods to GameEngine

### Phase 2: Area Rename
1. Rename `Zone` enum to `Area` throughout codebase
2. Update all references (variables, parameters, comments)
3. Update tests

### Phase 3: Helper Methods
1. Implement `apply_effort_modifiers()`
2. Implement `calculate_interaction_fatigue()` with modifications
3. Implement prevention check methods (can_interact, can_interact_past, etc.)

### Phase 4: Keyword Refactoring
1. Refactor Obstacle to use ConstantAbility
2. Refactor Friendly to use ConstantAbility
3. Update `get_valid_test_targets()` to use new prevention checks
4. Remove old hardcoded Obstacle/Friendly logic

### Phase 5: Integration & Testing
1. Update `perform_action()` to call effort modifiers
2. Add constant ability cleanup to base `Card.discard_from_play()`
3. Update existing tests
4. Add new tests for constant abilities

### Phase 6: New Card Implementations
1. Implement Caustic Mulcher with ranger token prevention
2. Implement Dense Undergrowth with effort modification
3. Implement Sheltering Canopy with fatigue exemption
4. Add tests for each

## Future Considerations

### Multiplayer
When implementing multiplayer, constant abilities need ranger context:
- "performing_ranger_id" in context dicts
- Some abilities affect only the ranger token owner
- Some abilities affect all rangers

### Ability Ordering
Currently, constant abilities apply in registration order. If complex cards create order-dependency issues, consider:
- Priority/layer system (like MTG)
- Timestamps for conflict resolution
- Player chooses order when ambiguous

### Performance
With many cards in play, checking all constant abilities on every action could get slow. Optimizations:
- Index abilities by type for O(1) lookup
- Cache active abilities between game state changes
- Only recalculate when relevant cards enter/leave play or exhaust/ready

### Debugging
Consider adding:
- `engine.debug_constant_abilities()` method to list all active abilities
- Logging when abilities apply/block actions
- UI command to inspect what abilities are affecting a card

## Summary

The Constant Ability system provides:
- **Unified framework** for passive/static card abilities
- **Clear separation** from ValueModifiers (simple stats) and EventListeners (reactions)
- **Extensible** for future cards with complex interactions
- **Testable** with isolated unit tests for each ability type
- **Maintainable** by removing hardcoded keyword logic

This system handles the full spectrum of "while" effects in EBR while remaining lightweight enough for the current implementation scale.
