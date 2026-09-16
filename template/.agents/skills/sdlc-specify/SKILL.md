---
name: sdlc-specify
description: Write or refine a change specification with testable acceptance criteria and non-functional requirements. Use in the spec phase, when requirements are vague, or before designing or coding a feature or fix.
license: MIT
metadata:
  harness-phase: spec
---
# Specify

Goal: a `spec.md` that a different engineer (or agent) could implement and verify without asking you.
Describe the problem and the outcome, not the solution.

## Steps

1. Restate the problem, the users affected and the measurable outcome. Link the issue/ticket.
2. Ask clarifying questions for every ambiguity that changes behaviour. Batch them; do not guess.
   Record answers in the spec's "Decisions and clarifications" section.
3. Write acceptance criteria as Given/When/Then (or EARS: "When <trigger>, the system shall <response>").
   Each criterion must be observable by an automated test or a named manual check.
4. Capture non-functional requirements that apply, with numbers: latency/throughput, availability,
   data classification and residency, retention, accessibility, compliance obligations, cost ceiling,
   deployment target (public cloud, private cloud, on-prem, hybrid) and portability constraints.
5. List explicit out-of-scope items and open risks.
6. For a `fix`: include reproduction steps, expected vs actual behaviour and the suspected root cause.

## Quality bar

- No acceptance criterion uses "fast", "secure", "user-friendly" without a measurable definition.
- Every criterion maps to at least one planned test later (`plan.md`).
- `status: proposed` in the frontmatter. Humans approve through the pull request.

Template: `docs/sdlc/templates/spec.md`.
