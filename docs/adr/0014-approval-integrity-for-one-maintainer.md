# 0014. A verified commit signature replaces the platform review for a single maintainer

**Status:** Accepted
**Date:** 2026-09-18
**Deciders:** maintainers

## Context and problem
`.harness/roster.toml` offers `separation_of_duties = false` for a repository with one maintainer, but
`sdlc approvals verify` still required an approving review on the pull request from the person named in the receipt,
and GitHub does not let anyone approve their own pull request. Taking a real application through the whole lifecycle
(field feedback, 2026-09-18) showed the consequence: the `harness` check was red on every pull request that added a
receipt, and the change was merged as an administrator with the deviation written down in prose. A documented mode
that cannot pass is worse than no mode: it teaches people that the red check is normal.

## Decision drivers
Approval integrity (high), reachability of every documented mode (high), agent cannot forge an approval (high),
setup cost for a single maintainer (medium).

## Options considered
1. Accept the local receipt as sufficient when `separation_of_duties = false`. Simple, but the receipt is a file in
   the repository: the same agent that wrote the change can write it, and only the convention in the skills stops it.
2. Require a commit signature the platform verifies on the commit that adds the receipt.
3. Keep the platform requirement and document that this mode needs a second identity (bot or GitHub App) to open the
   pull requests.

## Decision
Option 2. With `separation_of_duties = false`, when there is no platform approval for the receipt's approver,
`approvals verify` accepts the receipt if the platform confirms that the commit introducing it carries a verified
signature and that the signer is the approver named in the receipt. A platform review is still accepted when there is
one, and with separation of duties on, nothing changes.

## Consequences
- Positive: the single-maintainer mode is reachable; the approval still binds to an identity the platform checked
  against registered keys, which an agent writing files cannot produce; the failure message says exactly how to fix it.
- Negative: the maintainer must set up commit signing, and a leaked signing key weakens the control to the strength of
  that key. Teams with more than one person should leave separation of duties on, which is still the default.
