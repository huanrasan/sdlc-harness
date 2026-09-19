---
name: sdlc-verify
description: Run and record objective verification - tests, coverage, static analysis, dependency, secret, container and IaC scans - before review. Use in the verify phase, before claiming work is done, or before opening a pull request.
license: MIT
metadata:
  harness-phase: verify
---
# Verify

Goal: `verification.md` containing evidence, not assertions. "Should work" is not evidence.

## Steps

1. Run the full test suite and the project's quality gates. Paste commands and summarized output
   (pass/fail counts, coverage delta), not screenshots of success.
2. Check every acceptance criterion in `spec.md`: mark it verified with the test name or the manual check performed.
   A criterion that truly cannot be verified yet - it needs a permission you do not have, an environment that does
   not exist - is `blocked` or `pending` with an owner and a reason, as in
   `blocked - owner: rita - needs repository admin to protect the branch`. The gate stays red and the phase does not
   advance, which is correct: the point is that the record says what is true. Never write a result you did not
   observe, and never mark something `n/a` that simply has not been done.
3. Run the security sensors that apply to the stack (see `references/sensors.md`) writing SARIF
   (`sdlc-evidence/<kind>.sarif`) and a CycloneDX SBOM (`sdlc-evidence/sbom.json`), then
   `python3 .harness/sdlc.pyz evidence check`. The profile lists required kinds; `harness.toml [evidence]` sets the
   severity threshold and denied licenses. Never fill in an approver in `.harness/exceptions.toml` yourself:
   write the proposal with `python3 .harness/sdlc.pyz exception propose <rule> <path> --reason "..." --days <n>`,
   which stays pending, suppresses nothing, and appears in `sdlc check` until a security role approves it.
4. For user interfaces, verify in a real browser or device and record what was exercised.
5. For performance-sensitive changes, record a measurement against the spec's numbers.
6. Record every finding with its disposition: fixed, accepted (who accepted, why) or false positive (why).
7. Re-run `python3 .harness/sdlc.pyz check --base origin/<default-branch>` (adds test-first, weakened-test,
   architecture and contract sensors).

A red check is a result to report, never something to hide or skip.
