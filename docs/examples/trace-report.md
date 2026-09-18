# sdlc report: trace

## Change

| id | type | risk | phase | scopes | ai_assisted | release |
|---|---|---|---|---|---|---|
| 2026-09-17-staff-csv-export | feature | medium | done | ui, api | True | 1.5.0 |

## Gaps

_none_

## Acceptance criteria

| id | criterion | tests | result | evidence |
|---|---|---|---|---|
| AC-1 | Given a signed-in manager, when they choose a date range and select export, then a CSV downloads with one row per booking and the columns date, time, customer, service, status, payment reference | `test_export_returns_csv_for_range` | pass | `test_export_returns_csv_for_range` |
| AC-2 | Given a manager of studio A, when they export, then the file contains only bookings of studio A | `test_export_is_scoped_to_studio` | pass | `test_export_is_scoped_to_studio` |
| AC-3 | Given a user without the manager role, when they call the export endpoint, then the response is 403 and no data is returned | `test_export_requires_manager_role` | pass | `test_export_requires_manager_role` |
| AC-4 | Given a range with no bookings, when they export, then the CSV contains only the header row and the UI shows the empty state | `test_export_empty_range`, `export-panel.spec.ts` | pass | `test_export_empty_range`, `export-panel.spec.ts` |
| AC-5 | Given a range of 12 months with 50k bookings, when they export, then the download starts in under 2 s and streams to completion | `test_export_streams_large_range` | pass | `test_export_streams_large_range`: first byte 780 ms, 50k rows in 9.4 s, peak memory 96 MB |

## Threats

_none_

## ADRs

_none_

## Approvals

| artifact | approver | role | approved_at | state |
|---|---|---|---|---|
| docs/changes/2026-09-17-staff-csv-export/discovery.md | pat | product-owner | 2026-09-17T23:20:24+00:00 | valid |
| docs/changes/2026-09-17-staff-csv-export/spec.md | pat | product-owner | 2026-09-17T23:20:24+00:00 | valid |
| docs/changes/2026-09-17-staff-csv-export/design.md | tomas | tech-lead | 2026-09-17T23:20:25+00:00 | valid |
| docs/changes/2026-09-17-staff-csv-export/release.md | rita | release-manager | 2026-09-17T23:20:26+00:00 | valid |

## Commits

| sha | date | subject |
|---|---|---|
| c8fdc72278 | 2026-09-17T18:20:24-05:00 | chore: harness and change record |

