# Comprehensive Test Design - Mutation Testing Audit

## Overall Mutation Score: 40.8% → 53.8%

| Metric | Before | After | Delta |
|--------|-------:|------:|------:|
| **Total mutants** | 8,406 | 8,406 | — |
| **Killed** | 3,433 (40.8%) | 4,528 (53.8%) | **+1,095** |
| **Survived** | 3,340 (39.7%) | 2,773 (33.0%) | -567 |
| **No tests** | 1,633 (19.4%) | 1,105 (13.1%) | -528 |

## Per-Module Comparison

| Module | Before (surv+notest) | After (surv+notest) | Delta | Status |
|--------|---------------------:|--------------------:|------:|--------|
| campaign_guide | 1,792 | 1,792 | 0 | Analyzed — mostly narrative text (low value) |
| view | 651 | 651 | 0 | Not audited — pure rendering |
| engine | 409 | 248 | **-161** | Audited |
| save_load | 419 | 187 | **-232** | Audited |
| json_loader | 183 | 118 | **-65** | Audited |
| cards (all) | 992 | 783 | **-209** | Audited (cross-cutting themes) |
| registry | 153 | 60 | **-93** | Audited |
| models | 279 | 32 | **-247** | Audited |
| decks | 39 | 9 | **-30** | Audited |
| utils | 4 | 0 | **-4** | Audited — fully killed |


