# Comprehensive Test Design - Mutation Testing Audit

## Overall Mutation Score: 40.8%
- **Total mutants**: 8,406
- **Killed**: 3,433 (40.8%)
- **Survived**: 3,340 (39.7%) — tests ran but didn't detect the mutation
- **No tests**: 1,633 (19.4%) — no test exercised this code at all

## Per-Module Breakdown

| Module | Total | Kill % | Survived | No Tests | Priority |
|--------|------:|-------:|---------:|---------:|----------|
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



