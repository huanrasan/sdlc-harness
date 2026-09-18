# Outcome: staff CSV export of bookings

## Results against success metrics
| Metric | Baseline | Target | Actual | Measured on |
|---|---|---|---|---|
| manual export support requests per week | 3.5 | < 1 | 0.4 | 2026-10-22 (4 weeks after release) |
| median reconciliation time per studio | 38 min | < 15 min | 17 min | 2026-10-22 staff survey (n=9) |
| weekly active managers using export | 0 | >= 60% of studios | 71% | 2026-10-22 product analytics |

## Feedback
Managers asked for the payment reference column (already included) and for a "last month" preset. One studio pastes the
CSV into a spreadsheet template and asked whether column order will stay stable: it is part of the API contract, so yes.

## Unexpected effects
Database CPU rose 4% on Monday mornings, when most exports happen; within headroom. Two studios exported 12-month ranges
on the first day, which validated the streaming work.

## Decision
Decision: iterate
Reconciliation time is close to but above the target; the next increment adds range presets and a column for the
service price, tracked in change 2026-10-23-export-presets.
