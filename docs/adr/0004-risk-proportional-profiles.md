# 0004. Risk-proportional profiles and file-based change records

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
The harness targets individuals, product teams and regulated organizations. Uniform ceremony either burdens small
changes or under-protects risky ones. Evidence must survive context resets and be reviewable in pull requests.

## Decision drivers
Proportionality (high), auditability (high), agent resumability (high), tool independence (medium).

## Options considered
1. One fixed process for all changes.
2. Profiles (`lite`, `standard`, `regulated`) whose TOML rules map change type x risk x phase to required artifacts,
   stored as Markdown in `docs/changes/<id>/`.
3. Evidence stored in an external tracker via integrations.

## Decision
Option 2. Rules are data, editable per organization. Change records are versioned with the code, readable by any agent
and reviewer, and let a fresh agent session resume from files.

## Consequences
- Positive: ceremony scales with risk; evidence travels with the code; works offline.
- Negative: partial duplication with trackers; risk classification is a judgment call (the orchestrator skill asks for
  human confirmation on high risk and architecture changes). Gates check completeness, not quality.
