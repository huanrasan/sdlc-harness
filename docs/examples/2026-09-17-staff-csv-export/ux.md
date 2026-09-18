# UX: staff CSV export of bookings

## User flows
Manager opens Bookings in the admin panel, selects a date range (default: last 7 days), selects Export CSV and the
browser downloads the file. Covers AC-1 and AC-4; the role check behind AC-3 hides the control for non-managers.

## Screens and states
| Screen / component | Empty | Loading | Error | Success | Design reference |
|---|---|---|---|---|---|
| Export panel (Bookings) | "No bookings in this range" with the export still available (header-only CSV) | button shows a spinner and is disabled while the download starts | inline message "Export failed, try again" with a retry action; keeps the chosen range | browser download starts, toast "Export started" | design-system/components/DateRangePicker, Button |
| Range picker | n/a: always has a default range | n/a: local state | invalid range message under the field ("maximum 12 months") | selected range echoed as text for screen readers | design-system/components/DateRangePicker |

## Accessibility (WCAG 2.2 AA)
- [x] Keyboard operable, visible focus, logical order
- [x] Contrast ratios and non-color cues
- [x] Labels, names and roles for assistive technologies
- [x] Error identification and recovery
- [x] Responsive / zoom to 200% without loss
- [x] Motion and timing respect user preferences

## Content and localization
Labels and the empty state are translated (en, es); dates follow the studio locale; CSV header stays in English so
spreadsheets match the API contract.

## Validation
Prototype tested with four managers from the pilot studios: all completed the export unaided; two expected the range to
default to "last week", which is now the default. Screen-reader pass with VoiceOver on the panel and picker.
