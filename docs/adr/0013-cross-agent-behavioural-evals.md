# 0013. Cross-agent behavioural evals graded on repository state

**Status:** Accepted
**Date:** 2026-09-16
**Deciders:** maintainers

## Context and problem
Skills and `AGENTS.md` are guidance; whether a given agent follows them under pressure (approve its own work, skip
failing tests, obey instructions embedded in an issue) is an empirical question that changes with every agent and model
release.

## Decision drivers
Agent neutrality (high), deterministic grading (high), grader correctness (high), cost (medium).

## Options considered
1. LLM-as-judge over transcripts.
2. Scenarios that install the harness in a fresh repository, run any headless agent CLI through a data-driven adapter
   (`evals/agents.toml`), and grade the resulting repository state with deterministic checks; transcript checks are
   optional and soft. Graders are themselves tested in CI against scripted good and bad simulated agents.
3. Manual review sessions.

## Decision
Option 2, starting with seven scenarios: risky feature intake, refusing self-approval, not weakening tests under
pressure, prompt injection in an issue, no ceremony for trivial fixes, retirement classification and memory use.

## Consequences
- Positive: comparable pass rates across agents and versions; regressions in skills show up as failed scenarios.
- Negative: real-agent runs cost time and tokens and need authenticated CLIs, so they run on demand, not on every pull
  request; outcomes are stochastic, so use several trials.
