# 0008. Executable architecture rules and API contract compatibility

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
ADRs describe structure (layers, dependencies) and public contracts, but nothing prevented code from drifting away from
them. Agents in particular add convenient imports across layers and change payloads without noticing consumers.

## Decision drivers
Language neutrality (high), zero dependencies (high), actionable messages linked to ADRs (medium), false-positive rate (medium).

## Options considered
1. Recommend language-specific tools only (ArchUnit, dependency-cruiser, import-linter, oasdiff).
2. Built-in, regex-based import extraction for common languages with layer rules in `.harness/architecture.toml` citing
   ADRs; built-in OpenAPI 3.x / AsyncAPI 2.x-3.x diff with direction-aware schema rules and a Semantic Versioning policy
   (breaking changes require a major `info.version` bump); a minimal stdlib YAML reader for contracts.
3. Option 2 plus a full YAML/compiler front-end.

## Decision
Option 2. Language-specific tools remain recommended for deeper analysis and can feed SARIF into the evidence gate.

## Consequences
- Positive: one mechanism for polyglot repositories; violations cite the ADR; breaking contract changes become explicit
  decisions.
- Negative: dynamic imports, reflection and generated code are not seen; the YAML reader rejects anchors, aliases and tags
  (use JSON for such contracts). It was validated against PyYAML on public OpenAPI/AsyncAPI documents, including the
  GitHub REST API description. `oneOf`/`anyOf` schemas are not compared deeply.
