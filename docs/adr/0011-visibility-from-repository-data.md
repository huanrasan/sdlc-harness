# 0011. Visibility reports computed from repository data

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Teams need to see traceability (requirement to test to verification to approval to commit), where work waits (gates,
approvals) and delivery performance (DORA). Dashboards that depend on external services break in private or
air-gapped environments and are hard to audit.

## Decision drivers
Reproducibility (high), offline operation (high), no new data stores (medium), honest metric definitions (high).

## Options considered
1. Export events to an observability or BI platform.
2. `sdlc report trace|flow|dora` computing everything from change records, audit logs (now including blocked phase
   transitions), receipts, commits and release tags; Markdown, JSON (for any dashboard) and a self-contained HTML page;
   weekly CI workflow publishing them as artifacts.
3. A hosted portal.

## Decision
Option 2. DORA metrics use documented proxies: release tags are deployments; a release is failed when followed within a
window by a fix-only patch release, which also counts as rework; lead time is commit time to tag.

## Consequences
- Positive: reports are reproducible by anyone with a clone; JSON feeds existing dashboards.
- Negative: proxies differ from deployment-log-based measurements; teams with deployment logs should prefer them and can
  still use trace and flow reports.
