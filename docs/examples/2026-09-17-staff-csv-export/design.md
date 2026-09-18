---
status: proposed
---
# Design: staff CSV export of bookings

## Context
Implements `spec.md` (AC-1..AC-5) for the admin panel. Existing stack: Next.js app router, PostgreSQL via Prisma,
Auth.js sessions with a `role` claim per studio membership.

## Solution overview
A route handler `GET /api/studios/:studioId/bookings/export` streams `text/csv`. It authorizes the session against the
studio membership, reads bookings with a keyset cursor (1000 rows per page) and writes rows into the response stream.
The admin panel adds an export panel with a date-range picker that links to the endpoint with query parameters.

## Interfaces and contracts
`GET /api/studios/{studioId}/bookings/export?from=YYYY-MM-DD&to=YYYY-MM-DD` -> `200 text/csv` (streamed),
`400` invalid range (more than 366 days, `to` before `from`), `403` not a manager of that studio, `404` unknown studio.
Declared in `api/openapi.yaml`; the contract sensor compares it against the base branch on every pull request.

## Data
No schema change. Read-only query on `booking` filtered by `studio_id` and `starts_at`; uses the existing index
`booking_studio_starts_at_idx`. One row per export appended to `audit_log` (actor, studio, range, row count).

## Deployment and infrastructure
No new infrastructure: same image, same database. Feature flag `staff_csv_export` (default off) gates the UI entry.

## Failure modes and resilience
| Failure | Detection | Mitigation |
|---|---|---|
| Client aborts mid-download | request cancelled metric | stream is cancelled; no partial file is stored |
| Range too large | 400 with a message | UI limits the picker to 366 days |
| Slow query under load | p95 latency alert on the endpoint | keyset pagination, statement timeout 30 s, no shared transaction |
| Audit log write fails | error rate alert | export still succeeds; audit failure is logged and retried asynchronously |

## Observability
Counter `export.requested` and `export.downloaded` with studio id; histogram of rows and duration; error rate alert on
the endpoint; audit entries queryable by studio.

## Rollout and rollback
Enable the flag for the three pilot studios, then all studios after a week. Rollback: turn the flag off; the endpoint
returns 404 when the flag is off, and nothing persists.

## Decisions
| ADR | Title | Status |
|---|---|---|
| - | No ADR: no new technology, service or boundary; streaming CSV from the existing route handler | - |
