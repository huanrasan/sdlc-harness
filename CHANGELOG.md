# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.5.1] - 2026-09-17

### Fixed
- Workflow templates failed the harness's own `sensors` gate on first real use: GitHub Actions are now pinned to commit
  SHAs and GitHub context values reach `run:` steps through environment variables (no shell interpolation).

### Added
- `.github/dependabot.yml` template to keep pinned actions current; regression tests for workflow hygiene.

## [0.5.0] - 2026-09-16

### Added
- `sdlc upgrade [--dry-run]`: manifest-based 3-way upgrade (update unmodified, keep customized, `*.sdlc-new` on
  conflicts), TOML merge of new tables and keys, removal of unmodified obsolete files, legacy `sdlc.py` migration.
- `sdlc bundle [--full]`: deterministic single-file zipapp; `sdlc-full.pyz` can run `init` and `upgrade` offline.
- `sdlc init --adopt`: brownfield detection (languages, commands, IaC, contracts, CI, agent files), adoption report,
  appended harness sections for existing `AGENTS.md`, CI auto-detection.
- `sdlc evidence baseline`: pre-existing findings become exceptions awaiting a security approver; exceptions now require
  a roster role (`[authority] exception`).
- Distribution: Claude Code plugin and marketplace, Gemini CLI extension, root `skills/` for `npx skills add`,
  `sdlc-install` skill; generator with CI drift check.
- Behavioural evals (`evals/`): seven scenarios, adapters for Claude Code, Codex, Gemini CLI, OpenCode, Cursor and
  Copilot CLIs, deterministic graders tested with simulated agents.
- Release workflow for the harness: wheel/sdist, bundles, SBOM, SLSA provenance, keyless signatures, optional PyPI.
- ADRs 0012-0013; controls C28-C29.

### Fixed
- Adapters accept `CLAUDE.md` symlinked to `AGENTS.md` and link skills into existing agent skill directories.

## [0.4.0] - 2026-09-16

### Added
- `discover` phase, `retirement` change type and change scopes (`ui`, `api`, `data`, `personal-data`, `infra`, `ai`)
  with conditional artifacts and semantic gates: `discovery.md`, `ux.md`, `data.md`, `cost.md`, `ai-risk.md`,
  `outcome.md`, `retirement.md`; iteration review template.
- Eight skills: `sdlc-discover`, `sdlc-ux`, `sdlc-data`, `sdlc-finops`, `sdlc-ai-risk`, `sdlc-outcome`, `sdlc-retire`,
  `sdlc-iteration-review`.
- `sdlc org pull` and organization policy enforcement (`[require]`/`[recommend]`, hash lock, `org-` skills and memory)
  with expiring, role-authorized deviations.
- `sdlc memory add|search|index` with secret scanning, review dates and generated index.
- `sdlc mcp`: stdio MCP server with read-mostly tools; `--print-config` for common clients.
- `sdlc report trace|flow|dora` in Markdown, JSON and HTML; weekly report workflow; audit log records blocked transitions.
- Roster roles ux-lead, data-steward, finops; ADRs 0009-0011; controls C21-C27.

### Changed
- `sdlc new` starts at the first phase required by the profile and accepts `--scope`.

## [0.3.0] - 2026-09-16

### Added
- `sdlc tdd`: test-first ordering and weakened-test detection (skip/only markers, deleted tests) with waiver trailers.
- `sdlc evidence check`: policy over SARIF findings and CycloneDX SBOMs (required kinds per profile, severity threshold,
  license deny list) with expiring, attributed exceptions in `.harness/exceptions.toml`.
- `sdlc arch`: executable layer rules in `.harness/architecture.toml` for Python, JS/TS, Go, JVM, .NET, Rust and PHP.
- `sdlc contracts`: breaking-change detection for OpenAPI 3.x and AsyncAPI 2.x/3.x with a SemVer policy; stdlib YAML reader.
- `[sensors]` levels in profiles; `check --base` runs all history and structure sensors.
- CI `sensors` job (gitleaks, Semgrep, Trivy, Syft, Checkov) and signed release workflows for GitHub and GitLab
  (SBOM, SLSA provenance and SBOM attestations, keyless Sigstore signatures).
- ADRs 0007 and 0008.

## [0.2.0] - 2026-09-16

### Added
- Approval receipts (`sdlc approve`) bound to the SHA-256 of each artifact; edits invalidate approvals.
- `sdlc approvals verify`: GitHub/GitLab API verification of approver identity, approved content, role membership
  (including teams) and separation of duties.
- Hash-chained, append-only `audit.jsonl` per change (`sdlc audit verify`, `check --base`).
- Semantic gates for spec, design, threat model, plan, verification, review, release, runbook and ADRs.
- `.harness/roster.toml` with roles and authority matrix; `sdlc codeowners [--check]`.
- `approve = true` rules in profiles; `[verification] test_paths` to require cited tests to exist.
- ADRs 0005 and 0006.

### Changed
- CLI is now the `sdlc_harness` package (pipx/pip installable); `init` vendors `.harness/sdlc.pyz` into target repos
  instead of `.harness/sdlc.py`. ADR 0003 superseded by 0005.
- CI templates run approvals verification, CODEOWNERS drift check and append-only audit checks.

### Removed
- `.github/CODEOWNERS.example` (generated from the roster instead).

## [0.1.0] - 2026-09-16

### Added
- `sdlc` CLI (stdlib only): `init`, `sync`, `check`, `new`, `phase`, `commit-msg`, `hooks`, `doctor`.
- Ten Agent Skills covering the SDLC, `AGENTS.md` template and artifact templates.
- Profiles `lite`, `standard`, `regulated`; adapters for Claude Code, Codex, Copilot, Cursor, Gemini CLI, OpenCode, Windsurf.
- GitHub Actions and GitLab CI gate templates.
- Bilingual guide, research and controls matrix; ADRs 0001-0004.
