---
name: sdlc-implement
description: Implement planned tasks with test-first discipline, small commits and deterministic feedback. Use in the implement phase or whenever writing or modifying production code, infrastructure as code or tests.
license: MIT
metadata:
  harness-phase: implement
---
# Implement

## Loop (one task at a time)

1. Re-read the task in `plan.md` and the relevant acceptance criteria.
2. Explore before editing: find existing patterns, utilities and tests to follow. Match the surrounding style.
3. Write or update a failing test that expresses the criterion. Run it and see it fail for the right reason.
4. Make the smallest change that passes. Run the fast feedback set: formatter, linter, type checker, affected tests.
5. Refactor only within the task's scope while tests stay green.
6. Commit with a Conventional Commit message (add the `Change: <id>` trailer when the profile requires it).
7. Tick the task in `plan.md`.

## Rules

- Surgical changes. No speculative abstractions, no unrelated refactors, no error handling for impossible cases.
- Never weaken a failing check to make progress. Find the root cause or stop and report. CI flags added
  skip/ignore/only markers and deleted test files; only a human may justify one with a `Test-Waiver: <reason>` trailer.
- Test-first is checked from history: commit the test (or test + code) before or with the behaviour change.
  Pure refactors use `refactor:` commits. A `TDD-Waiver: <reason>` trailer is for humans to justify rare exceptions.
- Respect `.harness/architecture.toml`: run `python3 .harness/sdlc.pyz arch` after adding imports across modules.
- API contracts listed in `harness.toml [contracts]` must stay backward compatible; a breaking change needs an ADR
  and a major `info.version` bump (`python3 .harness/sdlc.pyz contracts --base origin/main`).
- Infrastructure: plan/preview before apply (`terraform plan`, `tofu plan`, `pulumi preview`, `helm diff`);
  applying to shared or production environments is a human action.
- Dependencies: prefer existing ones; for a new dependency record license, maintenance status and why it is needed.
- Secrets come from the secret manager or environment at runtime; never from code, fixtures or logs.
- Generated code is your responsibility: read it, test it, and keep it consistent with the codebase.
