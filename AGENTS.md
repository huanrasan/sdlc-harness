# AGENTS.md

Instructions for AI agents contributing to **sdlc-harness** itself (not the template installed in other repos).

## Layout

- `cli/sdlc.py` - the CLI. Standard library only, Python >= 3.11. Copied verbatim into target repos by `init`.
- `template/` - files installed into target repositories (`AGENTS.md`, `.agents/skills/`, `.harness/`, `docs/`, CI).
- `tests/` - `unittest` suite; tests install the template into temp repos.
- `docs/en`, `docs/es` - bilingual user docs; `docs/adr` - decisions (English).

## Commands

- Test: `python3 -m unittest discover -s tests`
- Smoke install: `python3 cli/sdlc.py init /tmp/demo --profile regulated && python3 /tmp/demo/.harness/sdlc.py check`

## Rules

- No third-party dependencies in the CLI. No network access at runtime.
- Behaviour change in the CLI -> test in `tests/test_sdlc.py`. Decision change -> new ADR (supersede, never rewrite).
- User-facing doc change -> update both `docs/en/` and `docs/es/` in the same PR.
- Skills in `template/.agents/skills/` must follow the Agent Skills spec (name = directory, description <= 1024 chars).
- Do not copy text from sources with licenses incompatible with MIT; reference ideas and cite in `ACKNOWLEDGEMENTS.md`.
- Never mark adapter paths as verified without checking the agent's current documentation.
