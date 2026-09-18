# Glossary

> Versión en español: [../es/glosario.md](../es/glosario.md)
> Terms are also available from the terminal: `sdlc explain <term>`.

## The core loop

| Term | Meaning |
|---|---|
| **Harness** | Everything around the agent that makes its output reliable: guides it reads before acting, sensors that check after it acts, gates that stop work without evidence, and human approvals. |
| **Guide (feedforward)** | Information the agent reads before acting: `AGENTS.md`, skills, memory, templates. Increases the chance of being right the first time. |
| **Sensor (feedback)** | A check after the fact: tests, linters, scanners, test-first and weakened-test history checks, layer rules, contract compatibility. |
| **Gate** | The condition for moving to the next phase: required evidence exists, is internally consistent and, where the profile says so, is approved by a human. Runs in `sdlc check`, git hooks and CI. |
| **Computational vs inferential control** | Computational controls are deterministic and cheap (a test, a linter). Inferential ones use a model (a review agent) and are slower and non-deterministic. The harness prefers computational controls for anything that must block. |

## Work and evidence

| Term | Meaning |
|---|---|
| **Change record** | A folder `docs/changes/<id>/` with `change.toml` plus the artifacts for the phases completed. It is the system of record for one change. |
| **Phase** | `discover, spec, design, plan, implement, verify, review, release, operate, done`. Each produces evidence and ends in a gate. |
| **Change type** | `fix`, `feature`, `architecture`, `retirement`. Decides which artifacts the profile requires. |
| **Risk** | `low`, `medium`, `high`, declared per change. Raises how much evidence and how many approvals are required. |
| **Scope** | A tag on a change (`ui`, `api`, `data`, `personal-data`, `infra`, `ai`) that switches on conditional artifacts such as `ux.md`, `data.md`, `cost.md` or `ai-risk.md`. |
| **Artifact** | A Markdown file in the change record (`spec.md`, `design.md`, ...) with a template and semantic checks. |
| **Semantic gate** | A check on the meaning of the evidence, not only its presence: every criterion traced to a test, every threat with a control, every metric measured. |
| **Acceptance criterion (`AC-n`)** | A testable statement of expected behaviour, written Given/When/Then or EARS. |
| **Threat (`T-n`)** | A risk identified in the threat model, which must have a verifiable control. |
| **Evidence** | Scanner output in standard formats (SARIF findings, CycloneDX SBOM) under `sdlc-evidence/`, plus the artifacts. |
| **Audit log** | `audit.jsonl` per change: creation, approvals, phase transitions and blocked attempts, hash-chained and append-only. |

## People and authority

| Term | Meaning |
|---|---|
| **Roster** | `.harness/roster.toml`: who holds each role, which roles may approve what, and extra CODEOWNERS entries. |
| **Role** | `product-owner`, `tech-lead`, `architect`, `security`, `release-manager`, `sre`, `platform`, `ux-lead`, `data-steward`, `finops`. One person may hold several. |
| **Authority matrix** | The `[authority]` table mapping artifact to the roles that may approve it. |
| **Approval receipt** | An entry in `approvals.toml` with the SHA-256 of the approved artifact, the approver and their role. Editing the artifact voids it. |
| **Separation of duties** | The rule that an approver may not have authored the change; enforced in CI against platform data. Turned off for a single maintainer, where a verified commit signature replaces the platform review. |
| **Amendment** | Re-approving an artifact after reading the diff since the last approval (`sdlc amend`). It exists so that protecting a receipt is never a reason to leave true information out of a document. |
| **Proposal** | A deviation or exception written by an agent with an empty approver: recorded and visible in `sdlc check`, but suppressing nothing until a human with an authorized role approves it. |
| **Open result (`blocked` / `pending`)** | A verification result that names an owner and a reason for a criterion that honestly cannot be verified yet. The record stays truthful; the gate stays red. |
| **CODEOWNERS** | The platform file, generated from the roster, that forces review by the right people. |

## Configuration and policy

| Term | Meaning |
|---|---|
| **Profile** | `lite`, `standard`, `regulated` or your own: the rules that decide which artifacts and approvals apply per type, risk and scope, plus sensor levels and required evidence. |
| **Rule** | One entry in a profile: artifact, producing phase, applicable types, minimum risk, optional scopes, and whether it needs an approval receipt. |
| **Organization policy** | `policy.toml` in a shared repository, vendored into `.harness/org/` with a hash lock. Its `[require]` minimums cannot be weakened by a project. |
| **Deviation** | A time-boxed, approved exception to an organization policy minimum, in `.harness/deviations.toml`. |
| **Exception** | A time-boxed, security-approved exception to a scanner finding or a denied licence, in `.harness/exceptions.toml`. |
| **Waiver** | A commit trailer (`TDD-Waiver:`, `Test-Waiver:`) with which a human justifies a history-sensor exception; it is recorded, not hidden. |

## Distribution and integration

| Term | Meaning |
|---|---|
| **`AGENTS.md`** | The open standard file every supported agent reads: project map, workflow and non-negotiables. |
| **Skill (`SKILL.md`)** | Conditional knowledge in the Agent Skills format, loaded only when its "use when" matches. One per phase or concern. |
| **Adapter** | The generated file or link that makes the canonical guides visible to an agent (`CLAUDE.md`, `GEMINI.md`, `.claude/skills`), produced by `sdlc sync`. |
| **Vendored CLI** | `.harness/sdlc.pyz`: the harness itself, committed to the repository so hooks and CI run it with no install and no network. |
| **Manifest** | `.harness/manifest.toml`: hashes of harness files as installed, used by `sdlc upgrade` to keep your customizations. |
| **MCP server** | `sdlc mcp`: exposes read-mostly harness tools (memory, status, check, trace, explain) to any MCP client. |
| **Memory** | Curated Markdown entries in `docs/memory/` (decisions, lessons, conventions, pitfalls) that agents search before starting. |

## Metrics

| Term | Meaning |
|---|---|
| **Traceability report** | `sdlc report trace`: criterion to planned test to verification result to approval to commits, with gaps listed. |
| **Flow report** | `sdlc report flow`: lead time, hours per phase, gate blocks, approval waits, share of AI-assisted changes. |
| **DORA report** | `sdlc report dora`: deployment frequency, lead time, change failure rate, recovery time and rework rate, using release tags as the deployment proxy. |
