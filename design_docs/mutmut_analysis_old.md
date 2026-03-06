## Per-Module Breakdown

| Module | Total | Kill % | Survived | No Tests | Priority |
|--------|------:|-------:|---------:|---------:|----------|
| woods_cards | 547 | 57.2% | 206 | 28 | HIGH |
| explorer_cards | 320 | 51.2% | 150 | 6 | MEDIUM |
| weather_cards | 255 | 32.2% | 47 | 126 | MEDIUM |
| mission_cards | 254 | 71.7% | 64 | 8 | LOW |
| valley_cards | 216 | 46.8% | 109 | 6 | MEDIUM |
| location_cards | 184 | 34.8% | 96 | 24 | MEDIUM |
| lone_tree_station | 91 | 69.2% | 28 | 0 | LOW |
| conciliator_cards | 84 | 64.3% | 30 | 0 | LOW |
| personality_cards | 41 | 80.5% | 8 | 0 | LOW |

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

**Theme 4: Completely untested phase functions (108 no-tests) — RESOLVED**
Added `Phase3TravelTests` (7 tests) and `ExecuteTravelTests` (9 tests) in test_engine.py.
Uses real LoneTreeStation/OvergrownThicket cards and prompt-aware response_decider callbacks.
- phase3_travel: insufficient/sufficient progress, accept/decline, active/exhausted Obstacle
  blocker, ranger-token-based travel (token on location vs elsewhere)
- execute_travel: non-persistent path cards discarded, Persistent cards survive, ranger cards
  in path areas discarded (but PLAYER_AREA preserved), path deck/discard cleared and rebuilt,
  location changes to destination, camping raises DayEndException, not camping returns False

**Theme 5: `enforce_equip_limit` (34 survived) — RESOLVED**
Added `EnforceEquipLimitTests` (4 tests): at-limit (5, no discard), over-limit (6, triggers
discard), non-gear cards not counted, and multiple discards until within limit.

**Theme 6: `interaction_fatigue` (21 survived) — RESOLVED**
Added `InteractionFatigueTests` (6 tests): ready card fatigues by presence value, exhausted
card skipped, Friendly card skipped, target in SURROUNDINGS includes both inner areas, target
in WITHIN_REACH excludes same-area cards, and no-cards-between message check.
NOTE: rules mention "Within Reach (another Ranger)" should include WR cards as between — this
is a multiplayer concern not yet implemented. Existing single-player behavior is correct.

**Theme 7: `phase4_refresh` (24 survived) — RESOLVED**
Added `Phase4RefreshTests` (4 tests): injured ranger fatigues by injury count, uninjured ranger
no fatigue, energy refilled to base aspects, and exhausted cards readied.

**Theme 8: `scout_cards` (25 survived) — RESOLVED**
Added `ScoutCardsTests` (4 tests): scout 0 is no-op, scout empty deck is no-op with message,
cards placed on top appear at deck front, cards placed on bottom appear at deck end.

#### Recommendations (prioritized)

High value / easy fixes:
- [x] Trim dead fields from ChallengeOutcome (removed `difficulty`, `base_effort`)
- [x] Add non-test action (Rest) test through perform_test
- [x] Test enforce_equip_limit boundary (5 vs 6 equip value)
- [x] Test interaction_fatigue actually applying fatigue (not just Friendly skip)
- [x] Test phase4_refresh with injured vs uninjured ranger

Medium value:
- [x] Test challenge effect ordering with multiple resolvable cards
- [x] Test scout_cards boundary conditions and pile ordering
- [ ] Test move_token type routing (progress vs harm vs unique tokens)
- [ ] Test move_ranger_token_to_card with PREVENT_RANGER_TOKEN_MOVE blocker

Lower priority (complex setup, lower ROI):
- [x] Test execute_travel (multi-step, needs full state setup)
- [x] Test phase3_travel eligibility and blockers
- [ ] Test arrival_setup path deck construction

---

### save_load.py

**Total mutants**: 915 | **Killed**: 496 (54.2%) | **Survived**: 395 (43.2%) | **No tests**: 24 (2.6%)

The existing tests are all round-trip (save→load→spot-check a few fields). This catches gross
breakage but misses most field-level mutations because assertions are shallow and many code
paths (facedown cards, modifiers, generic JSON cards, mission bubbles) have zero coverage.

Per-function breakdown:

| Function | Survived | No tests | Notes |
|----------|----------|----------|-------|
| `load_game` | 178 | 0 | Mega-function; many `.get()` defaults, facedown branch, weather/mission ID lookup |
| `instantiate_card` | 36 | 0 | Generic Card from JSON, facedown guard, `fresh` param inspection |
| `_apply_mutable_state` | 33 | 0 | `.get()` default values (`False`, `0`, `{}`) never tested with missing keys |
| `serialize_card` | 27 | 0 | Facedown detection, JSON source info, backside class |
| `deserialize_mission` | 27 | 0 | Bubble fields (`left_bubble`, etc.) never checked after load |
| `_validate_save_structure` | 25 | 0 | Tests always provide well-formed saves |
| `_build_card_class_registry` | 24 | 0 | Auto-discovery loop filter conditions never tested |
| `serialize_game_state` | 23 | 0 | Individual field mappings (weather_id, mission_ids, etc.) |
| `serialize_modifier` | 0 | 16 | Completely untested — no test card has modifiers |
| `save_game` | 9 | 0 | File I/O (encoding, mkdir) |
| `serialize_mission` | 6 | 0 | Bubble field serialization |
| Other | 7 | 8 | `get_card_class`, `deserialize_challenge_card`, etc. |

#### What's surviving and why — categorized by theme

**Theme 1: Facedown card round-trip completely untested (~30+ mutations) — RESOLVED**
Added `FacedownCardTests` (5 tests): serialize facedown fields, serialize non-facedown fields,
round-trip in area, frontside link preservation, mutable state preservation. **Also found and
fixed a bug:** `process_facedown_cards` silently dropped facedown cards whose frontside wasn't
separately in an area (which is the normal case after a card is flipped facedown). Fixed by
instantiating the frontside from its class name (stored in the `backside_class` field) when it's
not already in the card registry.

**Theme 2: Modifier serialization has zero coverage (16 no-tests + ~15 survived) — RESOLVED**
Added `ModifierSerializationTests` (4 tests): serialize_modifier field check, deserialize_modifier
field check, card-level round-trip (serialize_card → instantiate_card with modifiers list), and
full save/load round-trip with a card bearing a ValueModifier in an area. All four modifier
fields (`target`, `amount`, `source_id`, `minimum_result`) are now verified at every level.

**Theme 3: Mission bubble fields never verified (~27 survived in `deserialize_mission`) — RESOLVED**
Added `MissionBubbleTests` (2 tests): direct `serialize_mission` field check, and full round-trip
with both active and cleared missions having distinct bubble patterns. All three bubble fields
now verified on both serialization and deserialization paths.

**Theme 4: `load_game` fallback/default paths untested (~50+ survived) — RESOLVED**
Replaced all Category B silent fallback defaults with direct key access (`[]`) so `load_game`
fails loudly on missing data instead of silently fabricating defaults. Changes:
- All campaign tracker fields: `.get('key', default)` → `['key']`
- `weather_id`, `mission_ids`: now required (weather is always present in saveable state)
- `ranger.injury`: now required
- `deserialize_mission` bubble fields: now required
- Version mismatch: raises `ValueError` instead of silent `pass`
- `day_registry`: now required (removed `_default_day_registry()` fallback)
- Removed unused `_generate_campaign_id` import

Added `LoadGameFailLoudTests` (6 tests) verifying `ValueError` on missing
`weather_id`, `mission_ids`, `campaign_id`, `injury`, `current_location_id`, and version
mismatch. Updated existing `test_day_registry_backwards_compatibility` → `test_missing_day_registry_raises`.
(Originally expected `KeyError`; updated to `ValueError` after Theme 6 validator fix.)

**Theme 5: Generic Card from JSON not tested (~15 survived in `instantiate_card`) — RESOLVED**
Removed dead code: the generic Card branch in both `serialize_card` and `instantiate_card` was
only reachable from save_load.py itself (all production cards have dedicated subclasses).
`serialize_card` now raises `ValueError` on bare `Card` instances, the `json_source_title`/
`json_source_set` fields were removed from `CardData`, and the `instantiate_card` JSON loader
branch was deleted. Added `BareCardSerializationTests` (1 test) verifying the fail-loud
behavior. Also fixed `test_ranger_deck_and_hand_preserved` which was using bare `Card`
instances — switched to real explorer card subclasses.

**Theme 6: `_validate_save_structure` not directly tested (~25 survived) — RESOLVED**
Added `ValidateSaveStructureTests` (12 tests) that systematically corrupt save dicts and verify
descriptive `ValueError` messages. **Also found and fixed 14 missing keys** in the validator:
`weather_id` and `mission_ids` at top level, `injury` in ranger, and 11 campaign_tracker keys
(`campaign_id`, `campaign_name`, `notable_events`, `unlocked_rewards`, `active_missions`,
`cleared_missions`, `ranger_deck_card_ids`, `ranger_name`, `ranger_aspects`,
`current_location_id`, `current_terrain_type`, `day_registry`). All were accessed with `[]`
in `load_game` but not checked by the validator — corrupted saves would produce raw `KeyError`
instead of descriptive `ValueError`. Updated `LoadGameFailLoudTests` and
`test_missing_day_registry_raises` from `KeyError` to `ValueError` to match.

**Theme 7: `_build_card_class_registry` filter conditions (~24 survived) — RESOLVED**
Added `CardClassRegistryContentsTests` (4 tests): every card class exported from `ebr.cards`
is present (via `subTest` over all 30 card classes), base `Card` and `FacedownCard` are
accessible by name, and non-Card names are rejected. This exercises all four filter conditions
in the auto-discovery loop.

#### Recommendations (prioritized)

High value / easy fixes:
- [x] Round-trip test with FacedownCard attachment (+ bugfix in `process_facedown_cards`)
- [x] Round-trip test with card that has ValueModifiers
- [x] Round-trip test with mission bubble states (left/middle/right)
- [x] Removed dead generic Card branch; serialize_card now rejects bare Cards
- [x] Fail-loud on missing keys + tests (replaced backwards-compat defaults)

Medium value:
- [x] Direct `_validate_save_structure` tests with malformed saves (+ fixed 14 missing keys)
- [x] Verify weather and mission IDs resolve correctly after load

Lower priority:
- [x] Direct `_build_card_class_registry` contents test
- [ ] `serialize_card` field-level assertions (separate from round-trip)


### json_loader.py — Priority: LOW

**Total mutants**: 602 | **Killed**: 419 (69.6%) | **Survived**: 167 (27.7%) | **No tests**: 16 (2.7%)

No direct test file exists (no test_json_loader.py). All kills come indirectly through card
instantiation — creating `SitkaDoe()`, `APerfectDay()`, etc. reads JSON and populates fields.
Survived mutations are ones where no test asserts on the specific parsed field.

Per-function breakdown:

| Function | Survived | No tests | Notes |
|----------|:--------:|:--------:|-------|
| `parse_card_types` | 62 | 0 | Huge elif chain mapping strings → CardType enums + two large set literals |
| `load_card_fields` | 20 | 0 | Return dict: swapping which local maps to which key survives |
| `generate_card_id` | 0 | 16 | Dead code — defined but never called anywhere |
| `load_card_json_by_title` | 14 | 0 | File I/O, isinstance branch, card search loop |
| `parse_threshold_value` | 13 | 0 | 5 branches (None/-1/-2/int/str/"Ranger Token"/digits) |
| `parse_card_abilities` | 12 | 0 | "rules" array parsing, "challenge" kind formatting |
| `parse_starting_tokens` | 8 | 0 | Token type/amount from "enters_play_with" |
| `parse_clear_logs` | 8 | 0 | Regex-based "[Campaign Log Entry] N" extraction |
| `parse_area` | 8 | 0 | CardType → Area mapping with string cleaning |
| `parse_approach_icons` | 5 | 0 | Approach dict accumulation |
| `parse_mission_objective_log` | 4 | 0 | Regex-based log entry from mission objective text |
| `parse_aspect_requirement` | 4 | 0 | Aspect enum + min_value extraction |
| `get_project_root` | 4 | 0 | Path traversal up to README.md |
| `parse_energy_cost` | 3 | 0 | Energy cost amount extraction |
| `parse_traits` | 2 | 0 | Simple `.get("traits", [])` |

#### What's surviving and why — categorized by theme

**Theme 1: `parse_card_types` string matching (~62 survived)**
Two large string sets (`ranger_sets` with 9 entries, `path_sets` with 19 entries) plus a 10-branch
`if/elif` chain mapping card_type strings to `CardType` enums. Mutmut generates mutations on
every string literal ("explorer"→"XXXX"), every `==` comparison, every `.add()` call, and the
normalization chain (`.lower().replace()`). This is structurally identical to campaign_guide.py's
string-heavy inflation.

Most of these are **equivalent mutations** — changing one string in a 19-entry set doesn't break
anything because the other 18 still work for the production cards that use those sets. The elif
chain mutations survive because tests only exercise the card types used by test cards (Being,
Moment, Gear, Weather, Location, Mission) — not every branch.

**Theme 2: `load_card_fields` return dict (~20 survived)**
The return dict on lines 78-106 maps 22 local variables to dict keys. Mutations swap which
variable maps to which key (e.g., `"harm_threshold": harm_value` → `"harm_threshold":
progress_value`). These survive because existing tests don't assert every parsed field on
cards — they test behavior, not data fidelity.

**FIX:** Test a few representative cards and assert on their parsed fields: card_types, traits,
thresholds, presence, approach_icons, aspect, energy_cost, starting_area, abilities_text, etc.
This catches the field-swap mutations in `load_card_fields` AND validates the individual parsers.

**Theme 3: `load_card_json_by_title` file loading (~14 survived)**
Mutations on encoding parameter, `isinstance(data, list)` branch, `.get("cards", [])` fallback,
and the title-matching loop. Tests only exercise the happy path (card found). No test for
unknown set, missing file, or dict-format JSON files.

**Theme 4: `parse_threshold_value` edge cases (~13 survived)**
Five distinct return branches: `None`/`-1` → missing, `-2` → nulled, `int` → direct value,
`"Ranger Token"` → ranger-token threshold, string like `"2R"` → digit extraction. Tests only
exercise the int and None paths through production cards.

**Theme 5: `parse_card_abilities` rules formatting (~12 survived)**
Iterates "rules" array, formats challenge abilities with `symbol + ": " + text`. Mutations on
the "challenge" kind check, the "NO_SYMBOL_FOUND" default, and the text concatenation survive
because no test asserts on `abilities_text` content.

**Theme 6: Smaller parsers (parse_starting_tokens, parse_area, parse_clear_logs, parse_approach_icons, parse_aspect_requirement, parse_mission_objective_log) — ~37 survived total**
Each has a few surviving mutations on edge cases, string comparisons, or default values. Most
are caught indirectly but not exhaustively.

**Theme 7: `generate_card_id` — dead code (16 no-tests)**
Defined on line 286 but never called anywhere in the codebase. Can be deleted.

#### Recommendations (prioritized)

High value / easy fixes:
- [x] Delete dead `generate_card_id` function — DONE (deleted)
- [x] Field-level assertions on representative cards (kills Theme 2 + validates parsers) — DONE (12 tests in `FieldLevelAssertionTests`)
- [x] Test `parse_threshold_value` edge cases: -1, -2, "Ranger Token", "2R" — DONE (9 tests in `ParseThresholdValueTests`)
- [x] Test `parse_area` with different card types (Gear→PLAYER_AREA, Being→enters_play, Weather→SURROUNDINGS) — DONE (14 tests in `ParseAreaFailLoudTests`)

Medium value:
- [x] Test `parse_card_types` for each CardType enum member (verifies the elif chain) — DONE (8 tests + 10 subtests in `ParseCardTypesTests`)
- [x] Test `parse_card_abilities` challenge formatting vs regular text — DONE (5 tests in `ParseCardAbilitiesTests`)
- [x] Test `parse_clear_logs` and `parse_mission_objective_log` regex patterns — DONE (7 tests total)
- [x] Test `load_card_json_by_title` error paths (unknown set, missing card) — DONE (2 tests in `LoadCardJsonErrorTests`)

Lower priority (string-set inflation):
- [ ] `parse_card_types` string set membership — mostly equivalent mutations, low ROI
- [ ] `get_project_root` path traversal — works or the whole project breaks

#### Code changes made

Fail-loud improvements applied to `json_loader.py`:
- Deleted dead `generate_card_id` function (16 no-test mutations eliminated)
- `parse_card_types`: added `role` branch + raises `ValueError` on unknown card_type
- `parse_approach_icons`: removed try/except, now raises directly on unknown `Approach`
- `parse_aspect_requirement`: removed try/except, now raises directly on unknown `Aspect`
- `parse_area`: added `surroundings` branch, added `ROLE` to PLAYER_AREA routing, raises on unknown enters_play
- `parse_starting_tokens`: raises if `enters_play_with` block has no `type`
- `parse_card_abilities`: raises on challenge rule missing `challenge_symbol` (was "NO_SYMBOL_FOUND" sentinel)
- `parse_energy_cost`: removed dead try/except around `return amount` (returning an int can't raise ValueError)

All 532 existing tests + 69 new tests pass (40 subtests). No bugs found in production JSON data.


## Module-by-Module Analysis

### models.py — 496 total, 43.8% killed, 279 survived, 0 no-tests

#### Per-function survived mutation breakdown

| Function | Survived | Notes |
|----------|------:|-------|
| `_build_challenge_deck` | 176 | 24-card data table: icons, mods, reshuffle flags |
| `_default_day_registry` | 101 | 30-day data table: weather names, campaign log entries |
| `draw_challenge_card` | 1 | Message string mutation |
| `_generate_campaign_id` | 1 | `hex[:8]` slice boundary |

#### Theme Analysis

**Theme 1: Challenge deck data integrity (176 survived)**
`_build_challenge_deck` is a 24-row lookup table. Each ChallengeCard has an icon (sun/mountain/crest), 4 aspect modifiers (AWA/FIT/SPI/FOC), and a reshuffle flag. Mutations survive because no test verifies the actual card data — only that the deck exists and can be drawn from. Mutmut is swapping modifier values (0→1, -1→0), flipping reshuffle bools, and changing icons, all undetected.

Key properties to verify:
- Exactly 24 cards
- Icon distribution: 8 sun, 8 mountain, 8 crest
- Each card's 4 mods sum to 0 (zero-sum property — need to verify this holds)
- Exactly 4 reshuffle cards (cards 0, 4, 11, 13)
- Specific mod values on specific cards (spot-check a few)

**Theme 2: Day registry data integrity (101 survived)**
`_default_day_registry` is a 30-day lookup mapping day numbers to `DayContent(weather_name, entries_list)`. Mutations survive because no test checks the actual weather assignments or campaign log entries per day. Mutmut is swapping weather names between days, changing day numbers, and mutating the entry lists.

Key properties to verify:
- Exactly 30 days (1–30)
- Weather distribution matches game rules
- Days with campaign log entries (day 3 has "94.1", day 4 has "1.04")
- Specific day→weather mappings (spot-check representative days)

**Theme 3: draw_challenge_card message (1 survived)**
A message string mutation in `draw_challenge_card`. Low value — message text is cosmetic.

**Theme 4: _generate_campaign_id slice (1 survived)**
`uuid.uuid4().hex[:8]` — mutmut changes the slice to `[:9]` or similar. Low value — the ID just needs to be unique and short.

#### Recommendations (prioritized)

High value:
- [x] Challenge deck structural assertions — DONE (10 tests + 168 subtests in `ChallengeDeckStructureTests`)
- [x] Challenge deck spot-check — DONE (8 tests in `ChallengeDeckSpotCheckTests`, covers all 4 reshuffle + 4 non-reshuffle)
- [x] Day registry structural assertions — DONE (7 tests + 70 subtests in `DayRegistryStructureTests`)
- [x] Day registry spot-check — DONE (8 tests in `DayRegistrySpotCheckTests`)

Lower priority:
- [ ] `draw_challenge_card` message string — cosmetic, low ROI
- [ ] `_generate_campaign_id` slice boundary — functional, low ROI

All 564 tests pass (278 subtests). No bugs found in data tables.



### registry.py — 269 total, 43.1% killed, 117 survived, 36 no-tests

#### Per-function survived mutation breakdown

| Function | Survived | No Tests | Notes |
|----------|------:|------:|-------|
| `provide_common_tests` | 102 | 0 | 4 common tests: Traverse, Connect, Avoid, Remember — Action wiring + callbacks |
| `get_search_test` | 0 | 29 | Helper for "scout path + draw 1" test pattern — completely untested |
| `filter_tests_by_targets` | 9 | 0 | Filters tests by valid targets — edge cases not verified |
| `_search_test_success` | 0 | 7 | Search test success callback — completely untested |
| `provide_play_options` | 6 | 0 | Collects play actions from hand — field-level mutations survive |

#### Theme Analysis

**Theme 1: Common test Action wiring (102 survived)**
`provide_common_tests` builds 4 Action objects (Traverse, Connect, Avoid, Remember), each with specific field values (id, name, aspect, approach, verb, source_id/title), a difficulty function, success/fail callbacks, and a target provider. Tests exercise these through the engine's test-resolution flow, but don't directly verify the Action field values or that the correct callback is wired to the correct test. Mutmut is swapping aspects between tests, changing verbs, flipping difficulty calculations, and mutating callback wiring — all undetected.

Key properties to verify per common test:
- Action fields: id, aspect, approach, verb
- Target provider returns correct card types
- Difficulty function uses presence with min-1 floor
- Success effect (add_progress / exhaust / scout+draw)
- Fail effect (injure for Traverse, default no-op for others)

**Theme 2: Search test helper — untested (36 no-tests)**
`get_search_test` and `_search_test_success` form a reusable pattern for cards that offer a "scout path cards equal to effort, then draw 1 path card" test. No test exercises this code at all. Used by several cards (e.g. Overgrown Thicket, Sunberry Bramble based on naming pattern).

Key properties to verify:
- Action fields: id built from source_card.id, aspect=AWA, approach=CONNECTION
- Success effect: scouts path deck by effort, then draws 1 path card

**Theme 3: filter_tests_by_targets edge cases (9 survived)**
Filters a list of Actions to only include tests that can be initiated. Mutations in the filtering logic survive because tests don't cover:
- Non-test Actions (is_test=False) always pass through
- Tests with target_provider=None always included
- Tests with empty target list excluded

**Theme 4: provide_play_options (6 survived)**
Iterates hand cards, checks `can_be_played`, collects play Actions. Mutations survive in the filtering/appending logic. Likely low-value field swaps.

#### Recommendations (prioritized)

High value:
- [x] Common test Action field assertions — DONE (5 tests in `CommonTestActionFieldTests`)
- [x] Common test target providers — DONE (4 tests in `CommonTestTargetProviderTests`)
- [x] Common test difficulty functions — DONE (7 tests + 3 subtests in `CommonTestDifficultyTests`)
- [x] Common test success effects — DONE (5 tests in `CommonTestSuccessEffectTests`)
- [x] Common test fail effects — DONE (3 tests in `CommonTestFailEffectTests`)

Medium value:
- [x] Search test helper — DONE (10 field tests + 1 success effect test in `SearchTest*Tests`)
- [x] filter_tests_by_targets — DONE (5 tests in `FilterTestsByTargetsTests`, all 3 branches + mixed)

Lower priority:
- [ ] provide_play_options field-level mutations — largely cosmetic

All 604 tests pass (281 subtests). No bugs found.

### decks.py — 53 total, 26.4% killed, 20 survived, 19 no-tests

#### Per-function survived mutation breakdown

| Function | Survived | No Tests | Notes |
|----------|------:|------:|-------|
| `get_available_travel_destinations` | 0 | 11 | Completely untested — returns travel destinations from location graph |
| `get_current_missions` | 10 | 0 | Mission registry lookup — tests don't verify returned cards |
| `get_pivotal_cards` | 0 | 8 | Completely untested — returns pivotal set for a location |
| `get_current_weather` | 7 | 0 | Weather registry lookup — tests don't verify returned card types |
| `get_location_by_id` | 3 | 0 | Location registry lookup — default-fallback logic not fully tested |

#### Theme Analysis

**Theme 1: Travel destination graph — untested (11 no-tests)**
`get_available_travel_destinations` implements a triangle graph of 3 locations (Lone Tree Station ↔ Boulder Field ↔ Ancestor's Grove). Returns all locations except the current one. No test exercises this at all.

Key properties to verify:
- Each location returns exactly 2 destinations
- Returned destinations are correct Card subclass instances
- Current location is excluded from results

**Theme 2: Pivotal set lookup — untested (8 no-tests)**
`get_pivotal_cards` returns pivotal-set cards for a given location. Currently only implements Lone Tree Station (returns HyPimpotChef). Raises for unknown locations.

Key properties to verify:
- Lone Tree Station returns [HyPimpotChef]
- Unknown location raises RuntimeError

**Theme 3: Weather/mission/location registry lookups (20 survived)**
`get_current_weather`, `get_current_missions`, and `get_location_by_id` are registry lookups mapping string names to Card subclass constructors. Tests exercise them but don't verify the returned card types or titles.

Key properties to verify:
- Each weather name maps to the correct Weather card subclass
- Unknown weather raises RuntimeError
- Each mission name maps to the correct Mission card
- Unknown mission raises RuntimeError
- Each location ID maps to the correct Location card
- Unknown location defaults to Lone Tree Station (not a raise)

#### Recommendations (prioritized)

High value:
- [x] Travel destinations — DONE (8 tests + 3 subtests in `TravelDestinationTests`)
- [x] Pivotal cards — DONE (2 tests in `PivotalCardsTests`)
- [x] Weather registry — DONE (4 tests in `WeatherRegistryTests`)
- [x] Mission registry — DONE (3 tests in `MissionRegistryTests`)
- [x] Location registry — DONE (4 tests in `LocationRegistryTests`)

Code change: `get_location_by_id` now raises `ValueError` on unknown IDs instead of silently defaulting to Lone Tree Station.

Lower priority (already tested indirectly):
- [ ] `build_woods_path_deck` / `select_three_random_valley_cards` — deck builders, already killed by existing tests

All 631 tests pass (286 subtests). No bugs found in registry data.

---

### utils.py — 17 total, 76.5% killed, 4 survived, 0 no-tests

#### Per-function survived mutation breakdown

| Function | Survived | Notes |
|----------|------:|-------|
| `get_display_id` | 4 | Duplicate-title disambiguation (A/B/C suffix logic) |

#### Theme Analysis

**Theme 1: Display ID disambiguation (4 survived)**
`get_display_id` returns just the title when unique, or appends " A"/" B"/" C" when multiple cards share a title. The 4 surviving mutations are in the disambiguation branch: sorting by id, indexing, chr(65 + index), and the f-string formatting. Tests exercise the unique-title path but don't test the multi-card disambiguation.

Key properties to verify:
- Single card → just title
- Two cards with same title → title + " A" / " B" (sorted by id)
- Card not in context list → should raise (or handle gracefully)

#### Recommendations (prioritized)

Medium value:
- [x] get_display_id — DONE (6 tests in `GetDisplayIdTests`: unique title, 2 duplicates, 3 duplicates, sort order, mixed titles)




## Card Set Cross-Cutting Analysis — COMPLETED

All 9 remaining modules are Card subclass implementations. Survived mutations clustered by **method type** across all card sets.

### Tests Written (Themes A–F)

**Theme A: Constructor wiring** — `tests/test_card_constructors.py`
- [x] Keyword assertions: 11 cards verified against JSON source-of-truth keywords
- [x] Trait assertions: 18 cards verified against JSON traits
- [x] Backside wiring: 8 tests covering weather card A↔B backside classes and flip round-trips

**Theme B: Card-specific test Actions** — `tests/test_card_tests.py`
- [x] Action field assertions (aspect/approach/verb) for SitkaDoe, CausticMulcher, SunberryBramble, OvergrownThicket, MiddaySun, BiscuitBasket, LoneTreeStation
- [x] Success/fail effect tests for SunberryBramble (scout+draw), OvergrownThicket (add progress), MiddaySun (flip weather)

**Theme C: Challenge effect outcomes** — `tests/test_card_effects.py`
- [x] APerfectDay Mountain (conditional progress), MiddaySun Sun (fatigue)
- [x] ProwlingWolhund Sun (ready another) + Crest (exhaust+injure at 3+ fatigue)
- [x] OvergrownThicket Mountain (remove progress + fatigue by presence)
- [x] AncestorsGrove Sun (discard→fatigue stack)

**Theme D: Location arrival setup** — `tests/test_card_effects.py`
- [x] LoneTreeStation: discard first predator, then draw 1
- [x] AncestorsGrove: discard presence-3 card, put prey into play
- [x] BoulderField: challenge-dependent draw (Sun/Mountain/Crest)
- [x] BoulderField constant ability: reduces being presence by 1

**Theme E: Weather flip mechanics** — `tests/test_card_effects.py`
- [x] APerfectDay↔MiddaySun flip transitions
- [x] Cloud token ticking (refresh removes/adds clouds)
- [x] Auto-flip at threshold (0 clouds → Midday Sun, 3 clouds → A Perfect Day)

**Theme F: Moment resolve effects** — `tests/test_card_effects.py`
- [x] ShareintheValleysSecrets: exhaust obstacles + fatigue equal to count
- [x] AffordedByNature: transfer trail progress to being harm
- [x] WalkWithMe: add progress to being equal to effort
- [x] CradledbytheEarth: soothe fatigue equal to trail progress

### Remaining (lower priority — skipped)
- [ ] Art descriptions — purely cosmetic
- [ ] Message string mutations — cosmetic
- [ ] get_listeners / enters_play registration — largely verified through integration tests
- [ ] Additional challenge effects for remaining cards (SitkaBuck, SitkaDoe, CausticMulcher, SunberryBramble, CalypsaRangerMentor, QuisiVosRascal, TheFundamentalist)
- [ ] get_constant_abilities for non-BoulderField cards

### Test Count Summary
- **Pre-audit**: 463 tests
- **Post-audit**: 734 tests + 286 subtests
- **New tests added**: 271 tests + 286 subtests across 7 new test files
