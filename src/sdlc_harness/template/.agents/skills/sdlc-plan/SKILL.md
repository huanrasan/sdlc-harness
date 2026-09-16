---
name: sdlc-plan
description: Break an approved spec and design into small, ordered, independently verifiable tasks with a test strategy. Use in the plan phase or before starting implementation of anything larger than a single commit.
license: MIT
metadata:
  harness-phase: plan
---
# Plan

Goal: `plan.md` that lets work proceed in small batches, each leaving the system releasable.

## Steps

1. Map every acceptance criterion and every threat-model mitigation to at least one test (unit, integration,
   contract, end-to-end, performance, security) in a traceability table.
2. Slice the work vertically. Each task: one intent, fits in one reviewable pull request (guideline: < 400 changed
   lines), has an explicit "done when" check that is a command, not an opinion.
3. Order tasks to reduce risk early: contracts and migrations first (expand/contract), feature flags for
   incomplete behaviour, destructive steps last and behind human confirmation.
4. Identify the environments, data and credentials each task needs. Never plan to use production data in tests.
5. Mark tasks that can run in parallel and tasks that need a human decision.
6. Define the rollback approach for each migration or infrastructure change.

Keep the plan current: tick tasks as they complete and note deviations with the reason.
