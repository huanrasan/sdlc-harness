# Research and design recommendation

> Versión en español: [../es/investigacion.md](../es/investigacion.md)
> Research cut-off: 2026-09-16.

## 1. What a harness is and why it matters

Harness engineering is the work of surrounding a coding agent with **guides** (what it receives before acting)
and **sensors** (signals it receives after acting so it can self-correct), so that its output is reliable
enough for production software. Birgitta Böckeler (martinfowler.com) classifies these controls as:

| | Computational (deterministic, cheap) | Inferential (LLM, expensive, non-deterministic) |
|---|---|---|
| **Guide (feedforward)** | templates, scaffolding, codemods | `AGENTS.md`, skills, specifications |
| **Sensor (feedback)** | tests, linters, type checkers, scanners, CI | independent review agent, evaluators |

Converging findings:

- **Context is a scarce resource.** OpenAI's Codex harness uses `AGENTS.md` as a short *map* pointing to
  versioned in-repo documentation as the system of record. Anthropic recommends concise instructions and
  progressive loading. The Agent Skills specification formalizes progressive disclosure: metadata first
  (about 100 tokens), then instructions (under 5,000 tokens), then resources on demand.
- **Rules that matter must be deterministic.** Architectural constraints are enforced with linters and
  structural tests, not prose. A repeated mistake becomes a control.
- **Separate generation from evaluation.** Anthropic observes that agents grading their own work skew positive.
  Use an independent evaluator with a clean context, and agree on "done" before implementing.
- **Long tasks: state lives in files.** Plans, progress and hand-off notes live in the repo so a fresh session
  can resume from files alone.
- **Garbage collection.** Periodic passes detect drift between docs and code and prune stale instructions.
- **AI is an amplifier.** DORA 2025 shows AI magnifies existing strengths and weaknesses. Its seven capabilities
  (clear AI stance, healthy data ecosystems, AI-accessible internal data, strong version control, small batches,
  user-centric focus, quality internal platforms) are preconditions the harness should reinforce, not replace.

## 2. Standards that make "any agent" possible

| Standard | Role in the harness | Status (2026-09) |
|---|---|---|
| **AGENTS.md** | Project instructions readable by any agent. The nearest file takes precedence. | Stewarded by the Agentic AI Foundation (Linux Foundation). Adopted by Codex, Copilot, Cursor, Gemini CLI, Jules, Devin, Amp, VS Code and others. |
| **Agent Skills (`SKILL.md`)** | Conditional per-phase knowledge with progressive loading. Required `name` and `description`; `scripts/`, `references/` and `assets/` directories. | Open specification (agentskills.io). `.agents/skills/` is the neutral path read by Codex, Copilot, Cursor and OpenCode; Claude Code, Gemini CLI and Windsurf need a link to their own path. |
| **MCP** | Optional integrations (memory, code intelligence, trackers). | Stewarded by the AAIF. |
| **Git hooks + CI** | Deterministic gates independent of the agent. | Universal. |

**Agent lifecycle hooks** (Claude Code, Codex, Gemini CLI, Cursor) serve equivalent purposes, but each uses a
different event vocabulary and they change often. The harness therefore **does not rely on them to enforce
controls**: git hooks and CI are authoritative, and agent hooks are optional adapters that call the same commands.

## 3. Controls for teams and organizations

| Framework | Contribution to the harness |
|---|---|
| NIST SSDF SP 800-218 and the AI profile SP 800-218A | PO/PS/PW/RV secure development practices; backbone of the controls matrix. |
| SLSA v1.2 (Build + Source tracks), Sigstore, CycloneDX/SPDX SBOM, OpenSSF Scorecard | Supply-chain integrity: mandatory review, protected branches, provenance and signing. |
| OWASP Top 10 for Agentic Applications 2026 and Top 10 for LLM Applications | Risks of the agent itself (goal hijack, tool misuse, privilege abuse, memory poisoning) and of AI features being built. |
| OWASP SAMM / ASVS | Program maturity and verifiable requirements. |
| NIST AI RMF, ISO/IEC 42001, EU AI Act | AI governance: disclosure of AI use, human oversight, traceability and documentation. The harness produces evidence; it **does not certify compliance**. |
| DORA (throughput, instability, rework rate) | Metrics to tell whether the harness improves delivery. |
| Advice process (Harmel-Law), ADRs (Nygard/MADR), decision framework (Natanzon), Tech Radar | Decentralized but documented, advised decisions. |

**Key governance principle:** an agent never approves its own work. Human approval must be enforced by the
platform (CODEOWNERS, branch protection, protected environments), not by a field the agent can edit.

## 4. Reference repository sources: what was used and how

Only the source list of `csalamando/harness-sdlc` was reviewed. None of its code, structure or text was copied.

| Source | Use in this harness |
|---|---|
| Natanzon, *Architectural Decision Framework* | Decision-process ideas (last responsible moment, weighted criteria before options, revisit). **CC BY-NC-SA 4.0, incompatible with MIT**: an original process was written and the work is cited only. |
| Harmel-Law / Fowler, *Scaling Architecture Conversationally* | Advice process in the design skill and the ADR template ("Advice received"). |
| Nygard (ADR), ThoughtWorks Tech Radar | ADR format and lifecycle. Tech Radar is on the roadmap. |
| DeepSeek Harness (MIT) | "Everything is a plugin" approach evaluated. A custom runtime was rejected: the harness must live *inside* the repo and serve existing agents. Declarative extension points (`adapters.toml`, profiles) keep the idea. |
| gentle-ai / engram (MIT) | Confirm multi-agent viability, the value of persistent memory, and "verifying beats generating". In v0.1 memory is versioned files (change records); engram is an optional MCP integration. |
| gortex (Apache-2.0) | MCP code intelligence: recommended optional integration for large repositories. |
| archify (MIT), grip, Penpot | Diagrams, Markdown preview, UX prototyping: out of v0.1 scope, candidate extensions. |

## 5. Architecture recommendation

1. **Agent-agnostic core**: `AGENTS.md` (map, ≤150 lines) + `.agents/skills/` (10 SDLC skills) as the single source.
   `sdlc sync` generates adapters (`CLAUDE.md`, `GEMINI.md`, skill links or copies) from a declarative catalog.
2. **Deterministic gates outside the agent**: a stdlib-only Python `sdlc` CLI that runs identically locally, in
   GitHub Actions, self-managed GitLab or offline runners. Git hooks for fast feedback; CI is authoritative.
3. **Change records as system of record**: `docs/changes/<id>/change.toml` with type, risk, phase and AI
   disclosure, plus per-phase artifacts. The CLI refuses phase transitions without evidence.
4. **Risk-proportional profiles**: `lite`, `standard`, `regulated`, with editable TOML rules. Ceremony scales with
   risk instead of being uniform.
5. **Generator/evaluator separation**: the review skill requires a clean context; final approval is human via the platform.
6. **Cloud-agnostic**: IaC and policy-as-code described by capability (Terraform/OpenTofu, Pulumi, Crossplane, OPA,
   Kyverno) and self-hostable open-source tooling for private or air-gapped clouds.
7. **Continuous improvement**: the `sdlc-maintain` skill performs garbage collection and turns repeated mistakes
   into deterministic controls.

### Accepted trade-offs

- **TOML + stdlib** instead of YAML: zero dependencies, but Python ≥ 3.11 is required.
- **Evidence in files** instead of tracker integrations: works everywhere, but partially duplicates the tracker.
  MCP integrations remain optional.
- **Symlinks by default**: no copy drift, but Windows needs developer mode. A `copy` mode with drift detection exists.
- **Gates validate shape, not quality**: they check that evidence exists and is complete. The independent reviewer
  and the approving human judge quality.

## 6. Suggested roadmap

- v0.2 (done): package + vendored zipapp; approval receipts verified by the platform; audit log; semantic gates; roster and CODEOWNERS.
- v0.3 (done): real CI sensors (SBOM, signing, provenance, SAST, IaC, test-first order); executable architecture rules and API contract diff.
- v0.4 (done): discovery/product, UX, data, FinOps, feedback and retirement phases; organization policies with expiring exceptions and memory; traceability and DORA reports.
- v0.5: `sdlc upgrade`, releases and per-agent plugin packaging; cross-agent skill evals; brownfield adoption.

## 7. Sources

Full list with URLs in [ACKNOWLEDGEMENTS.md](../../ACKNOWLEDGEMENTS.md).
