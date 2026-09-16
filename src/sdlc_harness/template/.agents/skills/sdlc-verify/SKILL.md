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
3. Run the security sensors that apply to the stack (see `references/sensors.md`): SAST, dependency (SCA)
   and license scan, secret scan, IaC/policy scan, container image scan, DAST for exposed endpoints.
4. For user interfaces, verify in a real browser or device and record what was exercised.
5. For performance-sensitive changes, record a measurement against the spec's numbers.
6. Record every finding with its disposition: fixed, accepted (who accepted, why) or false positive (why).
7. Re-run `python3 .harness/sdlc.pyz check`.

A red check is a result to report, never something to hide or skip.
