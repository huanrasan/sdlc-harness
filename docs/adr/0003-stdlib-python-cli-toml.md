# 0003. Stdlib-only Python CLI with TOML configuration

> Superseded by [0005](0005-package-with-vendored-zipapp.md): the single-file constraint no longer scales; stdlib-only and TOML remain.

**Status:** Superseded by 0005
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Gates must run on developer laptops, hosted CI and restricted private-cloud runners without internet access, for any
application stack.

## Decision drivers
Zero install friction (high), offline operation (high), readability for auditors (medium), contributor familiarity (medium).

## Options considered
1. Node.js CLI distributed via npm.
2. Go binary.
3. Single-file Python ≥ 3.11 script using only the standard library, TOML config (`tomllib`).
4. Bash scripts.

## Decision
Option 3. Python is present on most CI images and developer machines; a single file is vendored into each repository
(`.harness/sdlc.py`) so it needs no package registry. TOML is parsed by the standard library, avoiding a YAML dependency.

## Consequences
- Positive: auditable single file, no supply-chain dependencies, works offline.
- Negative: requires Python ≥ 3.11; SKILL.md frontmatter is parsed with a minimal YAML subset (flat scalars and one-level maps).
  Vendored copies must be updated explicitly.
