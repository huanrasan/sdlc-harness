# 0005. Python package with a vendored zipapp

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers
**Supersedes:** [0003](0003-stdlib-python-cli-toml.md)

## Context and problem
v0.2 adds approval receipts, audit logs, semantic gates, platform verification and CODEOWNERS generation.
A single source file would exceed several thousand lines and become hard to review and test.
ADR-0003's goals still hold: no third-party dependencies, offline operation, one auditable file in target repositories.

## Decision drivers
Maintainability (high), zero runtime dependencies (high), offline CI (high), auditability of what runs in CI (medium).

## Options considered
1. Keep a single `sdlc.py`.
2. Python package (`src/sdlc_harness`) installed with pipx/pip for `init`; `init` builds a stdlib `zipapp`
   (`.harness/sdlc.pyz`, no templates) that target repositories commit and run in hooks and CI.
3. Package only, installed in every CI job from a registry.

## Decision
Option 2.

## Consequences
- Positive: modular code and tests; target repos still run one committed file with no network access.
- Negative: the `.pyz` is a binary diff in pull requests; reviewers should rely on the version and on regenerating it
  from a tagged release. Mitigation: CODEOWNERS for `/.harness/` (platform + security).
- Mitigations kept from 0003: stdlib only, Python >= 3.11, TOML configuration.
