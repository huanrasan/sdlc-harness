---
name: sdlc-outcome
description: Close the feedback loop after a release - measure success metrics from discovery against real data, gather user feedback and decide to keep, iterate, roll back or retire. Use in the operate phase, after the observation window of a release, or when asked whether a shipped feature worked.
license: MIT
metadata:
  harness-phase: operate
---
# Outcome

Goal: `outcome.md` that turns a release into learning and a decision.

## Steps

1. Wait for the observation window defined in `release.md` (enough traffic or time to be meaningful).
2. For every success metric in `discovery.md`, record baseline, target and the actual value with its source and date.
   Do not cherry-pick; report metrics that did not move.
3. Summarize user feedback and support signals, and any unexpected effects on performance, cost or other teams.
4. Propose `Decision: keep | iterate | rollback | retire` with rationale. Iterate and retire decisions open new change
   records (`sdlc new feature ...` or `sdlc new retirement ...`).
5. Record durable lessons as memory entries (`sdlc memory add`) so future discovery starts from evidence.
