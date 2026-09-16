---
name: sdlc-design
description: Produce a technical design, architecture decision records and a threat model. Use in the design phase, when choosing between technologies or patterns, changing a public contract, a data model, infrastructure, or a security boundary.
license: MIT
metadata:
  harness-phase: design
---
# Design

Goal: make the important decisions explicit, reversible where possible, and reviewed by the people affected.

## Steps

1. Read `spec.md`, existing ADRs in `docs/adr/` and the architectural principles (if the repo has them).
   Do not contradict an `Accepted` ADR silently: propose a superseding ADR instead.
2. Write `design.md`: context, components and responsibilities, interfaces/contracts, data model and
   migrations, deployment topology, failure modes, observability, rollout and rollback.
3. For each significant decision, follow `references/decision-process.md` and write an ADR in
   `docs/adr/NNNN-kebab-title.md` with `**Status:** Proposed`. Reference it in `change.toml` `adrs`.
4. When required by the profile (or when data, identities or network boundaries change), write
   `threat-model.md` following `references/threat-modeling.md`.
5. Portability: keep provider-specific services behind an interface or record the lock-in trade-off in the ADR.
   Describe infrastructure as code (Terraform/OpenTofu, Pulumi, Crossplane, Helm, etc.) as expected
   artefacts; policy-as-code (OPA/Conftest, Kyverno, Checkov) for guardrails.
6. Make structural decisions executable: add or update layers and rules in `.harness/architecture.toml`
   citing the ADR, and register API contracts (OpenAPI/AsyncAPI) in `harness.toml [contracts]`.
7. List who must give advice (owning teams, security, platform, data) in the ADR. Seeking advice is
   required; consensus is not. The accountable human decides.

## Anti-patterns

- A single option presented as a decision. Always compare at least two real alternatives plus "do nothing".
- Criteria invented after picking the winner.
- Diagrams that disagree with the text. Keep one source per view.
