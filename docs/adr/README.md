# Architecture Decision Records (harness)

Decisions about the harness itself. ADRs are written in English only to keep a single source of truth;
summaries in Spanish are in [docs/es/investigacion.md](../es/investigacion.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-agent-agnostic-core.md) | Use AGENTS.md and Agent Skills as the agent-agnostic core | Accepted |
| [0002](0002-deterministic-gates-outside-agent.md) | Enforce gates with git hooks and CI, not agent hooks | Accepted |
| [0003](0003-stdlib-python-cli-toml.md) | Stdlib-only Python CLI with TOML configuration | Superseded by 0005 |
| [0004](0004-risk-proportional-profiles.md) | Risk-proportional profiles and file-based change records | Accepted |
| [0005](0005-package-with-vendored-zipapp.md) | Python package with a vendored zipapp | Accepted |
| [0006](0006-approval-receipts-verified-by-platform.md) | Approval receipts bound to content and verified by the VCS platform | Accepted |
| [0007](0007-sensor-evidence-via-sarif-and-cyclonedx.md) | Sensor evidence via SARIF and CycloneDX, policy in the harness | Accepted |
| [0008](0008-executable-architecture-and-contract-compatibility.md) | Executable architecture rules and API contract compatibility | Accepted |
| [0009](0009-lifecycle-coverage-with-scopes.md) | Full lifecycle coverage with conditional scopes | Accepted |
| [0010](0010-organization-policy-and-memory.md) | Vendored organization policy with deviations, and reviewed memory | Accepted |
| [0011](0011-visibility-from-repository-data.md) | Visibility reports computed from repository data | Accepted |
| [0012](0012-distribution-and-upgrades.md) | Distribution channels and manifest-based upgrades | Accepted |
| [0013](0013-cross-agent-behavioural-evals.md) | Cross-agent behavioural evals graded on repository state | Accepted |
| [0014](0014-approval-integrity-for-one-maintainer.md) | A verified commit signature replaces the platform review for a single maintainer | Accepted |
| [0015](0015-amendment-instead-of-append-only-sections.md) | Re-approval shows the diff instead of exempting parts of a document | Accepted |
