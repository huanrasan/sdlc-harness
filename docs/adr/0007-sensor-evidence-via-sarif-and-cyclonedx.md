# 0007. Sensor evidence via SARIF and CycloneDX, policy in the harness

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
v0.2 documented security sensors but did not enforce them. Organizations use different scanners (commercial or open
source, hosted or air-gapped), and each scanner has its own severity model, exit codes and suppression format.
Git history also carries signals agents can abuse: skipping or deleting tests, or writing code before tests.

## Decision drivers
Tool neutrality (high), one policy across scanners (high), offline operation (high), auditability of exceptions (medium).

## Options considered
1. Integrate specific scanners in the CLI.
2. Scanners run in CI and only produce standard evidence (SARIF 2.1.0, CycloneDX JSON); `sdlc evidence check`
   applies one policy (required kinds per profile, severity threshold, license deny list, expiring exceptions).
   History sensors (test-first ordering, weakened tests) run in the CLI from git.
3. Rely on each scanner's own exit code.

## Decision
Option 2. Secret findings are treated as critical because secret scanners rarely assign severities.
Test-first and weakened-test checks are heuristics with explicit, human-written waiver trailers.

## Consequences
- Positive: any SARIF/CycloneDX producer plugs in; exceptions are reviewed (CODEOWNERS: security), attributed and expire.
- Negative: severity mapping depends on scanners publishing `security-severity` or SARIF levels; test-first ordering cannot
  prove a test failed first (red), only that it was written before or with the code.
