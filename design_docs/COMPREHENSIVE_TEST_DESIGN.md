# Comprehensive Test Design - Mutation Testing Audit

## Overall Mutation Score: 40.8%
- **Total mutants**: 8,406
- **Killed**: 3,433 (40.8%)
- **Survived**: 3,340 (39.7%) — tests ran but didn't detect the mutation
- **No tests**: 1,633 (19.4%) — no test exercised this code at all

## Per-Module Breakdown

| Module | Total | Kill % | Survived | No Tests | Priority |
|--------|------:|-------:|---------:|---------:|----------|
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

