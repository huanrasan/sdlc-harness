# Plan: staff CSV export of bookings

## Traceability
| Requirement / threat | Test(s) | Type |
|---|---|---|
| AC-1 | `test_export_returns_csv_for_range` | integration |
| AC-2 | `test_export_is_scoped_to_studio` | integration |
| AC-3 | `test_export_requires_manager_role` | integration |
| AC-4 | `test_export_empty_range`, `export-panel.spec.ts` | integration, e2e |
| AC-5 | `test_export_streams_large_range` | performance |

## Tasks
| # | Task | Done when (command or check) | Depends on | Status |
|---|---|---|---|---|
| 1 | Contract: add the export operation to api/openapi.yaml | `pnpm test:contract` passes and `sdlc contracts --base origin/main` reports no breaking change | | done |
| 2 | Route handler with authorization and validation | `pnpm vitest run export` covers AC-1..AC-4 | 1 | done |
| 3 | Keyset streaming for large ranges | `pnpm vitest run export.stream` passes with 50k rows under 2 s first byte | 2 | done |
| 4 | Audit log entry per export | `pnpm vitest run export.audit` passes | 2 | done |
| 5 | Export panel and range picker behind the flag | `pnpm playwright test export-panel` passes | 2 | done |
| 6 | Telemetry and alert for the endpoint | dashboard shows `export.requested` in staging | 2 | done |

## Environments, data and access
Local: Docker Compose PostgreSQL with seeded bookings. Staging: anonymized dataset (no production personal data).
Performance task uses a generated 50k-row dataset.

## Rollback per migration / infrastructure step
No migration. Feature flag `staff_csv_export` off restores previous behaviour immediately.

## Deviations
| Date | Change to plan | Reason |
|---|---|---|
| 2026-09-17 | Added task 6 (telemetry) before implementation | success metrics need the `export.downloaded` event from day one |
