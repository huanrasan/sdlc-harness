---
status: proposed
---
# Discovery: staff CSV export of bookings

## Problem
Staff at the three pilot studios rebuild a weekly bookings list by hand to reconcile payments: 42 support requests in
Q2 ("can you send me last week's bookings?"), each answered manually in 10-15 minutes. Two studios said they would
stop using the product if reconciliation stays manual (churn interviews, 2026-06).

## Target users
Studio staff with the `manager` role who reconcile payments weekly and prepare monthly reports for their accountant.

## Value hypothesis
We believe that a self-service CSV export of bookings for studio managers will result in fewer manual export requests
and faster reconciliation. We will know we are right when the success metrics below move.

## Success metrics
| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| manual export support requests per week | 3.5 | < 1 | support tickets tagged `export` |
| median reconciliation time per studio | 38 min | < 15 min | staff survey after 4 weeks |
| weekly active managers using export | 0 | >= 60% of studios | product analytics event `export.downloaded` |

## Options
| Option | Summary | Value | Effort | Risk |
|---|---|---|---|---|
| Do nothing | Support keeps exporting by hand | none | none | churn risk stays |
| CSV export in the admin panel | Manager picks a date range and downloads a CSV | high | S (3-4 days) | low |
| Full reporting dashboard | Charts, filters and scheduled email reports | high | L (4-6 weeks) | medium: delays reconciliation relief |

## Assumptions to validate
| Assumption | How we validate it (prototype, experiment, data) | Result |
|---|---|---|
| A CSV is enough; they do not need charts | Ask the 3 pilot studios what they do with the data | Confirmed: all three paste it into their own spreadsheet |
| Date range plus status filter covers the use case | Review the columns support sends today | Confirmed; they also want the payment reference |

## Decision
Decision: go
First increment: CSV export for a date range from the admin panel, current studio only. Out of scope: scheduled
reports, charts, cross-studio exports.
