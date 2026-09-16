---
name: sdlc-data
description: Design data changes safely - model and migration strategy, classification, ownership, retention, lineage and privacy impact. Use in the design phase when the change declares the data or personal-data scope, or when touching schemas, datasets, pipelines or personal information.
license: MIT
metadata:
  harness-phase: design
---
# Data and privacy

Goal: `data.md` that makes data changes reversible where possible and compliant by design.

## Steps

1. List every entity or dataset changed with its classification (public, internal, confidential, restricted) and owner.
2. Migrations: use expand/contract (add, dual-write or backfill, switch reads, remove old) so every deploy is
   backward compatible. Estimate volume and duration; plan batches and idempotent backfills.
3. Rollback: describe how to revert schema and data and identify any point of no return; a human confirms it.
4. Retention and lineage: retention period per dataset, deletion mechanism, upstream sources and downstream consumers
   (analytics, exports, caches, search indexes, backups).
5. Personal data (scope `personal-data`): answer every privacy impact question - categories, purpose and lawful
   basis, minimization, retention, data subject rights, cross-border transfers and residency, processors. Prefer
   pseudonymization and field-level encryption for restricted data. A data steward or security approves.
6. Never use production personal data in development or tests; describe synthetic or anonymized alternatives.
