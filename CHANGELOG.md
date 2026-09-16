# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

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
