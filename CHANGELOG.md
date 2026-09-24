# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.7.3] - 2026-09-24

From a second round of field feedback. Each fix removes a reason to write worse documentation to get past a gate.

### Fixed
- `verification.md` evidence: every token in `backticks` was treated as a test name, so commands and paths failed
  and pushed people to rewrite evidence as unformatted prose. A token is now a test name (sentences included, as
  vitest and jest name tests), a repository path that must exist (with `::test` or `:line` suffixes), or a command
  marked with a leading `$ `. Whitespace could not be the rule: in a real repository all 24 test names were
  sentences, and treating them as commands would have silently disabled the check. The old rule runs first, so
  nothing that passed before can fail now.
- `sdlc tdd --explain` truncated its listing ("... and 14 more"), which hid exactly the files someone needed. It now
  prints everything, and `sdlc tdd --explain <path> ...` answers for specific files, naming the glob that decided
  each one.
- `verification.test_paths` used pathlib's glob, where `tests/**` matches only directories before Python 3.13.
  On 3.11 and 3.12 no test file was read and every cited test name was reported missing. It now uses the same
  git-style matcher as `tdd`, so one glob dialect covers the whole harness on every supported Python, and it skips
  `node_modules`, virtual environments and `.git`, where a string match would let an invented test name "exist".
  Found by the 3.11 CI job; the suite now also runs on 3.12 locally before release.
- The Given/When/Then check only knew English keywords while the skills tell teams to write prose in their own
  language, so every Spanish criterion produced a warning. `Dado/Cuando/Entonces` and `debe` now count.

## [0.7.2] - 2026-09-18

### Added
- A playbook in both languages (`docs/en/playbook.md`, `docs/es/manual.md`): the long version of the walkthrough,
  built on the example change record. For every phase it names who acts, the exact command, why the harness asks
  for it, the real error text when it blocks and how to get out; then one card per role, and the three situations
  that look like failures but are not (a criterion that cannot be verified yet, an approved document that needs a
  true addition, a risk that cannot be fixed now). Every quoted message was captured from a real run.
- Upgrade notes in both languages (`docs/en/upgrading.md`, `docs/es/actualizar.md`): what changes for a repository
  that already runs the harness, starting with the four things in 0.7 that can turn a pipeline red - the new
  workflow-linting job, the Node 24 runner requirement for self-hosted runners, source globs that now match more
  files, and the signature bundle format.
- A test that fails when any CLI command is missing from the user documentation in either language. It found
  `sdlc hooks`, `sdlc commit-msg` and `sdlc bundle`, undocumented since they were added.
- A test that ties the playbook's role table to the authority matrix in the roster, so the documentation cannot
  drift into telling a role it approves something it does not.

### Changed
- The reference guide documents `sdlc amend`, the proposal commands, `sdlc tdd --explain`, the glob semantics, the
  workflow-linting job, the `scripts/build-release` contract, `[release] sbom_source` and the single-maintainer
  signing mode.
- `AGENTS.md`, the shipped `docs/sdlc/README.md` and the `sdlc-verify` skill state the rules the 0.7 features
  introduced: agents propose deviations and exceptions but never approve them, `sdlc amend` is human-only, and a
  criterion that cannot be verified yet is `blocked`/`pending` with an owner rather than an invented result.

## [0.7.1] - 2026-09-18

### Fixed
- The `sdlc-orchestrator` skill told agents to ask a human to confirm an `architecture` or `retirement`
  classification before opening the change record, so an agent could end its turn with a correct analysis and
  nothing written to disk. Found by an eval run against a real agent, which failed for exactly that reason while
  following the guidance. The confirmation now happens with the record already open and the question written
  inside it.
- `sdlc upgrade` run from the vendored `.harness/sdlc.pyz` ended in a `ValueError` traceback, because that build
  carries no templates by design. It now explains that the command needs the installed package or `sdlc-full.pyz`.
  Found while validating a real repository after its upgrade.
- The eval runner counted an agent that never ran - expired session, missing credential, usage limit - as a
  behavioural failure. Trials where the agent exits non-zero without touching the repository are now reported as
  `ERROR`, excluded from the pass rates and listed as "not measured", and the runner exits 2 when nothing could be
  measured. A usage limit hit mid-run is what exposed this.

### Changed
- Template workflows pin the current action releases (checkout 7.0.1, setup-python 7.0.0, attest-build-provenance
  4.2.2, attest-sbom 4.1.0, upload-artifact 7.0.1, cosign-installer 4.1.2, dependency-review 5.0.0). Dependabot only
  scans a repository's own `.github/workflows`, so the shipped template does not get these updates by itself.
- Release signing passes `--new-bundle-format` explicitly. cosign-installer 4 ships cosign 3, where that flag
  defaults to true, so the bundle format would otherwise have changed silently between releases. cosign 2.x needs
  the same flag on `verify-blob` to read the bundles; the workflow header says so.

## [0.7.0] - 2026-09-18

Everything here comes from taking the harness through a complete lifecycle on a real application, and fixes what that
run exposed.

### Added
- `sdlc amend <change> <artifact> --as <user> --role <role>`: shows the approver the diff since their approval and
  records a fresh receipt once they confirm. Refuses to run outside a terminal, so an agent cannot use it
  ([ADR-0015](docs/adr/0015-amendment-instead-of-append-only-sections.md)).
- `sdlc deviation propose|approve` and `sdlc exception propose|approve`: an agent can write the proposal, only a human
  with an authorized role approves it, and `sdlc check` lists what is pending. Accepted risk now expires on its own
  instead of living in prose.
- `verification.md` accepts `blocked` and `pending` results when they name an owner and a reason. The gate stays red,
  so the phase does not advance, but the record can say what is actually true.
- `sdlc tdd --explain`: how every tracked file is classified (test / source / other), and a warning when source files
  fall outside the globs, which used to disable the test-first sensor silently.
- `sdlc check --staged`: the pre-commit hook now validates only the change records the commit touches.
- `sdlc config <key> [--default <v>]`: read one value from `harness.toml` in scripts and CI.
- Workflow linting in the shipped `sdlc-gates.yml` and in this repository's CI: actionlint (with shellcheck) and
  zizmor. The harness required actions pinned by SHA and no interpolation of untrusted context into `run:`; now it
  verifies it.

### Changed
- With `separation_of_duties = false`, `sdlc approvals verify` accepts a receipt that arrives in a commit whose
  signature the platform verifies, instead of requiring a self-review that GitHub forbids. The single-maintainer mode
  was unreachable before ([ADR-0014](docs/adr/0014-approval-integrity-for-one-maintainer.md)).
- Approval gate messages spell out the exact command a human must run.
- `cost.md`: the production total accepts a currency before or after the amount (`USD 77,40`), and the guardrails
  section is judged by content (budget, alert thresholds, allocation tags, idle policy) instead of by punctuation.
  Both messages now say what is missing and show a valid example.
- `tdd` globs follow git semantics: `**` spans any number of directories including none, `*` and `?` stay inside one
  segment. `src/**/*.ts` now matches `src/proxy.ts`.
- Scanner images in every shipped workflow are pinned by digest, all checkouts set `persist-credentials: false`, and
  `dependency-review` only runs where the dependency graph exists (it failed on every private repository without
  GitHub Advanced Security).
- The release build contract (`scripts/build-release`, executable, no arguments, artifacts in `dist/`) is documented
  in `harness.toml` and the `sdlc-release` skill, and the SBOM source is configurable with `[release] sbom_source`,
  so a container release no longer produces an SBOM of the directory holding the image.
- Memory entry file names are ASCII and cut on a word boundary.
- Invalid TOML in `harness.toml` reports a readable error instead of a traceback.
- `sdlc explain` covers the new messages, plus the `amend` and `separation-of-duties` concepts.

## [0.6.0] - 2026-09-18

### Added
- `sdlc status`: one screen per change with the current blockers, pending approvals (role and the people who hold it)
  and the exact next command; `--format json` for tooling. Also exposed as the MCP `change_status` tool.
- `sdlc explain <topic|message>`: phases, artifacts (with the profile's rules and approvers), roles, scopes, concepts
  and a catalogue of gate messages with cause and fix. Works outside an installed repository. Also an MCP tool.
- `sdlc init --interactive`: guided setup for profile, agents, CI, link mode, adoption and roster members.
- `docs/examples/`: a complete change record produced with the harness, passing every gate with no traceability gaps,
  plus its `report trace` and `status` output, and a README explaining what to look at.
- Bilingual glossary (`docs/en/glossary.md`, `docs/es/glosario.md`).
- Documentation site built with MkDocs Material and published to GitHub Pages (`mkdocs.yml`, `docs/index.md`,
  `.github/workflows/docs.yml`).
- Animated terminal demo for the README, recorded from real command output (`scripts/record_demo.py`,
  `docs/assets/demo.svg`), with a `--check` mode wired into the tests.

### Changed
- `sdlc phase` points at `sdlc status` when a gate blocks.

## [0.5.3] - 2026-09-17

### Added
- Step-by-step walkthrough in English and Spanish with Mermaid diagrams, a table of which role approves each artifact
  per phase and profile, a gate troubleshooting table and a command cheat sheet.
- Mermaid diagrams in the READMEs and the guides (harness overview, phase gates, approval sequence, repository layout,
  upgrade decisions).
- `docs/sdlc/README.md` in the template: how work flows in the installed repository, everyday commands, a snippet that
  prints the approval matrix from the roster and profile.
- Documentation tests: relative links and anchors resolve, English/Spanish docs come in pairs, Mermaid blocks are valid.

### Changed
- Research documents present the evaluated projects and frameworks directly, without referring to a third-party
  aggregator repository.

## [0.5.2] - 2026-09-17

### Fixed
- Dependabot template sets a 7-day `cooldown` (Semgrep `dependabot-missing-cooldown`), which made the v0.5.1 template fail
  its own `sensors` gate.

### Added
- CI job `template-sensors`: installs the template and runs the shipped Semgrep and gitleaks scanners plus
  `sdlc evidence check` against it before any release.

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
