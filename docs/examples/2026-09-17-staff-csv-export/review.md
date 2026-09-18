# Review: staff CSV export of bookings

- Reviewer (agent/model or person): review agent, fresh session, read only the diff and the change record
- Fresh context (did not see implementation session): yes
- Verdict: ready-for-human-approval

## Findings
| Severity | Location | Finding | Recommendation |
|---|---|---|---|
| medium | app/api/studios/[studioId]/bookings/export/route.ts:48 | studio membership was checked after the query was built, so an unauthorized request still hit the database | authorize before querying (fixed in commit 9c1f2ab) |
| low | lib/csv.ts:22 | header order differed from the contract example | align with api/openapi.yaml (fixed) |
| low | app/(admin)/bookings/export-panel.tsx:64 | spinner had no accessible label | add `aria-label` (fixed) |

## Checklist
- [x] Acceptance criteria implemented and tested
- [x] Scope limited to plan
- [x] Security (input, authn/authz, secrets, dependencies, privileges)
- [x] Conforms to accepted ADRs / contracts compatible
- [x] Operability (telemetry, flags, rollback)
- [x] Tests meaningful and not flaky
- [x] Verification evidence reproducible

## Not reviewed
Design-system internals (unchanged) and the anonymized staging dataset generator.
