---
name: sdlc-install
description: Install, adopt or upgrade the SDLC harness in the current repository. Use when a repository has no harness.toml and the user wants SDLC gates, change records and approvals, or when asked to set up, adopt or upgrade sdlc-harness.
license: MIT
metadata:
  harness-phase: setup
---
# Install or upgrade the SDLC harness

The skills in this plugin/extension only enforce anything once the harness is installed in the repository
(`harness.toml`, `.harness/`, CI gates). Installing writes many files: confirm with the user first.

## New or existing repository without `harness.toml`

1. Ask which profile (`lite`, `standard`, `regulated`) and CI (`github`, `gitlab`, `none`) to use; default to
   `lite` for existing repositories and let the adoption report suggest the rollout.
2. Run one of (Python >= 3.11 required):
   ```bash
   pipx run --spec git+https://github.com/huanrasan/sdlc-harness sdlc init . --adopt --profile lite
   # or, without pipx, the single-file release:
   curl -fsSLo /tmp/sdlc-full.pyz https://github.com/huanrasan/sdlc-harness/releases/latest/download/sdlc-full.pyz
   python3 /tmp/sdlc-full.pyz init . --adopt --profile lite
   ```
3. Show the user `docs/sdlc/adoption.md` and the next steps printed by `init`. Roster members, CODEOWNERS and branch
   protection are human decisions: list them, do not invent people or teams.

## Repository with `harness.toml`

1. `python3 .harness/sdlc.pyz --version` and compare with the latest release.
2. Preview: `pipx run --spec git+https://github.com/huanrasan/sdlc-harness sdlc upgrade --dry-run`
   (or `python3 /tmp/sdlc-full.pyz upgrade --dry-run`), then run without `--dry-run` after the user agrees.
3. Merge every `*.sdlc-new` file the upgrade reports, delete it, run `python3 .harness/sdlc.pyz check`, and commit.
