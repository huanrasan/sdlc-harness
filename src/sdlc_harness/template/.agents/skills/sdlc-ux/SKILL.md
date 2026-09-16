---
name: sdlc-ux
description: Design user-facing flows, screen states, accessibility (WCAG 2.2 AA) and validation for changes with a user interface. Use in the design phase when the change declares the ui scope, or when creating or modifying screens, components or user journeys.
license: MIT
metadata:
  harness-phase: design
---
# UX design

Goal: `ux.md` that makes every user-visible state explicit and accessible before implementation.

## Steps

1. Map user flows to acceptance criteria (AC-n) from `spec.md`.
2. For each screen or component, define empty, loading, error and success states (write `n/a` with reason when
   a state cannot occur). Link the design source (design tool file, design-system component, prototype).
3. Reuse the design system: existing components and tokens first; new components need a reason.
4. Walk the WCAG 2.2 AA checklist and tick only what the design actually satisfies. Unchecked items block the gate.
5. Plan content: copy, localization, formats and right-to-left support where relevant.
6. Validate cheaply (prototype walkthrough, usability test with 3-5 users, analytics on the current flow) and record findings.
7. During implementation, verify states and accessibility in a real browser or device (automated axe-style checks
   plus keyboard and screen-reader spot checks) and record it in `verification.md`.
