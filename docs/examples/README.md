# A complete change record, from discovery to outcome

*A real change record produced with the harness. Un change record real producido con el arnés.*

`2026-09-17-staff-csv-export/` is a finished change: a small feature (CSV export of bookings for studio staff) taken
through every phase in the `standard` profile, with real approval receipts and a hash-chained audit log. It was not
written by hand for the documentation: it was created with `sdlc new`, advanced with `sdlc phase` and approved with
`sdlc approve`, and every gate passed (`sdlc check`: 0 errors). Reading it is the fastest way to see how much detail an
artifact actually needs.

`2026-09-17-staff-csv-export/` es un cambio terminado: una funcionalidad chica (exportar reservas a CSV para el personal
del estudio) llevada por todas las fases con el perfil `standard`, con recibos de aprobación reales y log de auditoría
encadenado por hash. No se escribió a mano para la documentación: se creó con `sdlc new`, avanzó con `sdlc phase` y se
aprobó con `sdlc approve`, y todas las compuertas pasaron (`sdlc check`: 0 errores). Leerlo es la forma más rápida de
ver cuánto detalle necesita de verdad cada artefacto.

## What to look at first

| File | Why it is worth reading |
|---|---|
| [change.toml](2026-09-17-staff-csv-export/change.toml) | type, risk, scopes (`ui`, `api`), phase and the AI-use disclosure |
| [discovery.md](2026-09-17-staff-csv-export/discovery.md) | evidence for the problem, three options including "do nothing", measurable success metrics |
| [spec.md](2026-09-17-staff-csv-export/spec.md) | five `AC-n` criteria, each naming the test that verifies it; non-functional requirements with numbers |
| [design.md](2026-09-17-staff-csv-export/design.md) | streaming decision, failure-mode table, flag-based rollback, and why no ADR was needed |
| [ux.md](2026-09-17-staff-csv-export/ux.md) | the four states per screen and a completed WCAG 2.2 AA checklist |
| [plan.md](2026-09-17-staff-csv-export/plan.md) | every criterion traced to a test, tasks with a command as "done when" |
| [verification.md](2026-09-17-staff-csv-export/verification.md) | commands with their real output, scanner findings and their disposition (two were fixed, not accepted) |
| [review.md](2026-09-17-staff-csv-export/review.md) | independent review from a fresh context, with a real authorization bug found before merge |
| [release.md](2026-09-17-staff-csv-export/release.md) | version, digests, SBOM, provenance, rollout thresholds and tested rollback |
| [outcome.md](2026-09-17-staff-csv-export/outcome.md) | measured results against the discovery metrics and an honest `Decision: iterate` |
| [approvals.toml](2026-09-17-staff-csv-export/approvals.toml) | four receipts, each bound to the SHA-256 of the approved file |
| [audit.jsonl](2026-09-17-staff-csv-export/audit.jsonl) | creation, approvals and phase transitions, hash-chained |
| [trace-report.md](trace-report.md) | `sdlc report trace` output: criteria to tests to verification to approvals, with no gaps |
| [status-output.txt](status-output.txt) | `sdlc status` output for the finished change |

## Things this example does on purpose

- **The spec names the test for each criterion.** That is what makes the plan and verification checks pass without
  inventing links afterwards.
- **No ADR.** The design explains why: no new technology, service or boundary. An `architecture` change would require one.
- **Findings were fixed, not excepted.** Exceptions exist for what you truly cannot fix now, with an expiry and a
  security approver; this change had two fixable issues, so they were fixed.
- **The review found a real problem.** An authorization check ran after the query was built. That is the point of
  separating generation from evaluation.
- **The outcome is not a victory lap.** One metric missed its target, and the decision is `iterate` with a follow-up change.

## Reproduce it

```bash
sdlc init /tmp/demo --profile standard          # then fill .harness/roster.toml
sdlc --root /tmp/demo new feature staff-csv-export --risk medium --scope ui,api
# write the artifacts, then advance phase by phase; approvals are run by the humans in the roster
sdlc --root /tmp/demo status
```
