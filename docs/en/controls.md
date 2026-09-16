# Controls matrix

> Versión en español: [../es/controles.md](../es/controles.md)

How harness mechanisms map to recognized frameworks. Use it as a starting point for your own control
mapping; it is **not** a compliance certification. "Platform" means configuration on the VCS/CI system that
the harness documents and `sdlc doctor` checks for, but cannot enforce by itself.

| # | Control | Mechanism | Enforcement | NIST SSDF | Other references |
|---|---|---|---|---|---|
| C1 | Security and non-functional requirements defined before building | `spec.md` NFR table; `sdlc-specify` | Gate (`phase`) | PO.1, PW.1 | ISO/IEC 42001 (AI system requirements) |
| C2 | Design risk analysis and threat modeling | `threat-model.md`; `sdlc-design` references | Gate by profile/risk | PW.1, PW.2 | Threat Modeling Manifesto; OWASP Agentic Top 10 |
| C3 | Significant decisions documented with advice and trade-offs | ADRs + `adrs` in `change.toml` | Gate (architecture) + ADR format check | PW.2 | Advice process; MADR |
| C4 | Small, traceable changes | `plan.md`; Conventional Commits; `Change:` trailer (regulated) | `commit-msg` hook + CI | PS.1 | DORA small batches; SLSA Source track |
| C5 | Tests and automated analysis of code | `verification.md`; sensors reference | Gate + stack CI jobs | PW.7, PW.8 | OWASP ASVS |
| C6 | Secrets never committed | gitleaks job; agent non-negotiables | CI | PS.1, PW.5 | OWASP Agentic ASI03 |
| C7 | Third-party components assessed | dependency-review / SCA jobs; license review in `sdlc-implement` | CI | PW.4, RV.1 | SLSA; OpenSSF Scorecard |
| C8 | Independent review; generator is not the evaluator | `review.md` from fresh context + human CODEOWNERS approval | Gate + **Platform** | PW.7 | SLSA Source track (review); Anthropic evaluator pattern |
| C9 | Human oversight of AI output and AI-use disclosure | `ai_assisted` field; agents never set `approved`; human approval | Check + **Platform** | PO.2 | EU AI Act human oversight; NIST AI RMF Govern; ISO/IEC 42001 |
| C10 | Protected harness and pipeline configuration | CODEOWNERS on `harness.toml`, `.harness/`, `.agents/`, workflows | **Platform** | PO.3, PO.5, PS.1 | OWASP Agentic ASI04 (supply chain) |
| C11 | Release integrity: SBOM, signing, provenance | `release.md`; `sdlc-release` | Gate + CI jobs (roadmap v0.3 reference jobs) | PS.2, PS.3 | SLSA Build L2/L3; Sigstore; CycloneDX/SPDX |
| C12 | Safe rollout and rollback | `release.md` rollout/rollback; protected environments | Gate + **Platform** | - | DORA change failure rate |
| C13 | Operability and incident learning | `runbook.md`; postmortem template | Gate by profile/risk | RV.2, RV.3 | Google SRE |
| C14 | Untrusted input to agents (prompt/goal injection) | AGENTS.md non-negotiable; least-privilege agent config | Guidance + agent settings | PO.5 | OWASP Agentic ASI01, ASI02, ASI06 |
| C15 | Destructive actions need human confirmation | AGENTS.md non-negotiable; IaC apply by humans | Guidance + **Platform** (environment protection) | PO.5 | OWASP Agentic ASI02, ASI05, ASI10 |
| C16 | Instruction and documentation drift controlled | `sdlc check` (skills index, adapters, AGENTS.md size); `sdlc-maintain` | CI + scheduled task | PO.3 | Harness engineering "garbage collection" |

## Platform configuration checklist

- Branch protection on the default branch: require pull request, required status checks (`sdlc-gates`),
  require review from Code Owners, dismiss stale approvals, no force push.
- `CODEOWNERS` (see `.github/CODEOWNERS.example`).
- Protected deployment environments with required human reviewers for production.
- Signed commits or verified identity where your organization requires it.
- Agent credentials: least privilege, short-lived tokens, no production write access by default.
- Pin CI actions/images by digest; mirror them internally for private or air-gapped clouds.
