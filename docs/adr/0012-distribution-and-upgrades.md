# 0012. Distribution channels and manifest-based upgrades

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Installing required cloning the repository, and there was no safe way to move a repository to a newer harness without
losing local customizations (filled `AGENTS.md`, tuned profiles, roster, edited templates). Teams also want to get the
skills through their agent's native distribution channel.

## Decision drivers
Customizations preserved (high), repository install remains authoritative (high), offline installs (medium),
low maintenance of per-agent packages (medium).

## Options considered
1. Overwrite on upgrade and let git diffs sort it out.
2. Record hashes of installed harness files in `.harness/manifest.toml`; `sdlc upgrade` performs a 3-way decision per
   file (unmodified -> update, customized and template unchanged -> keep, both changed -> write `*.sdlc-new`),
   merges `harness.toml`/`roster.toml` by adding missing tables and keys, removes unmodified obsolete files and rebuilds
   the vendored CLI. Distribution through pipx/pip, a deterministic single-file `sdlc-full.pyz`, a Claude Code
   plugin/marketplace and a Gemini CLI extension generated from the template skills (checked in CI), and the root
   `skills/` directory for `npx skills add`.
3. Per-agent plugins as the primary install.

## Decision
Option 2. Plugins and extensions deliver skills and an `sdlc-install` skill; gates, approvals and sensors still require
the repository installation. A Codex plugin is not generated until its manifest format is documented publicly.

## Consequences
- Positive: upgrades are reviewable diffs with explicit conflicts; one-file installs work in restricted networks;
  generated packages cannot drift from templates.
- Negative: repositories installed before 0.5 have no manifest, so changed files surface as `.sdlc-new` once; TOML
  merges add missing keys but never change values the template changed (release notes must call these out).
