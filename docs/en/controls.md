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
| C5 | Tests and automated analysis of code | `verification.md`; SARIF evidence (SAST, secrets, IaC) with severity policy | Gate + CI (`evidence check`) | PW.7, PW.8 | OWASP ASVS |
| C6 | Secrets never committed | gitleaks job; agent non-negotiables | CI | PS.1, PW.5 | OWASP Agentic ASI03 |
| C7 | Third-party components assessed | SCA SARIF + CycloneDX SBOM with license deny list; expiring exceptions | CI (`evidence check`) | PW.4, RV.1 | SLSA; OpenSSF Scorecard |
| C8 | Independent review; generator is not the evaluator | `review.md` semantic gate (fresh context, verdict) + human receipt verified against platform review | Gate + CI (`approvals verify`) | PW.7 | SLSA Source track (review); Anthropic evaluator pattern |
| C9 | Human oversight of AI output and AI-use disclosure | `ai_assisted` field; approval receipts by authorized roles; separation of duties | Gate + CI (`approvals verify`) | PO.2 | EU AI Act human oversight; NIST AI RMF Govern; ISO/IEC 42001 |
| C10 | Protected harness and pipeline configuration | CODEOWNERS generated from roster for `harness.toml`, `.harness/`, `.agents/`, workflows; `codeowners --check` | CI + **Platform** | PO.3, PO.5, PS.1 | OWASP Agentic ASI04 (supply chain) |
| C11 | Release integrity: SBOM, signing, provenance | `sdlc-release` workflow: SBOM + license policy, SLSA provenance and SBOM attestations, keyless signatures, protected environment | CI + **Platform** | PS.2, PS.3 | SLSA Build L2/L3; Sigstore; CycloneDX |
| C12 | Safe rollout and rollback | `release.md` rollout/rollback; protected environments | Gate + **Platform** | - | DORA change failure rate |
| C13 | Operability and incident learning | `runbook.md`; postmortem template | Gate by profile/risk | RV.2, RV.3 | Google SRE |
| C14 | Untrusted input to agents (prompt/goal injection) | AGENTS.md non-negotiable; least-privilege agent config | Guidance + agent settings | PO.5 | OWASP Agentic ASI01, ASI02, ASI06 |
| C15 | Destructive actions need human confirmation | AGENTS.md non-negotiable; IaC apply by humans | Guidance + **Platform** (environment protection) | PO.5 | OWASP Agentic ASI02, ASI05, ASI10 |
| C16 | Instruction and documentation drift controlled | `sdlc check` (skills index, adapters, AGENTS.md size); `sdlc-maintain` | CI + scheduled task | PO.3 | Harness engineering "garbage collection" |
| C17 | Approval integrity: approvals bound to exact content, attributable and tamper-evident | `approvals.toml` SHA-256 receipts; hash-chained `audit.jsonl`; append-only check against base | Gate + CI | PS.1, PO.2 | SLSA Source track; ISO/IEC 42001 records |
| C18 | Test integrity: tests precede behaviour changes and are not weakened | `sdlc tdd`: test-first ordering; skip/only markers and deleted tests; human waivers by trailer | CI (`check --base`) | PW.8 | OWASP Agentic ASI01/ASI10 (goal drift) |
| C19 | Architecture conformance | `.harness/architecture.toml` layer rules citing ADRs | Gate + CI | PW.1, PW.2 | Architecture fitness functions |
| C20 | API compatibility | OpenAPI/AsyncAPI breaking-change detection with SemVer policy | CI (`check --base`) | PW.1 | Semantic Versioning |
| C21 | Product value validated before building and after release | `discovery.md` metrics and go decision; `outcome.md` results and decision | Gate | PO.1 | DORA user-centric focus |
| C22 | Privacy and data protection by design | `data.md` classification, retention, privacy impact; approval for personal data | Gate + approvals | PO.1, PW.1 | GDPR-style DPIA; ISO/IEC 27701 |
| C23 | AI system risk management | `ai-risk.md` risks, evaluations with thresholds, human oversight, monitoring | Gate + approvals | PW.1 (SP 800-218A) | NIST AI RMF Map/Measure/Manage; EU AI Act; OWASP LLM Top 10 |
| C24 | Organization policy conformance with governed deviations | vendored `policy.toml` with hash lock; expiring deviations by authorized roles | Gate + CI | PO.1, PO.3 | ISO/IEC 42001 controls; internal audit |
| C25 | Memory integrity and provenance | reviewed memory files; secret scanning; review dates; read-mostly MCP tools | Gate + PR review | PO.5 | OWASP Agentic ASI06 |
| C26 | Measurement and continuous improvement | `report trace\|flow\|dora`; iteration review | CI (weekly) | PO.4 | DORA metrics |
| C27 | Safe decommissioning | `retirement.md` consumers, sunset, data disposition, credential revocation | Gate | PS.3, RV.2 | - |
| C28 | Harness supply chain: signed, reproducible, reviewable updates | deterministic `sdlc.pyz`; release SBOM, SLSA provenance, keyless signatures; manifest-based upgrades with explicit conflicts | CI + release | PS.2, PS.3 | SLSA; Sigstore |
| C29 | Agent conformance measured, not assumed | behavioural evals per agent and version graded on repository state; graders tested against simulated agents | On demand + CI (graders) | PO.4, PW.7 | OWASP Agentic ASI01, ASI02, ASI10; NIST AI RMF Measure |

## Platform configuration checklist

- Branch protection on the default branch: require pull request, required status checks (`sdlc-gates`),
  require review from Code Owners, dismiss stale approvals, no force push.
- `CODEOWNERS` generated by `sdlc codeowners` from `.harness/roster.toml`.
- A token able to read reviews and team membership for `sdlc approvals verify` (`SDLC_APPROVALS_TOKEN`); on GitLab, enable "Remove all approvals when commits are added".
- Protected deployment environments with required human reviewers for production.
- Signed commits or verified identity where your organization requires it.
- Agent credentials: least privilege, short-lived tokens, no production write access by default.
- Pin CI actions/images by digest; mirror them internally for private or air-gapped clouds.
