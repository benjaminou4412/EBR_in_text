# Earthborne Rangers — Dev TODO

A living checklist distilled from our discussion. Grouped by area and roughly prioritized.

## Current priorities
- Implement exhaust abilities and Peerless Pathfinder
- Implement Caustic Mulcher
  - Attachment system
  - faceup/facedown cards
  - ranger tokens + prevent ranger token from moving
  - prevent attached beings from readying
- Implement at least two other Valley NPCs
- Implement Refresh abilites
- Implement Locations and Travel
- Implement weather-flipping
- Implement at least one Gear + one non-response Moment + 1 attachment, and the Play action
- Implement actual challenge cards rather than the current RNG setup
- Implement missions, campaign log entries, clear entries, etc.
- Implement Day system and save/load/autosave
- Implement ordering selection:
  -scouting/remember
  -challenge effects in the same zone
  -response abilities at the same timing point
- Implement Challenge effects noting whether or not they have "resolved" for the purposes of other game effects
- Implement...the entire rest of the game.


## Engine 
- [ ] Extend `CommitDecision` to support committing in‑play entities (exhaust/spend tokens)
- [ ] Update commit/discard flow:
  - [ ] In‑play commits → exhaust entity and/or spend tokens
- [ ] Replace simple `symbol_handlers` with ordered challenge effects resolver:
  - [ ] Produce `ChallengeEffect` objects via registry for a drawn symbol
  - [ ] Within an area, let active player pick resolution order (view callback)
  - [ ] Prevent re‑trigger when a card moves into an already‑resolved area during the same test

## Actions & Behaviors
- [ ] Add non‑test "Play" actions for hand cards that become permanents (Feature/Being/Gear/Role/Attribute)
  - [ ] Enforce aspect requirements and energy costs
  - [ ] On success: spend, remove from hand, create entity, place by `enters_play`, add `enters_play_with` tokens
- [ ] Hand‑code more card behaviors (tests + symbol effects) for current demo set:
  - [ ] Midday Sun
- [ ] Extend common‑test rules as needed (e.g., Disconnected, Dodge later)
- [ ] Implement keyword system (enum-based with well-documented behavior):
  - [ ] Implement Ambush keyword (fatigue on enter/move to Within Reach)
  - [ ] Implement remaining keywords as needed
  - [ ] Add "Friendly can't be targeted by Weapons" rule
  - [ ] Add "Obstacle blocks Travel" rule

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

## View / CLI
- [ ] Add ordering UI for challenge effects within an area
- [ ] Expand commit UI to include in‑play sources and indicate exhaust/token costs

## Architecture Improvements
- [ ] Parse keywords from JSON card data (currently hardcoded)
  - [ ] Scan static-kind rules elements for keyword strings
  - [ ] Extract keywords automatically during card loading
- [ ] Refactor targeting system to use Card objects instead of target_id strings
  - [ ] Update card_chooser injection pattern
  - [ ] Clean up old target_id passing architecture
- [ ] Add autosave system for graceful error degradation (post-MVP)
- [ ] Consider adding has_keyword() method wrapper if keyword behaviors become more complex

## Testing
- [ ] In‑play commits exhaust/spend tokens
- [ ] Challenge effect ordering and once‑per‑area semantics
- [ ] Card‑specific behaviors (Bramble/Doe/Thicket/Weather)
- [ ] End‑to‑end deterministic tests with fixed challenge drawer and effect selector

