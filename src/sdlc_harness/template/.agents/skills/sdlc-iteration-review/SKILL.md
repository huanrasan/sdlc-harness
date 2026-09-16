---
name: sdlc-iteration-review
description: Run an evidence-based iteration or sprint review - delivered changes, flow and DORA signals from the harness reports, gate and sensor trends, and concrete harness adjustments. Use at the end of an iteration, sprint or release train, or when asked how the team or the harness is performing.
license: MIT
metadata:
  harness-phase: review
---
# Iteration review

## Steps

1. Generate facts, do not estimate them:
   `python3 .harness/sdlc.pyz report flow --since <start-date>` and `python3 .harness/sdlc.pyz report dora --since <start-date>`
   (add `--format html --output <file>` for a shareable page).
2. Fill `docs/sdlc/reviews/<date>.md` from `docs/sdlc/templates/iteration-review.md`: delivered changes with outcome
   links, lead time, time blocked at gates, approval wait, rework and change failure rate, sensor findings trend.
3. Look for systemic causes, not individuals: long approval waits (roster too small?), repeated gate blocks on the
   same artifact (template or skill unclear?), exceptions accumulating, flaky tests waived.
4. Propose harness adjustments with owners: rule or sensor level changes, skill clarifications, new memory entries,
   automation. Adjusting profiles or rosters is a human decision reviewed through CODEOWNERS.
