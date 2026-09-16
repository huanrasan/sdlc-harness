# 0006. Approval receipts bound to content and verified by the VCS platform

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
v0.1 relied on CODEOWNERS approval of the whole pull request. It could not prove *which* artifact a person approved,
did not invalidate approvals when an artifact changed later, and gave agents no deterministic signal that a human gate
was pending. Anyone (including an agent) can write a local approval record, so local evidence alone is not trustworthy.

## Decision drivers
Integrity of approvals (high), no key management (high), works on GitHub and GitLab including self-managed (high),
separation of duties (medium).

## Options considered
1. Platform approval only (v0.1).
2. Receipts in the repository with the SHA-256 of the approved artifact, role and approver, plus CI verification against
   the platform API (identity, approved commit contains the same content and the receipt, role membership,
   separation of duties). Hash-chained, append-only audit log per change.
3. Option 2 plus Sigstore signatures on every receipt.

## Decision
Option 2. Option 3 remains a possible extension for organizations with a Sigstore instance.

## Consequences
- Positive: editing an approved artifact invalidates the approval immediately (locally and in CI); approvals are
  attributable to roles; agents are blocked until a human acts; no keys to manage.
- Negative: GitLab approvals carry no commit, so the project must enable "Remove all approvals when commits are added".
  Team membership checks need a token with organization read access. The audit log is tamper-evident, not tamper-proof:
  its protection comes from git history plus the append-only check against the base branch in CI.
