# Comprehensive Test Design - Mutation Testing Audit

## Overall Mutation Score: 40.8%
- **Total mutants**: 8,406
- **Killed**: 3,433 (40.8%)
- **Survived**: 3,340 (39.7%) — tests ran but didn't detect the mutation
- **No tests**: 1,633 (19.4%) — no test exercised this code at all

## Per-Module Breakdown

| Module | Total | Kill % | Survived | No Tests | Priority |
|--------|------:|-------:|---------:|---------:|----------|
| campaign_guide | 2,453 | 22.5% | 1,320 | 580 | LOW (see notes) |
| engine | 974 | 58.0% | 300 | 109 | HIGH |
| save_load | 899 | 53.4% | 395 | 24 | MEDIUM |
| view | 651 | 0.0% | 0 | 651 | SKIP (UI rendering) |
| json_loader | 602 | 69.6% | 167 | 16 | LOW |
| woods_cards | 547 | 57.2% | 206 | 28 | HIGH |
| models | 496 | 43.8% | 279 | 0 | HIGH |
| explorer_cards | 320 | 51.2% | 150 | 6 | MEDIUM |
| registry | 269 | 43.1% | 117 | 36 | HIGH |
| weather_cards | 255 | 32.2% | 47 | 126 | MEDIUM |
| mission_cards | 254 | 71.7% | 64 | 8 | LOW |
| valley_cards | 216 | 46.8% | 109 | 6 | MEDIUM |
| location_cards | 184 | 34.8% | 96 | 24 | MEDIUM |
| lone_tree_station | 91 | 69.2% | 28 | 0 | LOW |
| conciliator_cards | 84 | 64.3% | 30 | 0 | LOW |
| decks | 53 | 26.4% | 20 | 19 | MEDIUM |
| personality_cards | 41 | 80.5% | 8 | 0 | LOW |
| utils | 17 | 76.5% | 4 | 0 | LOW |

---

## Module-by-Module Analysis

### 1. campaign_guide.py — Priority: LOW

**Verdict: Largely acceptable as-is. The low kill rate is a structural artifact, not a testing failure.**

**Why the numbers look bad:**
- 46.9% of the file is `engine.add_message()` calls containing narrative text
- Much of the remaining "behavioral" code is continuation lines of multi-line strings, `return False` boilerplate, imports, and entry-routing calls
- Mutmut generates mutations on every string literal (case changes, `"XXXX"` substitutions, boundary edits), which massively inflates the mutant count
- 2,453 total mutants from a 929-line file = ~2.6 mutants per line, driven by string-heavy code

**What's actually well-tested:**
- The `resolve_entry()` routing function: 9/10 mutants killed — conditional dispatch and override system is solid
- Entry 47.x (Hy Pimpot): The branching logic (`if clear_type is None`, location checks, etc.) is covered by `test_hy_pimpot.py`
- Entry 80.x (Quisi): Conditional routing tested through `test_valley_cards.py`

**What's genuinely untested:**
- `resolve_entry_1` (campaign start/setup): 349 "no tests" mutants. Tests construct `GameEngine` directly and skip this. This is **acceptable** — it's a one-time setup function that's effectively an integration test of its own, and unit tests rightly avoid it.
- `resolve_entry_91_1`, `91_2`, `91_5`, `91_6` (Biscuit Delivery sub-entries): 162 "no tests" mutants. Some of these contain state mutations (gaining missions, recording events) that could be worth testing.
- `resolve_entry_85`, `86`, `94_1`, `1_04`: Placeholder/stub entries (9 mutants each, no tests). Acceptable.

**The `_discard_flora_from` function (5 survived):**
This is the one genuinely behavioral helper. The survived mutations are:
- `and` → `or` in the compound conditional (3 mutations) — tests only exercise the happy path where all conditions are true
- `"Flora"` → `"flora"` / `"FLORA"` (2 mutations) — `has_trait()` may be case-insensitive, or tests never have non-Flora facedown attachments

**Recommendations:**
- [x] Test `_discard_flora_from` with non-Flora facedown attachments (added to test_hy_pimpot.py)
- [x] Test 91.x sub-entries with state mutations - Kordo/Nal routing and effects (added to test_mission_cards.py)
- [ ] Do NOT try to test narrative text content — that's a losing battle with mutation testing
- [ ] Do NOT test `resolve_entry_1` in isolation — it's fine as an integration concern

---

### 2. engine.py — Priority: HIGH

**300 survived + 109 no-tests = 409 problem mutants out of 974 total (58% kill rate)**

#### Per-function breakdown

| Function | Survived | No Tests | Total | Notes |
|----------|:--------:|:--------:|:-----:|-------|
| `perform_test` | 62 | 0 | 62 | Core test resolution — most impactful |
| `execute_travel` | 0 | 62 | 62 | Completely untested |
| `phase3_travel` | 0 | 46 | 46 | Completely untested |
| `enforce_equip_limit` | 34 | 0 | 34 | Tested but weak assertions |
| `scout_cards` | 25 | 0 | 25 | Tested but weak assertions |
| `arrival_setup` | 25 | 0 | 25 | Tested but weak assertions |
| `phase4_refresh` | 24 | 0 | 24 | Tested but weak assertions |
| `interaction_fatigue` | 21 | 0 | 21 | Tested but weak assertions |
| `initiate_test` | 16 | 0 | 16 | String mutations + minor behavioral |
| `move_token` | 12 | 0 | 12 | Token type routing |
| `draw_path_card` | 10 | 0 | 10 | |
| `will_challenge_resolve` | 8 | 0 | 8 | |
| `move_ranger_token_to_card` | 8 | 0 | 8 | |
| `filter_by_obstacles` | 8 | 0 | 8 | |
| `__init__` | 8 | 0 | 8 | |
| `attach` | 7 | 0 | 7 | |
| `trigger_listeners` | 6 | 0 | 6 | |
| `check_and_process_clears` | 5 | 0 | 5 | |
| Other (7 functions) | 21 | 1 | 22 | Small counts |

#### What the existing tests cover well

test_engine.py has solid coverage of:
- The core test resolution pipeline (5-step sequence, effort calculation, success/failure)
- All 4 common test types (Traverse, Connect, Avoid, Remember)
- Challenge icon effects (Sun/Mountain/Crest) for specific cards
- Event listener system (registration, activation, filtering, player decisions)
- Keyword effects (Friendly, Obstacle, Persistent)
- Challenge effect retrigger prevention

#### What's surviving and why — categorized by theme

**Theme 1: Non-test action path in `perform_test` (~24 mutations) — RESOLVED**
The `if not action.is_test:` branch was completely untested. Added `NonTestActionTests` class
(4 tests) in test_engine.py that verifies: on_success called with effort=0, correct
ChallengeOutcome fields, target card passthrough, and no challenge deck interaction.

**Theme 2: ChallengeOutcome had dead fields (~8 mutations) — RESOLVED**
`difficulty` and `base_effort` were never read by any production or test code — they echoed
back values the caller already knew. Removed both fields from the dataclass. Kept `modifier`
and `symbol` (challenge deck draw results that may matter for future effects).
Remaining mutations on `modifier`/`symbol` are acceptable until downstream consumers exist.

**Theme 3: Challenge effect ordering and resolution (~12 mutations) — RESOLVED**
Added `ChallengeResolutionTests` class (5 tests) with a `_SunEffectCard` helper in test_engine.py:
- Retrigger guard: card moves from SURROUNDINGS→WITHIN_REACH during resolution, asserts handler
  fires exactly once (kills `and`→`or` on `already_resolved_ids` check)
- Order decider boundary: 2 cards in same area → decider called; 1 card → decider NOT called
  (kills `> 1` → `>= 1` and `> 2`)
- No-effects message: asserted present when no handlers exist, asserted absent when effects
  resolve (kills flag init/set/conditional mutations)

**Theme 4: Completely untested phase functions (108 no-tests)**
`execute_travel` (62) and `phase3_travel` (46) have zero test coverage. These are the travel
system — checking progress thresholds, travel blockers, clearing the play area, building the
new path deck, and running arrival setup.

**FIX:** These are complex multi-step flows. Worth testing at least:
- Travel eligibility check (progress threshold met vs. not met)
- Travel blocker constant abilities
- Play area cleanup during travel (non-Persistent cards discarded)
- Path deck reconstruction after travel

**Theme 5: `enforce_equip_limit` (34 survived)**
Tests exercise this function but don't verify the equip limit value (5), the gear filtering,
or the discard prompting. Mutations to `MAX_EQUIP = 5` → `6`, equip value fallback
`or 0` → `or 1`, and the `has_type(CardType.GEAR)` filter all survive.

**FIX:** Test with gear totaling exactly 5 (passes) vs. 6 (triggers discard prompt).

**Theme 6: `interaction_fatigue` (21 survived)**
This calculates fatigue from ready non-Friendly cards between the ranger and the target.
Mutations survive on: the card filtering logic, the area traversal, the display ID generation,
and error messages. The existing Friendly keyword test verifies the SKIP case but doesn't
verify the fatigue-APPLIED case deeply enough.

**FIX:** Test that interaction fatigue actually fatigues the correct number of cards, and that
exhausted cards between ranger and target don't cause fatigue.

**Theme 7: `phase4_refresh` (24 survived)**
The refresh phase (injury fatigue, draw card, refill energy, ready cards) is exercised
indirectly by integration tests but assertions don't catch mutations to the injury threshold
(`> 0` → `>= 0` or `> 1`), the fatigue amount, or the energy refill logic.

**FIX:** Test refresh with injured ranger (verify fatigue amount matches injury count) and
uninjured ranger (verify no fatigue).

**Theme 8: `scout_cards` (25 survived)**
Scout is exercised but assertions don't verify the boundary conditions (`count <= 0` → `< 0`,
`actual_count == 0` → `== 1`) or the correct top/bottom pile ordering.

**FIX:** Test scout with 0 count (no-op), test that cards placed on top vs. bottom actually
appear in the correct deck positions.

#### Recommendations (prioritized)

High value / easy fixes:
- [x] Trim dead fields from ChallengeOutcome (removed `difficulty`, `base_effort`)
- [x] Add non-test action (Rest) test through perform_test
- [ ] Test enforce_equip_limit boundary (5 vs 6 equip value)
- [ ] Test interaction_fatigue actually applying fatigue (not just Friendly skip)
- [ ] Test phase4_refresh with injured vs uninjured ranger

Medium value:
- [x] Test challenge effect ordering with multiple resolvable cards
- [ ] Test scout_cards boundary conditions and pile ordering
- [ ] Test move_token type routing (progress vs harm vs unique tokens)
- [ ] Test move_ranger_token_to_card with PREVENT_RANGER_TOKEN_MOVE blocker

Lower priority (complex setup, lower ROI):
- [ ] Test execute_travel (multi-step, needs full state setup)
- [ ] Test phase3_travel eligibility and blockers
- [ ] Test arrival_setup path deck construction
