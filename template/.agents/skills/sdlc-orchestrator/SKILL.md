---
name: sdlc-orchestrator
description: Entry point for any development request. Use when starting a task, bug fix, feature, refactor or architecture change, or when unsure which SDLC phase or skill applies.
license: MIT
metadata:
  harness-phase: all
---
# SDLC orchestrator

Route the request through the right track with the least ceremony that still leaves evidence.

## 1. Classify

| Signal | type | Typical risk |
|---|---|---|
| Defect with known expected behaviour, local blast radius | `fix` | low |
| New or changed user-visible behaviour, API, data model | `feature` | medium |
| Cross-cutting decision: new service, datastore, cloud/runtime, security boundary, public contract, anything hard to reverse | `architecture` | medium/high |

Raise risk one level when the change touches: authentication/authorization, personal or financial data,
money movement, infrastructure or network boundaries, data migrations, or availability-critical paths.
Trivial edits (typos, comments, formatting, dependency bumps with green CI) need no change record.

State the classification and the reason in one sentence and ask the human to confirm when risk is `high`
or the type is `architecture`.

## 2. Open the change record

```bash
python3 .harness/sdlc.py new <type> <kebab-slug> --risk <risk>
```

## 3. Walk the phases

| Phase | Skill | Exit evidence |
|---|---|---|
| spec | `sdlc-specify` | `spec.md` with testable acceptance criteria |
| design | `sdlc-design` | `design.md`, ADR(s), `threat-model.md` when required |
| plan | `sdlc-plan` | `plan.md` with small, ordered, verifiable tasks |
| implement | `sdlc-implement` | code + tests in small commits |
| verify | `sdlc-verify` | `verification.md` with command output |
| review | `sdlc-review` | `review.md` from a fresh-context reviewer + human PR approval |
| release | `sdlc-release` | `release.md`, version, changelog, SBOM/provenance, rollback plan |
| operate | `sdlc-operate` | `runbook.md`, dashboards/alerts, post-release check |

Advance with `python3 .harness/sdlc.py phase <id> <next>`. The profile in `harness.toml` decides which
artifacts are mandatory; artifacts that are not mandatory are still welcome when they reduce risk.

## 4. Stop conditions

Stop and ask a human when: requirements conflict, a gate fails for reasons outside the change,
a destructive operation is needed, credentials are required, or you have failed the same check 3 times.
Long tasks: before the context fills up, write progress and next steps into the change record so a fresh
session can resume from files alone.
