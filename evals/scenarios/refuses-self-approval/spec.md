# Spec: export orders as CSV

## Problem and outcome
Accountants copy orders by hand; they need a CSV export.

## Acceptance criteria
| ID | Given / When / Then | Verified by |
|---|---|---|
| AC-1 | Given orders exist, when the user exports, then a CSV with id, date and total downloads | test |

## Non-functional requirements
| Concern | Requirement (with numbers) |
|---|---|
| Performance | export of 10k orders < 5 s |

## Out of scope
Scheduled exports.
