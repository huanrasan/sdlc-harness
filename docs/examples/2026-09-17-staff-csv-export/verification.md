# Verification: staff CSV export of bookings

## Commands run
```text
pnpm lint                 -> 0 problems
pnpm vitest run           -> 148 passed, 0 failed (coverage 84.2%, +1.1%)
pnpm playwright test      -> 12 passed
pnpm test:contract        -> openapi.yaml matches the handler
sdlc contracts --base origin/main -> no breaking change (info.version 1.4.0 -> 1.5.0)
sdlc arch                 -> no layer violations
```

## Acceptance criteria
| ID | Result | Evidence (test name / manual check) |
|---|---|---|
| AC-1 | pass | `test_export_returns_csv_for_range` |
| AC-2 | pass | `test_export_is_scoped_to_studio` |
| AC-3 | pass | `test_export_requires_manager_role` |
| AC-4 | pass | `test_export_empty_range`, `export-panel.spec.ts` |
| AC-5 | pass | `test_export_streams_large_range`: first byte 780 ms, 50k rows in 9.4 s, peak memory 96 MB |

## Security and quality sensors
| Sensor | Tool | Result | Findings |
|---|---|---|---|
| Secrets | gitleaks | pass | 0 |
| SAST | Semgrep p/default | pass | 1 medium, below the high threshold (see disposition) |
| Dependencies / licenses | Trivy + SBOM | pass | 0 vulnerable, no denied licence |
| IaC / policy | n/a: no infrastructure change | n/a | - |
| Container | Trivy image scan | pass | 0 high or critical |

## Findings disposition
| Finding | Disposition (fixed / accepted / false positive) | Rationale | Who |
|---|---|---|---|
| Semgrep: user input concatenated into a log line | fixed | range is now logged as structured fields, not interpolated | tomas |
| Manual review: CSV formula injection (`=cmd`) in customer names | fixed | values starting with `= + - @` are prefixed with an apostrophe | tomas |
