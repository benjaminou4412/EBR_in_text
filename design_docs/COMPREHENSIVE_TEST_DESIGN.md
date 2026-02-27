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
- [ ] Do NOT try to test narrative text content — that's a losing battle with mutation testing
- [ ] Do NOT test `resolve_entry_1` in isolation — it's fine as an integration concern
