---
status: proposed
---
# Spec: staff CSV export of bookings

## Problem and outcome
Studio managers cannot get their own bookings data, so support exports it by hand. Outcome: a manager downloads the
bookings of a chosen date range as a CSV without contacting support. Issue: STUDIO-482.

## Acceptance criteria
| ID | Given / When / Then | Verified by |
|---|---|---|
| AC-1 | Given a signed-in manager, when they choose a date range and select export, then a CSV downloads with one row per booking and the columns date, time, customer, service, status, payment reference | `test_export_returns_csv_for_range` |
| AC-2 | Given a manager of studio A, when they export, then the file contains only bookings of studio A | `test_export_is_scoped_to_studio` |
| AC-3 | Given a user without the manager role, when they call the export endpoint, then the response is 403 and no data is returned | `test_export_requires_manager_role` |
| AC-4 | Given a range with no bookings, when they export, then the CSV contains only the header row and the UI shows the empty state | `test_export_empty_range` |
| AC-5 | Given a range of 12 months with 50k bookings, when they export, then the download starts in under 2 s and streams to completion | `test_export_streams_large_range` |

## Non-functional requirements
| Concern | Requirement (with numbers) |
|---|---|
| Performance | first byte < 2 s for 50k rows; streamed, memory use < 128 MB |
| Availability / resilience | export failure must not affect booking creation; no long-lived database transaction |
| Security and data classification | bookings are confidential; customer name and payment reference are personal data; manager role required; every export is audit-logged |
| Compliance / residency / retention | export files are not stored server-side; audit entries kept 24 months |
| Deployment target (public, private, on-prem, hybrid) | same container image as the app, any cloud; no new managed service |
| Cost | no new infrastructure; egress estimated < 2 GB/month |

## Out of scope
Scheduled email reports, Excel formatting, charts, cross-studio exports, export of customer contact details.

## Decisions and clarifications
| Question | Answer | Who |
|---|---|---|
| Which timezone for dates? | Studio local timezone, ISO 8601 with offset | pat |
| Include cancelled bookings? | Yes, with status column so they can filter | pat |
| Customer email in the file? | No: not needed for reconciliation, reduces exposure | dana |

## Risks and open questions
Large ranges could be slow on studios with heavy history; mitigated by streaming and a 12-month maximum range.
