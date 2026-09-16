# AGENTS.md

Instructions for AI agents contributing to **sdlc-harness** itself (not the template installed in other repos).

## Layout

- `src/sdlc_harness/` - CLI package. Standard library only, Python >= 3.11. `init` vendors it (without templates)
  into target repos as `.harness/sdlc.pyz`.
- `src/sdlc_harness/template/` - files installed into target repositories.
- `tests/` - `unittest` suites; they install the template into temporary git repos.
- `docs/en`, `docs/es` - bilingual user docs; `docs/adr` - decisions (English).
- `skills/`, `.claude-plugin/`, `gemini-extension.json` - generated distribution packages; `distribution/` - their extra sources.
- `evals/` - behavioural scenarios, agent adapters and runner.

## Commands

- Test: `python3 -m unittest discover -s tests`
- Lint: `uvx pyflakes src tests`
- Distribution packages: `python3 scripts/build_distribution.py` (CI runs `--check`)
- Evals: `python3 evals/run.py --agent simulated-good` (graders) or a real agent (costs tokens)
- Smoke install: `PYTHONPATH=src python3 -m sdlc_harness init /tmp/demo --profile regulated && python3 /tmp/demo/.harness/sdlc.pyz --root /tmp/demo check`

## Rules

- No third-party runtime dependencies. No network access except `sdlc approvals verify` (platform API).
- Behaviour change in the CLI -> tests. Decision change -> new ADR (supersede, never rewrite).
- User-facing doc change -> update both `docs/en/` and `docs/es/` in the same PR.
- Skills in the template must follow the Agent Skills spec (name = directory, description <= 1024 chars).
- Never weaken approval integrity: receipts, audit logs and platform checks are security controls; add tests for bypasses.
- Do not copy text from sources with licenses incompatible with MIT; reference ideas and cite in `ACKNOWLEDGEMENTS.md`.
