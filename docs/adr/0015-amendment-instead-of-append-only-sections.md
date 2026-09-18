# 0015. Re-approval shows the diff instead of exempting parts of a document

**Status:** Accepted
**Date:** 2026-09-18
**Deciders:** maintainers

## Context and problem
Approval receipts are bound to the SHA-256 of the artifact, so any later edit invalidates them. In a real lifecycle
run this cost three re-approvals of `design.md` for honest, minor additions, and it produced an incentive the harness
should never create: the published artifact digests were left out of `release.md` and recorded elsewhere, precisely so
that its receipt would stay valid. The document describing the release was the one missing the data.

## Decision drivers
The record must stay truthful (high), receipts must keep meaning a human saw the content (high), friction
proportional to the size of the change (medium).

## Options considered
1. Declare append-only sections (for example `## Implementation notes`) whose changes do not invalidate the receipt.
   It removes the friction, but it creates a region of an approved document that nobody approved, and substantive
   content will end up there.
2. `sdlc amend <change> <artifact>`: recover the approved content from git by its hash, show the approver the diff
   since their approval, and record a fresh receipt once they confirm at a terminal.
3. Leave it as it is and rely on guidance.

## Decision
Option 2. Every byte of an approved artifact is still covered by a receipt, and the human sees what changed instead of
re-approving blind. The command refuses to run when standard input is not a terminal, so an agent cannot use it, and
it writes an `amend-reviewed` event into the audit log before the new receipt.

## Consequences
- Positive: no reason is left to keep true information out of an approved document; the audit log shows that a diff
  was reviewed, which a plain re-approval never showed.
- Negative: the approved content must exist in git history for the diff to be recoverable; if it was never committed,
  the command says so and falls back to a normal approval.
