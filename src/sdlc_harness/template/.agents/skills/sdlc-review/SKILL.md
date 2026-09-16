---
name: sdlc-review
description: Perform an independent review of a change against its spec, design and quality criteria, from a fresh context. Use in the review phase, when asked to review a pull request or diff, or before merging.
license: MIT
metadata:
  harness-phase: review
---
# Review

Generation and evaluation must be separated: an agent grading its own work in the same context skews positive.
Run this skill in a new session, as a subagent, or with a different model/agent than the implementer.

## Inputs

The diff (`git diff <base>...HEAD`), `spec.md`, `design.md`, ADRs, `plan.md`, `verification.md`.
Do not read the implementer's reasoning or chat history.

## Checklist

1. **Correctness**: each acceptance criterion is implemented and tested; edge cases and error paths are handled.
2. **Scope**: nothing outside the plan; no dead code, debug leftovers, or commented-out tests.
3. **Security**: input validation, authn/authz, secrets handling, injection, logging of sensitive data,
   dependency and permission changes, agent/tool privileges.
4. **Design conformance**: matches accepted ADRs and layering rules; contracts are backward compatible or versioned.
5. **Operability**: logs, metrics, traces, alerts, feature flags, migration and rollback path.
6. **Tests**: meaningful assertions, not coverage padding; flaky patterns (sleeps, order dependence) absent.
7. **Evidence**: `verification.md` claims are reproducible.

## Output

Write `review.md`: verdict (`changes-requested` or `ready-for-human-approval`), findings ranked by severity with
file:line, and what was not reviewed. A human reviewer gives the final approval with a receipt (`sdlc approve`) and a pull request review;
this skill never approves anything. The gate rejects `changes-requested` verdicts, missing fresh context and unchecked items.
