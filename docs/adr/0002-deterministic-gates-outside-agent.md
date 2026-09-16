# 0002. Enforce gates with git hooks and CI, not agent hooks

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Organizations need controls that cannot be skipped by a misbehaving or prompt-injected agent. Agent lifecycle hooks
exist in several tools but differ in event names, semantics and stability, and run under the agent's control.

## Decision drivers
Enforceability (high), agent independence (high), fast feedback (medium).

## Options considered
1. Agent lifecycle hooks as the enforcement point.
2. Git hooks for fast feedback + CI as the authoritative gate + VCS platform settings for human approval.
3. Only CI.

## Decision
Option 2. The same `sdlc check` command runs in all three places. Agent hooks may call it as optional adapters.

## Consequences
- Positive: identical behaviour for humans and agents; works in any CI, including private and air-gapped.
- Negative: local hooks can be bypassed (`--no-verify`), so protection depends on CI + branch protection being configured;
  `sdlc doctor` flags missing CI and CODEOWNERS (errors under the regulated profile).
