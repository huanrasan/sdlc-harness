# Release: staff CSV export of bookings

| Field | Value |
|---|---|
| Version | 1.5.0 |
| Pipeline run | actions run 118 (tag v1.5.0) |
| Artifacts and digests | app image sha256:6b1f...c204; sbom.cdx.json sha256:2ad9...91be |
| SBOM location | release asset sbom.cdx.json |
| Signature / provenance | cosign bundle per asset; SLSA build provenance attestation |

## Rollout plan
Flag `staff_csv_export` on for the three pilot studios at release, all studios after 7 days. Health signals: endpoint
error rate < 1%, p95 first byte < 2 s, no increase in database CPU. Automatic rollback if the error rate exceeds 5% over
10 minutes.

## Success metrics
`export.downloaded` events per studio per week, support tickets tagged `export`, reconciliation time survey after four weeks.

## Rollback
Turn the flag off (takes effect in under a minute; verified in staging). No migration, so no data rollback is needed.

## Communication
Release note in the product changelog, direct message to the three pilot studios, support macro updated to point at the
self-service export.
