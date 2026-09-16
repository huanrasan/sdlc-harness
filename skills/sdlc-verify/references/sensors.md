# Verification sensors (examples, pick what fits the stack)

Prefer open-source, self-hostable tools so the same gates run in public cloud, private cloud and air-gapped CI.
These are examples, not endorsements; the organization's approved list wins. The harness only needs their output as
SARIF (`sdlc-evidence/<kind>.sarif`: secrets, sast, sca, iac, container, dast) or CycloneDX JSON (`sdlc-evidence/sbom.json`).

| Concern | Examples |
|---|---|
| Secrets | gitleaks, trufflehog |
| SAST | Semgrep, CodeQL, language linters with security rules (Bandit, gosec, ESLint security plugins) |
| Dependencies (SCA) and licenses | OSV-Scanner, Trivy, Grype, Dependabot/Renovate, dependency-review |
| SBOM | Syft, cdxgen, Trivy (CycloneDX or SPDX output) |
| IaC and policy | Checkov, Trivy config, tfsec, KICS, OPA/Conftest, Kyverno (Kubernetes) |
| Containers | Trivy, Grype, Hadolint |
| DAST | OWASP ZAP |
| Supply chain posture | OpenSSF Scorecard |
| Signing and provenance | Sigstore cosign, SLSA provenance, GitHub/GitLab artifact attestations |
| Architecture fitness | ArchUnit, dependency-cruiser, import-linter, custom structural tests |
| LLM/agent features | promptfoo, garak or equivalent evaluation and red-team suites |
