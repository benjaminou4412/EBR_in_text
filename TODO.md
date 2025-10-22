# Earthborne Rangers — Dev TODO

A living checklist distilled from our discussion. Grouped by area and roughly prioritized.

## Current Focus: Walk With Me Implementation (Event Listener System)

**Goal:** Implement Walk With Me card, which requires building an event/timing trigger system for "Response:" cards.

**Implementation Steps:**
- [ ] 1. Create EventListener dataclass (models.py)
  - Fields: event_type, timing, filter_fn, effect_fn, source_card_id
- [ ] 2. Add event_listeners registry to GameState (models.py)
  - list[EventListener] field
  - Method to register/unregister listeners
- [ ] 3. Add response_decider to GameEngine (engine.py)
  - Callable[[GameState, Card, dict], bool] for "play this Response?" decisions
  - Default implementation: auto-play if can afford
  - Runtime gets interactive version from view.py
- [ ] 4. Create trigger_listeners method in GameEngine (engine.py)
  - Signature: trigger_listeners(event_type: str, timing: str, context: dict)
  - Scans registry, filters by event_type and timing
  - Calls filter_fn to check if listener should fire
  - If yes, calls effect_fn with engine and context
- [ ] 5. Implement Walk With Me card class (explorer_cards.py)
  - Override enters_hand() or on_zone_change() to register listener
  - Listener filters for: event="TEST_SUCCEED", timing="after", verb="Traverse"
  - Effect: prompt to play, pay cost, choose being, add progress, discard self
- [ ] 6. Call trigger_listeners in perform_action (engine.py)
  - After test success: trigger_listeners("TEST_SUCCEED", "after", context={...})
  - Context includes: action, verb, effort, target_id, success
- [ ] 7. Implement interactive response_decider (view.py)
  - choose_play_response(state, card, context) -> bool
  - Show card details, prompt "Play this card? (y/n)"
- [ ] 8. Wire up response_decider in main.py
  - Pass choose_play_response to GameEngine constructor
- [ ] 9. Write tests for Walk With Me
  - Test listener registration when card enters hand
  - Test trigger fires after successful Traverse
  - Test doesn't trigger after failed Traverse or non-Traverse tests
  - Test energy cost is paid, progress is added, card is discarded
  - All tests should be silent (use default response_decider)


## Engine 
- [ ] Extend `CommitDecision` to support committing in‑play entities (exhaust/spend tokens)
- [ ] Update commit/discard flow:
  - [ ] Hand commits → push to `ranger_discard`
  - [ ] In‑play commits → exhaust entity and/or spend tokens
- [ ] Replace simple `symbol_handlers` with ordered challenge effects resolver:
  - [ ] Produce `ChallengeEffect` objects via registry for a drawn symbol
  - [ ] Within an area, let active player pick resolution order (view callback)
  - [ ] Prevent re‑trigger when a card moves into an already‑resolved area during the same test
- [ ] Expose deterministic hooks for tests (injectable chooser for effect ordering)

## Actions & Behaviors
- [ ] Introduce behavior registry `card_id -> provider`:
  - [ ] `build_actions(state, entity) -> List[Action]`
  - [ ] `build_symbol_effects(state, entity, symbol) -> List[ChallengeEffect]`
- [ ] Update `provide_card_tests` to consult behavior registry, fallback to current hardcoded actions
- [ ] Add non‑test “Play” actions for hand cards that become permanents (Feature/Being/Gear/Role/Attribute)
  - [ ] Enforce aspect requirements and energy costs
  - [ ] On success: spend, remove from hand, create entity, place by `enters_play`, add `enters_play_with` tokens
- [ ] Hand‑code more card behaviors (tests + symbol effects) for current demo set:
  - [ ] Sunberry Bramble
  - [ ] Midday Sun
- [ ] Extend common‑test rules as needed (e.g., Disconnected, Obstacle/Dodge later)

## Decks & Setup
- [ ] Path deck: shuffle and reshuffle policy; configurable draw count per round
- [ ] Challenge deck: real deck model (per‑aspect modifiers, discard, [RESHUFFLE])
- [ ] Weather arrival/setup: execute “Arrival Setup” printed instructions; Phase 4 refresh hooks

## Round Flow
- [ ] Phase 3 Travel:
  - [ ] Add simple location/trail graph (use `valley_map.json`)
  - [ ] Derive travel options; on travel, rebuild path deck by terrain and resolve on‑travel rules
- [ ] Phase 4 Refresh:
  - [ ] Implement printed refresh effects (e.g., weather add/flip)
  - [ ] Add energy recovery rules if applicable

## View / CLI
- [ ] Add ordering UI for challenge effects within an area
- [ ] Expand commit UI to include in‑play sources and indicate exhaust/token costs
- [ ] Improve non‑interactive/test mode with default choices for automation

## Testing
- [ ] Non‑test actions (Rest/Play) behavior
- [ ] Insufficient energy raises `RuntimeError`
- [ ] Discard pile transitions on commit
- [ ] In‑play commits exhaust/spend tokens
- [ ] Challenge effect ordering and once‑per‑area semantics
- [ ] Card‑specific behaviors (Bramble/Doe/Thicket/Weather)
- [ ] End‑to‑end deterministic tests with fixed challenge drawer and effect selecto

## Tooling & Docs
- [ ] Add short docstrings to core dataclasses and engine methods

