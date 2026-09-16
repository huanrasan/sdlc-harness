---
name: sdlc-discover
description: Frame a product opportunity before specifying it - problem evidence, target users, value hypothesis, success metrics, options and a go/no-go decision. Use in the discover phase, for new features or initiatives, or when asked "should we build this?".
license: MIT
metadata:
  harness-phase: discover
---
# Discover

Goal: `discovery.md` that lets the product owner decide whether the change is worth building, and defines how
success will be measured after release (`sdlc-outcome` reads these metrics).

## Steps

1. State the problem with evidence (usage data, support tickets, interviews, incidents). Mark assumptions as such.
2. Identify the users affected and the job they are trying to get done.
3. Write the value hypothesis: "We believe that <capability> for <users> will result in <outcome>".
4. Define success metrics with baseline, target and measurement source. Prefer outcome metrics (conversion, time
   saved, errors avoided) over output metrics (features shipped). If a baseline is unknown, plan how to obtain it.
5. Compare at least two options, always including "Do nothing", on value, effort and risk.
6. List the riskiest assumptions and the cheapest way to validate each (prototype, experiment, data query).
7. Propose `Decision: go | no-go | iterate` with the first increment's scope. The product owner approves the
   decision with a receipt; never approve it yourself.

## Anti-patterns

- Jumping to a solution in the problem statement.
- Metrics that cannot be measured with existing telemetry and no plan to add it.
- Treating "no-go" as failure: it is a valid, cheap outcome.
