# Earthborne Rangers — Dev TODO

A living checklist distilled from our discussion. Grouped by area and roughly prioritized.

## Types & Models
- [ ] Add typed default factories for lists/dicts in dataclasses (silence IDE warnings)
- [ ] Introduce enums:
  - [ ] Aspect: `AWA`, `FIT`, `SPI`, `FOC`
  - [ ] Approach: `Conflict`, `Exploration`, `Reason`, `Connection`
  - [ ] Area: `Weather`, `Location`, `Missions`, `AlongTheWay`, `WithinReach`, `PlayerArea`
- [ ] Add `DiscardPile` for ranger hand discards; consider converting `path_discard` later
- [ ] Add generic `tokens: Dict[str,int]` on `Entity` (charges, morsels, etc.)
- [ ] Add `CardDefinition` (immutable print data) for hand cards that become permanents
- [ ] Add `definition_to_entity(defn)` helper to create in‑play `Entity` from `CardDefinition`

## Engine
- [ ] Extend `CommitDecision` to support committing in‑play entities (exhaust/spend tokens)
- [ ] Update commit/discard flow:
  - [ ] Hand commits → push to `ranger_discard`
  - [ ] In‑play commits → exhaust entity and/or spend tokens
- [ ] Replace simple `symbol_handlers` with ordered challenge effects resolver:
  - [ ] Produce `ChallengeEffect` objects via registry for a drawn symbol
  - [ ] Group by `Area` and resolve order: Weather → Location → Missions → AlongTheWay → WithinReach → PlayerArea
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
  - [ ] Sitka Doe
  - [ ] Midday Sun
  - [ ] Overgrown Thicket (move from legacy handler to new system)
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
- [ ] End‑to‑end deterministic tests with fixed challenge drawer and effect selector

## Tooling & Docs
- [ ] Apply typed default factories across codebase
- [ ] Optionally migrate `energy` to `Dict[Aspect, int]` after enums
- [ ] Add short docstrings to core dataclasses and engine methods
- [ ] Optionally tune Pylance diagnostics once typed factories are in place

## Suggested Sequence (incremental)
1) Typed factories + enums (Aspect/Approach/Area)
2) DiscardPile + push committed cards there
3) Behavior registry skeleton; migrate Overgrown Thicket
4) Challenge effects resolver + view ordering; migrate a couple effects
5) “Play” actions path (CardDefinition → Entity) for one simple permanent
6) Path/Challenge deck improvements and Travel Phase basics
7) Flesh out behaviors and tests card‑by‑card

