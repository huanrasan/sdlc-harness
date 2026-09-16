# User guide

> Versión en español: [../es/guia.md](../es/guia.md)

## Requirements

- Git and Python ≥ 3.11 (standard library only). Windows: use WSL, Git Bash, or `--mode copy`.
- Any coding agent that reads `AGENTS.md`. Skills work natively or through generated adapters.

## Install into a repository

```bash
pipx install git+https://github.com/huanrasan/sdlc-harness.git
sdlc init path/to/your-repo --profile standard --agents claude-code,codex,copilot,cursor,gemini-cli --ci github
cd path/to/your-repo
python3 .harness/sdlc.pyz hooks
python3 .harness/sdlc.pyz doctor
```

`init` never overwrites existing files (it lists what it skipped) and vendors the CLI as `.harness/sdlc.pyz`
(standard library only), so target repositories and CI need nothing but Python >= 3.11. Then:

1. Fill the `Project` section of `AGENTS.md` (build/test/lint commands). Keep it short.
2. Put people or teams in `.harness/roster.toml`, run `python3 .harness/sdlc.pyz codeowners`, and configure branch
   protection (see [controls](controls.md#platform-configuration-checklist)).
3. Add stack-specific CI jobs (tests, SAST, SBOM...) next to `sdlc-gates`.
4. Commit everything, including generated adapters, so every contributor and CI sees the same harness.

| Option | Values | Notes |
|---|---|---|
| `--profile` | `lite`, `standard`, `regulated` | Changeable later in `harness.toml`. |
| `--agents` | keys of `.harness/adapters.toml` | Agents that read `.agents/skills` natively need no files. |
| `--mode` | `symlink`, `copy` | `copy` for filesystems without symlinks; `check` detects drift. |
| `--ci` | `github`, `gitlab`, `none` | GitLab: include `.gitlab-ci.sdlc.yml` from your `.gitlab-ci.yml`. |

## Daily workflow

Ask your agent for the work as usual. `AGENTS.md` sends it to the `sdlc-orchestrator` skill, which:

```bash
python3 .harness/sdlc.pyz new feature payment-retries --risk high   # opens docs/changes/<date>-payment-retries/
python3 .harness/sdlc.pyz phase <id> design                          # blocked until spec.md is complete and approved
python3 .harness/sdlc.pyz check                                      # same gate CI runs
```

Required artifacts per profile, type and risk are defined in `.harness/profiles/<profile>.toml`. A rule makes
an artifact mandatory once the change has moved **past** the rule's phase. Unfilled template sections
(`<!-- sdlc:fill -->`) fail the gate. Beyond presence, **semantic gates** check consistency:

| Artifact | Checks |
|---|---|
| `spec.md` | at least one `AC-n` criterion in Given/When/Then or EARS form; no empty NFR rows |
| `threat-model.md` | at least one `T-n` threat; every threat has a control that is verifiable |
| `plan.md` | every `AC-n` and `T-n` is in the traceability table with a test; every task has a "done when" check |
| `verification.md` | every `AC-n` passed with evidence; cited tests exist when `[verification] test_paths` is set; findings have dispositions |
| `review.md` | verdict `ready-for-human-approval`, fresh context `yes`, no unchecked items |
| `release.md`, `runbook.md` | version, artifacts, rollout and rollback; at least one alert and safe mitigations |
| ADRs | at least two options, decision and consequences |

| Artifact | lite | standard | regulated |
|---|---|---|---|
| `spec.md` | feature/architecture; fix from medium | all | all |
| `design.md` | architecture; feature high | feature from medium; architecture | all |
| ADR | architecture | architecture | architecture |
| `threat-model.md` | - | feature high; architecture from medium | feature from medium; architecture |
| `plan.md` | - | feature from medium; architecture | all |
| `verification.md` | from medium | all | all |
| `review.md` | - | from medium | all |
| `release.md` | - | feature/architecture from medium | all |
| `runbook.md` | - | feature high; architecture from medium | feature/architecture from medium |
| `Change:` commit trailer | - | - | required |
| Human approval receipts | none | spec, design, ADR, threat model, release | every artifact |

## Approvals

Profiles mark artifacts with `approve = true`. Such an artifact blocks the next phase until a human in an authorized
role (see `[authority]` in `.harness/roster.toml`) records a receipt and approves the pull request:

```bash
python3 .harness/sdlc.pyz approve <id> spec.md --as alice --role product-owner   # human only
git add docs/changes/<id> && git commit -m "docs: approve spec" && git push
# then submit an approving review on the pull request
```

The receipt stores the SHA-256 of the artifact. Editing the artifact afterwards invalidates the approval.
In CI, `sdlc approvals verify` confirms with the GitHub or GitLab API that the named person approved a commit containing
that exact content and the receipt, belongs to the role (directly or via a team), and, with `separation_of_duties`,
did not author the pull request or the artifact. Every change also keeps a hash-chained `audit.jsonl`; CI rejects
edits to existing events. GitLab projects must enable "Remove all approvals when commits are added"; team checks need
a token with organization read access (`SDLC_APPROVALS_TOKEN` secret on GitHub, `GITLAB_TOKEN` on GitLab).

## How it works

```text
            guides (feedforward)                         sensors (feedback)
  AGENTS.md ──> .agents/skills/<phase>/SKILL.md    tests, linters, scanners (stack CI)
       │                  │                        sdlc check / phase gates
       ▼                  ▼                        independent review (fresh context)
  any agent ──writes──> docs/changes/<id>/*  ──>  git hooks (fast) ──> CI (authoritative) ──> human approval (platform)
       ▲
  adapters generated by `sdlc sync` from .harness/adapters.toml (CLAUDE.md, GEMINI.md, skill links)
```

| Path | Purpose |
|---|---|
| `AGENTS.md` | Map for agents: project commands, workflow, non-negotiables, generated skills index. |
| `.agents/skills/` | Canonical skills (Agent Skills format), one per SDLC phase plus orchestrator and maintenance. |
| `harness.toml` | Profile, agent targets, paths, verification settings. |
| `.harness/roster.toml` | Roles, members, authority matrix, extra CODEOWNERS rules. |
| `.harness/profiles/` | Gate rules per profile (editable TOML). |
| `.harness/adapters.toml` | Declarative per-agent adapters. |
| `.harness/sdlc.pyz`, `.harness/hooks/` | Vendored CLI and git hooks. |
| `docs/changes/<id>/approvals.toml`, `audit.jsonl` | Approval receipts and hash-chained audit log. |
| `docs/changes/` | Change records (system of record). |
| `docs/sdlc/templates/` | Artifact templates. |
| `docs/adr/` | Architecture decision records. |

## Extending

- **New agent**: add an entry to `.harness/adapters.toml` (`files` with required content, `links` to mirror skills),
  add it to `targets`, run `sdlc sync`. Please upstream it.
- **Custom profile**: copy a profile to `.harness/profiles/<name>.toml`, set `profile = "<name>"`.
- **Organization skills**: add folders under `.agents/skills/` (for example, your cloud landing-zone rules) and run `sdlc sync`.
- **Agent hooks (optional)**: point your agent's pre-tool or stop hook at `python3 .harness/sdlc.pyz check`
  for earlier feedback; CI stays authoritative.
- **MCP (optional)**: memory (e.g. engram) or code intelligence (e.g. gortex) servers complement, but never replace, change records.

## Updating the harness

Upgrade the package (`pipx upgrade sdlc-harness`), re-run `init` into a scratch directory and compare; copy
`.harness/sdlc.pyz` and the skills you have not customized. Profile, roster and adapter files are yours once installed.
An `sdlc upgrade` command is planned for v0.5.
