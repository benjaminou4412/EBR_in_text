# Ranger Token System Design

## Overview
Each ranger has a unique token that can be placed on cards, representing the ranger's focus or physical presence. This document outlines the design for implementing ranger tokens.

## Core Rules (from rulebook)
- Each Ranger has a single token unique to them
- Tokens can be moved to cards in play by game effects
- When a ranger token is on a card, OTHER rangers commit +1 effort to test that card (cumulative per token)
- Some cards clear when every Ranger's token is on them (instead of progress threshold)
- When token would be discarded or is not on a card, it moves to the ranger's role card
- Tokens represent requiring the ranger's undivided attention or physical presence

---

## 1. Data Model

### Current State (already in GameState):
```python
@dataclass
class GameState:
    # ... existing fields ...
    ranger_token_location: str | None = None  # Can be card_id or "role"
```

### For Multiplayer (Future):
When we support multiple rangers, we'll need:
```python
@dataclass
class GameState:
    # ... existing fields ...

    # Map ranger name to token location
    ranger_tokens: dict[str, str] = field(default_factory=dict)  # {ranger_name: card_id or "role"}
```

For now, we'll use the single `ranger_token_location` and refactor later.

---

## 2. Token Movement Operations

### Add to GameEngine:

```python
def move_ranger_token_to_card(self, card: Card) -> str:
    """
    Move the ranger token onto a card.

    Args:
        card: The card to place the token on

    Returns:
        Message describing the token movement
    """
    self.state.ranger_token_location = card.id
    return f"Your Ranger token moved onto {card.title}."

def move_ranger_token_to_role(self) -> str:
    """
    Move the ranger token to the ranger's role (default position).

    Returns:
        Message describing the token movement
    """
    self.state.ranger_token_location = "role"
    return f"Your Ranger token moved to your role."

def get_ranger_token_card(self) -> Card | None:
    """
    Get the card the ranger token is currently on, if any.

    Returns:
        The card with the token, or None if token is on role
    """
    if self.state.ranger_token_location is None or self.state.ranger_token_location == "role":
        return None

    return self.state.get_card_by_id(self.state.ranger_token_location)

def discard_ranger_token(self) -> str:
    """
    Discard the ranger token (moves it back to role).

    Returns:
        Message describing the token discard
    """
    if self.state.ranger_token_location == "role":
        return "Your Ranger token is already on your role."

    self.state.ranger_token_location = "role"
    return "Your Ranger token discarded - moved back to your role."
```

---

## 3. Card Clearing with Ranger Tokens

### Special Threshold Type

Some cards clear when all ranger tokens are on them, not when reaching a progress threshold. We need to represent this in the Card model.

### Option A: Special String Value
Use a special string like `"ranger"` in the `progress_threshold` field:

```python
@dataclass
class Card:
    # ... existing fields ...
    progress_threshold: int | str | None = None  # Can be int or "ranger"
```

**Pros:**
- Simple, reuses existing field
- JSON can easily specify `"ranger"` as threshold

**Cons:**
- Type confusion (int | str)
- Less explicit

### Option B: Separate Boolean Field
Add a new field specifically for ranger-token clearing:

```python
@dataclass
class Card:
    # ... existing fields ...
    clears_with_ranger_tokens: bool = False  # True if cleared by ranger tokens
```

**Pros:**
- Explicit, clear intent
- Type-safe

**Cons:**
- Extra field

**Recommendation:** Use Option A for simplicity. The JSON already uses strings like "2R" for thresholds in multiplayer, so `"ranger"` fits the pattern.

### JSON Representation:
```json
{
  "id": "woods-008-caustic-mulcher",
  "title": "Caustic Mulcher",
  "progress_threshold": "ranger",
  ...
}
```

### JSON Loader Update:
```python
def load_card_fields(title: str, card_set: str) -> dict:
    # ... existing loading ...

    # Handle progress_threshold
    if "progress_threshold" in card_data:
        threshold = card_data["progress_threshold"]
        if threshold == "ranger":
            fields["progress_threshold"] = "ranger"
        elif isinstance(threshold, str) and threshold.endswith("R"):
            # Multiplayer threshold like "2R"
            fields["progress_threshold"] = int(threshold[:-1])
        elif threshold == -1:
            fields["progress_threshold"] = None
        else:
            fields["progress_threshold"] = threshold
```

---

## 4. Clearing Logic

### Update Card.clear_if_threshold():

```python
def clear_if_threshold(self, engine: GameEngine) -> str | None:
    """
    Check if this card should clear based on progress, harm, or ranger tokens.

    Returns:
        "progress", "harm", "ranger", or None
    """
    # Check progress threshold
    if self.progress_threshold is not None:
        if self.progress_threshold == "ranger":
            # Check if all ranger tokens are on this card
            # For now (solo), just check if THE ranger token is on this card
            if engine.state.ranger_token_location == self.id:
                return "ranger"
        elif isinstance(self.progress_threshold, int) and self.progress >= self.progress_threshold:
            return "progress"

    # Check harm threshold
    if self.harm_threshold is not None and self.harm >= self.harm_threshold:
        return "harm"

    return None
```

### Update Engine Clear Handling:

```python
def check_and_clear_cards(self):
    """Check all cards in play and clear any that meet their threshold"""
    cards_to_clear = []

    for card in self.state.all_cards_in_play():
        clear_type = card.clear_if_threshold(self)
        if clear_type:
            cards_to_clear.append((card, clear_type))

    for card, clear_type in cards_to_clear:
        if clear_type == "progress":
            self.add_message(f"{card.title} cleared (progress threshold reached)!")
            self.clear_card(card)
        elif clear_type == "harm":
            self.add_message(f"{card.title} cleared (harm threshold reached)!")
            self.clear_card(card)
        elif clear_type == "ranger":
            self.add_message(f"{card.title} cleared (all Ranger tokens present)!")
            self.clear_card(card)
            # Return ranger token to role when card clears
            self.move_ranger_token_to_role()
```

---

## 5. When Cards Leave Play

When a card with a ranger token on it leaves play (discarded, cleared, etc.), the token should return to role.

### Update discard_card_and_attachments():

```python
def discard_card_and_attachments(self, card: Card) -> list[str]:
    """
    When a card leaves play, discard it and all attached cards.
    If ranger token is on this card, return it to role.
    """
    messages = []

    # Check if ranger token is on this card
    if self.state.ranger_token_location == card.id:
        messages.append("Ranger token returned to role.")
        self.state.ranger_token_location = "role"

    # ... rest of existing discard logic ...
```

---

## 6. Multiplayer Considerations (Future)

When we support multiple rangers, we'll need:

### Extended Data Model:
```python
@dataclass
class GameState:
    rangers: list[RangerState] = field(default_factory=list)  # Multiple rangers
    ranger_tokens: dict[str, str] = field(default_factory=dict)  # {ranger_name: location}
```

### Extended Clear Logic:
```python
def clear_if_threshold(self, engine: GameEngine) -> str | None:
    if self.progress_threshold == "ranger":
        # Check if ALL ranger tokens are on this card
        all_tokens_present = all(
            location == self.id
            for location in engine.state.ranger_tokens.values()
        )
        if all_tokens_present:
            return "ranger"
```

### Interaction Penalty (OTHER Rangers):
```python
def get_test_difficulty(self, engine: GameEngine, target_card: Card) -> int:
    """Calculate test difficulty including ranger token penalties"""
    base_difficulty = target_card.get_base_difficulty()

    # Count ranger tokens on target card (excluding current ranger)
    other_tokens = sum(
        1 for ranger_name, location in engine.state.ranger_tokens.items()
        if location == target_card.id and ranger_name != engine.current_ranger.name
    )

    return base_difficulty + other_tokens
```

---

## 7. Travel Restrictions

Some cards (like Caustic Mulcher) block travel when your ranger token is on them.

### Add Card Method:
```python
@dataclass
class Card:
    # ... existing fields ...

    def blocks_travel(self) -> bool:
        """
        Check if this card blocks travel when ranger token is on it.
        Override in specific card classes (like CausticMulcher).
        """
        return False
```

### Update GameEngine:
```python
def can_travel(self) -> tuple[bool, str | None]:
    """
    Check if ranger can travel.
    Returns (can_travel, reason_if_not)
    """
    token_card = self.get_ranger_token_card()
    if token_card and token_card.blocks_travel():
        return False, f"Cannot travel while your Ranger Token is on {token_card.title}."

    return True, None
```

---

## 8. View Changes

### Rendering Ranger Token Location:

```python
def render_state(state: GameState, engine: GameEngine = None):
    """Render current game state, including ranger token location"""

    # ... existing rendering ...

    # Show ranger token location
    print("\n=== Ranger Token ===")
    if state.ranger_token_location == "role" or state.ranger_token_location is None:
        print("  Location: On your role")
    else:
        token_card = state.get_card_by_id(state.ranger_token_location)
        if token_card:
            print(f"  Location: On {token_card.title}")
        else:
            print("  Location: Unknown")

def render_card_detail(card: Card, display_id: str = None):
    """Render detailed card information, including ranger tokens"""

    # ... existing rendering ...

    # Show if ranger token is on this card
    # (Need engine context to check - pass it in or add to Card?)
    if hasattr(card, '_has_ranger_token') and card._has_ranger_token:
        print(f"  [Ranger Token on this card]")
```

---

## 9. Testing Strategy

### Unit Tests Needed:
- Move token to card
- Move token to role
- Token returns to role when card discards
- Token returns to role when card clears (ranger threshold)
- Clear condition with ranger token (solo)
- Travel blocking when token on blocking card

### Future Multiplayer Tests:
- Multiple ranger tokens on same card
- Interaction penalty for other rangers
- Clear condition requires ALL tokens
- Token independence (one ranger's token doesn't affect another ranger's tests)

---

## 10. Implementation Priority

### Phase 1: Basic Token Movement
1. Ensure `ranger_token_location` field exists in GameState (already done!)
2. Implement token movement methods in GameEngine
3. Default token to "role" on game start
4. Add view rendering for token location

### Phase 2: Token Return on Card Leave Play
1. Update `discard_card_and_attachments()` to return token
2. Update `clear_card()` to return token
3. Test token returns in various scenarios

### Phase 3: Ranger Token Clearing
1. Update JSON loader to handle `"ranger"` threshold
2. Update `clear_if_threshold()` to check ranger token
3. Add clearing logic for ranger-threshold cards
4. Test Caustic Mulcher clearing

### Phase 4: Travel Blocking
1. Add `blocks_travel()` method to Card
2. Implement in CausticMulcher
3. Add `can_travel()` check in engine
4. Test travel blocking

### Phase 5: Multiplayer (Future)
1. Extend to support multiple rangers
2. Implement interaction penalty
3. Update clear logic for all tokens
4. Extensive multiplayer testing

---

## 11. Caustic Mulcher Integration

With this system, Caustic Mulcher can be implemented:

### Sun Effect:
```python
def _sun_effect(self, engine: GameEngine) -> bool:
    """If there is another active being, exhaust it and attach it to this biomeld.
    If not, move your Ranger Token to this biomeld."""

    # Try to find another active being
    beings = [c for c in engine.state.all_cards_in_play()
              if CardType.BEING in c.card_types
              and c.id != self.id
              and not c.exhausted]

    if beings:
        # Attach being
        target = engine.card_chooser(engine, beings)
        target.exhausted = True
        target.attach_to(self)
        return True
    else:
        # Move ranger token
        engine.move_ranger_token_to_card(self)
        return True
```

### Static Ability (blocks travel):
```python
class CausticMulcher(Card):
    def blocks_travel(self) -> bool:
        """Cannot travel while ranger token is on Caustic Mulcher"""
        return True
```

### Clearing:
In JSON:
```json
{
  "progress_threshold": "ranger",
  ...
}
```

The card clears when the ranger token is on it (solo mode).

---

## Summary

The ranger token system is relatively simple:
- **Storage**: Single field `ranger_token_location` (card_id or "role")
- **Movement**: Engine methods to move token
- **Clearing**: Special "ranger" threshold type
- **Cleanup**: Token returns to role when card leaves play
- **Future**: Extend to multiple tokens for multiplayer

This system integrates cleanly with the attachment system and completes the foundation needed for Caustic Mulcher!
