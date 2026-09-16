---
name: sdlc-retire
description: Decommission a service, feature, API version, dataset or infrastructure safely - consumer inventory, deprecation timeline, data disposition, contract deprecation, teardown and rollback. Use for changes of type retirement, when sunsetting or deprecating anything, or when an outcome decision is retire.
license: MIT
metadata:
  harness-phase: design
---
# Retire

Goal: `retirement.md` and a change that removes something without surprising anyone or leaving orphaned data,
credentials or costs.

## Steps

1. State what is retired and why (outcome decision, cost, security, replacement).
2. Inventory consumers from evidence, not memory: access logs, API gateway metrics, service dependency maps, data
   lineage, CODEOWNERS of dependent repos. Give each a migration path and track status.
3. Timeline: deprecation notice (API `Deprecation`/`Sunset` headers, changelog, direct communication), optional
   brownouts, and a sunset date.
4. Data disposition: archive, export or delete according to retention obligations; keep evidence of deletion.
5. Contracts and dependencies: bump the contract major version or remove it with an ADR; revoke credentials, secrets,
   DNS entries, service accounts and network rules.
6. Infrastructure: destroy through IaC (plan reviewed by a human), remove dashboards and alerts, confirm cost savings.
7. Rollback: how to restore before the point of no return. Destructive steps require human confirmation.
