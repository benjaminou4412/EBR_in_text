# Attachment System Design

## Overview
Cards can attach to other cards (or to a ranger's role). This document outlines the design for implementing attachments, face-up/down mechanics, and ranger tokens.

## Core Rules (from rulebook)
- Attached cards are placed underneath the card they're attached to
- **Faceup** attached cards are "in play"
- **Facedown** attached cards are NOT "in play"
- No limit to number of attachments per card
- When attaching facedown: discard any tokens from the card
- When card leaves play: discard all cards attached to it
- Cards can attach to your role (still interactable)
- Challenge effects on role-attached cards resolve as if within reach
- Role-attached ready cards fatigue you during ALL interactions
- Cards can attach to already-attached cards (nested attachments)

---

## 1. Card Model Changes

### Add to Card dataclass (in models.py):

```python
@dataclass
class Card:
    # ... existing fields ...

    # Mutable state variables (add to existing section)
    attached_to_id: str | None = None  # ID of card this is attached to, or "role" for role attachment
    attached_cards: list[Card] = field(default_factory=list)  # Cards attached to this card
    facedown_original: Card | None = None  # If this IS a facedown placeholder, points to the original card
```

### Design Rationale:
- `attached_to_id`:
  - `None` = not attached to anything (normal)
  - `"role"` = attached to ranger's role (special case)
  - `card_id` = attached to another card
- `attached_cards`: List maintains order and allows nested attachments
- `facedown_original`:
  - If `None`, this is a normal faceup card
  - If set, this card is a facedown placeholder pointing to the hidden original
  - The original card exists outside zones while facedown

### Face-Down Card Philosophy:
Face-down cards are **not just a flag** - they are completely separate Card objects that act as placeholders. When a card flips facedown:
1. The **original card** is preserved outside of zones (on the heap)
2. A **new placeholder Card** is created with minimal/null properties
3. The placeholder has `facedown_original` pointing to the original
4. The placeholder takes the original's place in zones/attachments
5. Face-down cards are truly "blank cards" - they have no properties except what specific effects may grant them

This design enables effects like "treat this facedown card as a Feature with presence 2 and Obstacle keyword" by simply setting those fields on the placeholder.

---

## 2. Attachment Operations

### Key Insight: Attachments Stay in Zones
**Important:** When a card attaches to another card, it **stays in its zone**. Attachments are metadata relationships, not structural zone changes. The `attached_to_id` field simply tracks the relationship.

Example: If Card B (in Within Reach) attaches to Card A (also in Within Reach), B remains in the Within Reach zone list. The attachment is just metadata.

**Exception:** Facedown attached cards are filtered out of "in play" queries (see section 3).

### Core Methods to Add to Card class:

```python
def is_facedown(self) -> bool:
    """Check if this card is a face-down placeholder"""
    return self.facedown_original is not None

def is_faceup(self) -> bool:
    """Check if this card is face-up (normal state)"""
    return self.facedown_original is None

def attach_to(self, target: Card | str) -> str:
    """
    Attach this card to a target (Card or "role").
    Card stays in its current zone - this is just metadata.

    Args:
        target: Either a Card object or the string "role"

    Returns:
        Message describing the attachment
    """
    if isinstance(target, str) and target == "role":
        self.attached_to_id = "role"
        return f"{self.title} attached to role."
    else:
        self.attached_to_id = target.id
        target.attached_cards.append(self)
        return f"{self.title} attached to {target.title}."

def detach(self, engine: GameEngine) -> str:
    """
    Detach this card from whatever it's attached to.
    Requires engine context to look up parent card.

    Returns message describing the detachment.
    """
    if self.attached_to_id is None:
        return f"{self.title} is not attached to anything."

    old_attachment = self.attached_to_id

    # Remove from parent's attached_cards list
    if self.attached_to_id != "role":
        parent = engine.state.get_card_by_id(self.attached_to_id)
        if parent and self in parent.attached_cards:
            parent.attached_cards.remove(self)

    self.attached_to_id = None

    return f"{self.title} detached from {old_attachment}."
```

---

## 3. Face-Down Card Operations

### Engine-Level Methods (in GameEngine):

```python
def flip_card_facedown(self, original_card: Card,
                       special_properties: dict | None = None) -> Card:
    """
    Flip a card face-down, creating a placeholder.
    The original card is preserved outside zones.

    Args:
        original_card: The card to flip down
        special_properties: Optional dict of properties for the placeholder
                           e.g., {"presence": 2, "keywords": {Keyword.OBSTACLE}}

    Returns:
        The face-down placeholder Card
    """
    # Clear tokens from ORIGINAL before flipping (physically knocking them off!)
    original_card.unique_tokens.clear()
    original_card.progress = 0
    original_card.harm = 0

    # Create minimal placeholder
    placeholder = Card(
        id=f"facedown-{original_card.id}",
        title="[Face-down Card]",
        facedown_original=original_card  # Pointer to real card
    )

    # Apply special properties if specified by an effect
    if special_properties:
        for key, value in special_properties.items():
            setattr(placeholder, key, value)

    # Replace in zones (card stays in same zone, just swapped with placeholder)
    for zone, cards in self.state.zones.items():
        if original_card in cards:
            idx = cards.index(original_card)
            cards[idx] = placeholder
            break

    # Replace in attachments if attached
    if original_card.attached_to_id:
        if original_card.attached_to_id != "role":
            parent = self.state.get_card_by_id(original_card.attached_to_id)
            if parent:
                idx = parent.attached_cards.index(original_card)
                parent.attached_cards[idx] = placeholder
        placeholder.attached_to_id = original_card.attached_to_id

    # Transfer any cards that were attached to original
    placeholder.attached_cards = original_card.attached_cards
    original_card.attached_cards = []

    return placeholder

def flip_card_faceup(self, facedown_card: Card) -> Card:
    """
    Flip a face-down card face-up, restoring the original.

    Args:
        facedown_card: The face-down placeholder to flip

    Returns:
        The original Card (now face-up)
    """
    if not facedown_card.is_facedown():
        raise ValueError(f"{facedown_card.title} is not face-down!")

    original = facedown_card.facedown_original

    # Replace in zones (placeholder swapped back with original)
    for zone, cards in self.state.zones.items():
        if facedown_card in cards:
            idx = cards.index(facedown_card)
            cards[idx] = original
            break

    # Replace in attachments if attached
    if facedown_card.attached_to_id:
        if facedown_card.attached_to_id != "role":
            parent = self.state.get_card_by_id(facedown_card.attached_to_id)
            if parent:
                idx = parent.attached_cards.index(facedown_card)
                parent.attached_cards[idx] = original
        original.attached_to_id = facedown_card.attached_to_id

    # Restore any cards that were attached to placeholder
    original.attached_cards = facedown_card.attached_cards

    # Placeholder is now orphaned and will be garbage collected
    return original
```

---

## 4. GameState Changes

### Add to GameState dataclass:

```python
@dataclass
class GameState:
    # ... existing fields ...

    # Ranger token tracking
    ranger_token_location: str | None = None  # Can be card_id or zone name
```

### Add Helper Methods to GameState:

```python
def cards_attached_to_role(self) -> list[Card]:
    """
    Get all cards attached to the ranger's role.
    Role attachments exist in zones like normal cards.
    """
    result = []
    for zone_cards in self.zones.values():
        for card in zone_cards:
            if card.attached_to_id == "role":
                result.append(card)
    return result

def all_cards_in_play(self) -> list[Card]:
    """
    Get all cards in play.

    Rules:
    - Faceup cards in zones are in play (including faceup attached cards)
    - Facedown ATTACHED cards are NOT in play
    - Facedown NON-ATTACHED cards ARE in play (they're blank placeholders in zones)

    Since attached cards stay in zones, we just iterate zones and filter out
    facedown attached cards.
    """
    result = []

    for zone_cards in self.zones.values():
        for card in zone_cards:
            # Skip facedown attached cards - they're NOT in play per rules
            if card.is_facedown() and card.attached_to_id is not None:
                continue
            result.append(card)

    return result

def discard_card_and_attachments(self, card: Card) -> list[str]:
    """
    When a card leaves play, discard it and all attached cards.
    Since attached cards are in zones, we need to remove them all.
    Returns list of messages.
    """
    messages = []

    # Recursively discard all attached cards first
    for attached in card.attached_cards[:]:  # Copy list to avoid modification during iteration
        messages.extend(self.discard_card_and_attachments(attached))

    # Remove from zone
    for zone_cards in self.zones.values():
        if card in zone_cards:
            zone_cards.remove(card)
            break

    # If this is a facedown placeholder, we should discard the original too
    if card.is_facedown():
        # The original is not in play, but we should handle it appropriately
        # For now, just note that the original will be garbage collected
        pass

    # Add to path discard (or ranger discard if ranger card)
    self.path_discard.append(card)
    card.attached_cards.clear()
    card.attached_to_id = None

    messages.append(f"{card.title} discarded.")
    return messages
```

---

## 5. Ranger Token System

### RangerState Changes:

```python
@dataclass
class RangerState:
    # ... existing fields ...

    # No changes needed - token location tracked in GameState
```

### Token Helper Methods in GameEngine:

```python
def move_ranger_token_to_zone(self, zone: Zone) -> str:
    """Move ranger token to a zone"""
    self.state.ranger_token_location = zone.value
    return f"Ranger token moved to {zone.value}."

def move_ranger_token_to_card(self, card: Card) -> str:
    """Move ranger token onto a card"""
    self.state.ranger_token_location = card.id
    return f"Ranger token moved onto {card.title}."

def get_ranger_token_card(self) -> Card | None:
    """Get the card the ranger token is on, if any"""
    if self.state.ranger_token_location is None:
        return None

    # Check if it's a card ID
    return self.state.get_card_by_id(self.state.ranger_token_location)

def can_travel(self) -> tuple[bool, str | None]:
    """
    Check if ranger can travel.
    Returns (can_travel, reason_if_not)
    """
    # Check if token is on a card that blocks travel
    token_card = self.get_ranger_token_card()
    if token_card:
        # Check for cards like Caustic Mulcher that block travel
        # TODO: Implement proper blocking check (probably a card method)
        return False, f"Cannot travel while your Ranger Token is on {token_card.title}."

    return True, None
```

---

## 6. Refresh Phase Changes

### Update phase4_refresh() in GameEngine:

```python
def phase4_refresh(self):
    """
    Phase 4: Refresh
    - Ready all cards EXCEPT:
      - Cards attached to certain beings (like Caustic Mulcher)
    - Restore energy
    - Suffer injury fatigue
    - Draw 1 ranger card
    """
    self.add_message(f"Begin Phase 4: Refresh")

    # Step 1: Ready all cards in play (except attached beings)
    for card in self.state.all_cards_in_play():
        # Check if this card is attached to something that prevents readying
        if card.attached_to_id is not None and card.attached_to_id != "role":
            parent = self.state.get_card_by_id(card.attached_to_id)
            if parent and self._card_prevents_attached_ready(parent):
                # Skip readying this card
                continue

        if card.exhausted:
            card.exhausted = False
            # Note: Don't spam messages about every ready

    # ... rest of refresh phase ...

def _card_prevents_attached_ready(self, card: Card) -> bool:
    """
    Check if a card prevents attached beings from readying.
    TODO: This should probably be a card method or trait check.
    """
    # For now, hardcode Caustic Mulcher check
    # In future, could be a keyword or card method
    return "Caustic Mulcher" in card.title
```

---

## 7. Interaction Fatigue Changes

### Update interaction_fatigue() in GameEngine:

Cards attached to role always count as being between you and other cards.

```python
def interaction_fatigue(self, ranger: RangerState, target: Card) -> None:
    """Apply fatigue from cards between ranger and target, INCLUDING role attachments"""

    # Get role-attached cards (they're in zones, just filter by attached_to_id)
    role_attached = self.state.cards_attached_to_role()
    # Filter for ready, non-friendly, faceup cards
    ready_role_attached = [c for c in role_attached
                          if not c.exhausted
                          and Keyword.FRIENDLY not in c.keywords
                          and c.is_faceup()]

    # Get cards between ranger and target
    cards_between = self.state.get_cards_between_ranger_and_target(target)
    target_zone = self.state.get_card_zone_by_id(target.id)

    # ... existing logic for cards_between ...

    # ALWAYS apply fatigue from role-attached ready cards
    if ready_role_attached:
        all_cards = self.state.all_cards_in_play()
        self.add_message("Cards attached to your role fatigue you:")
        for card in ready_role_attached:
            card_display_id = get_display_id(all_cards, card)
            self.add_message(f"    {card_display_id} fatigues you.")
            curr_presence = card.get_current_presence()
            if curr_presence is not None:
                self.fatigue_ranger(ranger, curr_presence)
```

---

## 8. View Changes

### Rendering Attachments:

```python
def render_card_detail(card: Card, display_id: str = None):
    """Render detailed card information, including attachments"""

    # ... existing rendering ...

    # Show if this is a facedown placeholder
    if card.is_facedown():
        print(f"  [FACE-DOWN CARD]")
        # Don't show other details for facedown cards unless they have special properties
        if card.presence:
            print(f"  Presence: {card.presence}")
        if card.keywords:
            print(f"  Keywords: {', '.join(k.value for k in card.keywords)}")
        return  # Don't show other details

    # Show attachments
    if card.attached_cards:
        print(f"\n  Attached Cards:")
        for attached in card.attached_cards:
            facestate = "face-down" if attached.is_facedown() else "face-up"
            print(f"    - {attached.title} ({facestate})")
            # Recursively show nested attachments
            if attached.attached_cards:
                for nested in attached.attached_cards:
                    nested_state = "face-down" if nested.is_facedown() else "face-up"
                    print(f"        - {nested.title} ({nested_state})")

    if card.attached_to_id:
        if card.attached_to_id == "role":
            print(f"  [Attached to: Role]")
        else:
            print(f"  [Attached to: {card.attached_to_id}]")
```

---

## 9. Implementation Priority

### Phase 1: Basic Attachments
1. Add fields to Card (`attached_to_id`, `attached_cards`, `facedown_original`)
2. Implement `is_facedown()`, `is_faceup()` helper methods
3. Implement `attach_to()` and `detach()` methods (cards stay in zones)
4. Update `all_cards_in_play()` to filter out facedown attached cards
5. Basic view rendering of attachments

### Phase 2: Face-Up/Down System
1. Implement `flip_card_facedown()` in GameEngine (creates placeholder, preserves original)
2. Implement `flip_card_faceup()` in GameEngine (restores original, destroys placeholder)
3. Test token clearing happens on original before flip
4. Test special properties can be set on placeholders
5. Update view to handle facedown placeholders

### Phase 3: Ranger Tokens
1. Add ranger_token_location to GameState
2. Implement token movement methods
3. Implement can_travel() check

### Phase 4: Special Rules
1. Role attachment rules (fatigue on all interactions)
2. Attached beings don't ready (Caustic Mulcher)
3. Cards leave play → discard attachments cascade

### Phase 5: Caustic Mulcher
1. Implement FIT+Conflict test
2. Implement Sun effect (attach beings or move token)
3. Implement Crest effect (harm attached beings, injure rangers)
4. Implement static abilities

---

## Open Questions

1. **How to handle "this card prevents readying"?**
   - Option A: Add a `prevents_attached_ready: bool` field
   - Option B: Add a card method `prevents_attached_ready() -> bool`
   - Option C: Create a new Keyword (e.g., `Keyword.PREVENTS_READY`)

2. **Role attachments in zones?**
   - Should role-attached cards exist in a zone, or be completely separate?
   - Probably separate from zones, tracked via attached_to_id == "role"

3. **Nested attachment depth limit?**
   - Rules say "no limit" but should we have a sanity check?
   - Probably just trust the game design

4. **Travel system integration?**
   - Need to implement travel before Caustic Mulcher is fully functional
   - Travel probably involves moving ranger token between zones/cards

---

## Testing Strategy

### Unit Tests Needed:
- Attach/detach operations
- Faceup/facedown flipping
- Token clearing on facedown
- Nested attachments
- all_cards_in_play() with attachments
- Discard cascade
- Role attachment fatigue
- Ranger token movement
- Travel blocking

### Integration Tests Needed:
- Caustic Mulcher full scenario
- Multiple nested attachments
- Role attachment during interaction
- Refresh phase with attached beings
