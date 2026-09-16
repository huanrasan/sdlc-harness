---
name: sdlc-maintain
description: Keep the codebase and the harness healthy - detect drift between docs, ADRs and code, prune stale instructions, track technical debt and turn repeated agent mistakes into deterministic checks. Use for periodic maintenance, after a postmortem, or when agents repeat the same mistake.
license: MIT
metadata:
  harness-phase: maintain
---
# Maintain (garbage collection)

Run on a schedule (for example weekly) and after incidents. Output small, independent pull requests.

## Checks

1. **Doc drift**: AGENTS.md commands still work; design docs and ADRs match the code; broken links.
2. **Instruction hygiene**: every AGENTS.md line must prevent a real mistake. Remove lines that do not;
   move conditional knowledge into skills; keep AGENTS.md under the configured line limit.
3. **Promote repeated feedback**: if a review comment or agent mistake appears twice, encode it as the most
   deterministic control possible: type or schema > linter/structural test > CI policy > skill instruction.
4. **Dependencies and supply chain**: outdated or vulnerable dependencies, unpinned CI actions and images,
   OpenSSF Scorecard results, exceptions in `.harness/exceptions.toml` close to expiry (renewal needs a human).
5. **Executable architecture**: accepted ADRs without matching rules in `.harness/architecture.toml`; rules citing
   superseded ADRs.
6. **Technical debt**: list hotspots (churn x complexity), dead code, flaky tests; propose prioritized items.
7. **Harness metrics**: gate failure rates, rework rate, lead time and change failure rate (DORA); skills never
   triggered or always ignored are candidates for rewrite or removal.

Never delete accepted ADRs or change records; supersede or archive them.
