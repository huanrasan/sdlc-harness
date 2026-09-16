---
name: sdlc-orchestrator
description: Entry point for any development request. Use when starting a task, bug fix, feature, refactor or architecture change, or when unsure which SDLC phase or skill applies.
license: MIT
metadata:
  harness-phase: all
---
# SDLC orchestrator

Route the request through the right track with the least ceremony that still leaves evidence.
If the repository has no `harness.toml`, the harness is not installed: offer the `sdlc-install` skill instead.

## 1. Classify

| Signal | type | Typical risk |
|---|---|---|
| Defect with known expected behaviour, local blast radius | `fix` | low |
| New or changed user-visible behaviour, API, data model | `feature` | medium |
| Cross-cutting decision: new service, datastore, cloud/runtime, security boundary, public contract, anything hard to reverse | `architecture` | medium/high |
| Removing or deprecating a service, feature, API version, dataset or infrastructure | `retirement` | medium |

Raise risk one level when the change touches: authentication/authorization, personal or financial data,
money movement, infrastructure or network boundaries, data migrations, or availability-critical paths.
Trivial edits (typos, comments, formatting, dependency bumps with green CI) need no change record.

Declare scopes so conditional artifacts apply: `ui` (screens), `api` (public contracts), `data` (schemas, datasets),
`personal-data`, `infra` (cloud or on-prem resources, cost), `ai` (LLMs, ML models, agents in the product).

State the classification and the reason in one sentence and ask the human to confirm when risk is `high`
or the type is `architecture` or `retirement`.

Before starting, search memory for prior decisions and pitfalls: `python3 .harness/sdlc.pyz memory search "<topic>"`.

## 2. Open the change record

```bash
python3 .harness/sdlc.pyz new <type> <kebab-slug> --risk <risk> --scope <scope,...>
```

## 3. Walk the phases

| Phase | Skill | Exit evidence |
|---|---|---|
| discover | `sdlc-discover` | `discovery.md` with success metrics and a go decision |
| spec | `sdlc-specify` | `spec.md` with testable acceptance criteria |
| design | `sdlc-design` (+ `sdlc-ux`, `sdlc-data`, `sdlc-finops`, `sdlc-ai-risk`, `sdlc-retire` by scope/type) | `design.md`, ADR(s), `threat-model.md` and scope artifacts |
| plan | `sdlc-plan` | `plan.md` with small, ordered, verifiable tasks |
| implement | `sdlc-implement` | code + tests in small commits |
| verify | `sdlc-verify` | `verification.md` with command output and sensor evidence |
| review | `sdlc-review` | `review.md` from a fresh-context reviewer + human PR approval |
| release | `sdlc-release` | `release.md`, version, changelog, SBOM/provenance, rollback plan |
| operate | `sdlc-operate`, `sdlc-outcome` | `runbook.md`, `outcome.md` with measured results and decision |

`sdlc new` starts at the first phase the profile requires (small changes start at `spec`).
Periodic work: `sdlc-iteration-review` at the end of an iteration, `sdlc-maintain` for garbage collection.

Advance with `python3 .harness/sdlc.pyz phase <id> <next>`. When the gate reports that an artifact
requires approval, stop: tell the human which artifact, which roles may approve (`.harness/roster.toml`), and the
command they run themselves: `python3 .harness/sdlc.pyz approve <id> <artifact> --as <username> --role <role>`,
followed by an approving review on the pull request. Any later edit to that artifact invalidates the approval. The profile in `harness.toml` decides which
artifacts are mandatory; artifacts that are not mandatory are still welcome when they reduce risk.

## 4. Stop conditions

Stop and ask a human when: requirements conflict, a gate fails for reasons outside the change,
a destructive operation is needed, credentials are required, or you have failed the same check 3 times.
Long tasks: before the context fills up, write progress and next steps into the change record so a fresh
session can resume from files alone.
