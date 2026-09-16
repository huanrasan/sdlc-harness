---
name: sdlc-operate
description: Make a change operable and learn from production - observability, SLOs, runbooks, post-release verification, incident response and blameless postmortems. Use in the operate phase, after a release, during an incident, or when writing a runbook or postmortem.
license: MIT
metadata:
  harness-phase: operate
---
# Operate

## After a release

1. Verify the success metrics and health signals defined in `release.md` against real telemetry.
2. Confirm logs, metrics and traces exist for the new paths (OpenTelemetry is the portable default) and that
   alerts are tied to SLOs, not to raw resource usage.
3. Write or update `runbook.md`: purpose, dependencies, dashboards, alerts and their meaning, diagnostic
   commands, safe mitigation steps, escalation contacts, and how to roll back.
4. Move the change to `done` when the post-release window closes without rollback triggers.

## During an incident (assist, do not command)

- Help triage severity, gather timeline facts and draft status updates. Humans own mitigation decisions in production.
- Prefer reversible mitigations (rollback, flag off, scale) over live code changes.

## After an incident

Write a blameless postmortem (`docs/sdlc/templates/postmortem.md`): impact, timeline, contributing factors,
what went well, action items with owners and due dates. Feed systemic learnings back into the harness via
`sdlc-maintain` (a new test, lint rule, skill instruction, or ADR).
