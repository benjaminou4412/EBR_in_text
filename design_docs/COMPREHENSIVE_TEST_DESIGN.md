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

