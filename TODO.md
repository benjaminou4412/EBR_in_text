# Earthborne Rangers — Dev TODO

A living checklist distilled from our discussion. Grouped by area and roughly prioritized.


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

