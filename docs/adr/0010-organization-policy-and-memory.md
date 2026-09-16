# 0010. Vendored organization policy with deviations, and reviewed memory

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Organizations need minimum controls that individual repositories cannot silently weaken, with a governed way to accept
exceptions. Agents also need durable knowledge across sessions (decisions, pitfalls, conventions) without turning memory
into an unreviewed injection channel (OWASP Agentic ASI06).

## Decision drivers
Enforceable minimums (high), offline CI (high), explicit and expiring exceptions (high), memory integrity (high),
agent neutrality (high).

## Options considered
1. Policy fetched at runtime from a central service; memory in a database behind an MCP server.
2. `sdlc org pull` vendors a policy repository (policy, `org-` skills, memory) into the repo with a content-hash lock;
   `[require]` minimums fail the gate unless a deviation in `.harness/deviations.toml` names an authorized approver and an
   expiry; memory entries are Markdown files reviewed in pull requests, searchable by CLI and MCP.
3. Documentation-only guidelines.

## Decision
Option 2. Project settings may be stricter than the organization, never looser. An optional stdio MCP server exposes
read-mostly tools (memory search/add, change status, check, trace) and deliberately no approval or policy tools.

## Consequences
- Positive: works air-gapped; policy updates are visible diffs; local edits to vendored files are detected; memory has
  provenance, review dates and secret scanning.
- Negative: policy updates require a pull per repository (schedule it); keyword search is simpler than semantic search.
