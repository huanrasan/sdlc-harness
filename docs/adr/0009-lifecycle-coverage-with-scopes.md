# 0009. Full lifecycle coverage with conditional scopes

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
v0.3 started at specification and ended at operation. Product discovery, UX, data and privacy, cost, AI-specific risk,
post-release outcomes, iteration reviews and decommissioning were missing. Adding every artifact to every change would
bury small changes in ceremony.

## Decision drivers
Coverage of the whole lifecycle (high), proportionality (high), compatibility with existing profiles (medium).

## Options considered
1. Role-based agents (product owner, UX designer, data engineer...) each owning a pipeline stage.
2. A `discover` phase before `spec`, a `retirement` change type, and **scopes** declared per change
   (`ui`, `api`, `data`, `personal-data`, `infra`, `ai`) that make artifacts conditional (`ux.md`, `data.md`, `cost.md`,
   `ai-risk.md`); `outcome.md` closes the loop in `operate`; iteration reviews are periodic, not per change.
3. Separate harnesses per discipline.

## Decision
Option 2. Changes start at the first phase their profile requires, so fixes still start at `spec`. Skills remain
phase- and concern-oriented rather than impersonating roles; people hold roles through the roster.

## Consequences
- Positive: one flow from idea to retirement; ceremony grows only with type, risk and scope; each new artifact has
  semantic gates (metrics, states, privacy answers, numeric cost, eval thresholds, sunset date).
- Negative: scope declaration depends on correct classification (the orchestrator asks humans to confirm risky cases);
  more roles in the roster (ux-lead, data-steward, finops).
