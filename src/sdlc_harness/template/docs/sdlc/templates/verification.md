# Verification: <!-- sdlc:fill -->

## Commands run
```text
<!-- sdlc:fill --> command + summarized output (pass/fail counts, coverage)
```

## Acceptance criteria
| ID | Result | Evidence (test name / manual check) |
|---|---|---|
| AC-1 | <!-- sdlc:fill --> | |

Result is `pass`, `verified` or `n/a`. Use `blocked` or `pending` when a criterion honestly cannot be verified yet;
it must then name who owns it and why, as in `blocked - owner: rita - needs repository admin to protect the branch`.
The gate stays red (verify does not close) but the record says what is true.

In the evidence column, `backticks` hold a test name (a sentence is fine), a repository path, or a command
written as `$ pnpm test:integration`. An unmarked token that is neither a test nor a file fails the gate:
that is how invented evidence is caught, so mark commands rather than dropping the formatting.

## Security and quality sensors
| Sensor | Tool | Result | Findings |
|---|---|---|---|
| Secrets | <!-- sdlc:fill --> | | |
| SAST | | | |
| Dependencies / licenses | | | |
| IaC / policy | | | |
| Container | | | |

## Findings disposition
| Finding | Disposition (fixed / accepted / false positive) | Rationale | Who |
|---|---|---|---|
