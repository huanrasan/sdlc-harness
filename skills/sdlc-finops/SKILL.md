---
name: sdlc-finops
description: Estimate and control the cost of infrastructure changes on any public or private cloud - pricing drivers, monthly estimate, unit economics, budgets, allocation tags and idle policies. Use in the design phase when the change declares the infra scope, or when choosing instance sizes, managed services or data retention.
license: MIT
metadata:
  harness-phase: design
---
# FinOps

Goal: `cost.md` with a defensible estimate and guardrails that keep actual spend observable.

## Steps

1. Break the design into cost components and identify each pricing driver (vCPU-hours, GB-month, requests, egress
   GB, licenses, support tiers, on-prem amortization for private cloud).
2. Estimate volumes from the spec's non-functional requirements; state assumptions explicitly (traffic, growth,
   retention, redundancy, environments). Cite the price source and date; never invent prices - mark unknowns.
3. Produce monthly totals for production and non-production, and unit economics (cost per request, user, tenant).
4. Compare at least one cheaper alternative (smaller tier, serverless vs provisioned, retention reduction, reserved
   capacity) and explain the trade-off.
5. Guardrails: budget with alert thresholds, cost allocation tags or labels in IaC, scale-down or idle shutdown for
   non-production. Put these in infrastructure code, not only in documentation.
6. After release, compare actual cost with the estimate in `outcome.md` or the iteration review.
