#!/usr/bin/env python3
"""Generate agent distribution packages from the template skills.

Outputs (committed, so marketplaces and `npx skills add` can install from the repository):
- skills/                          Agent Skills: template skills + distribution-only skills
- .claude-plugin/plugin.json       Claude Code plugin manifest (plugin root = repository root)
- .claude-plugin/marketplace.json  Claude Code marketplace listing this plugin
- gemini-extension.json            Gemini CLI extension manifest (skills/ + context file)

Usage: python3 scripts/build_distribution.py [--check]
"""
from __future__ import annotations

import filecmp
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sdlc_harness import __version__  # noqa: E402

SOURCES = [ROOT / "src/sdlc_harness/template/.agents/skills", ROOT / "distribution/skills"]
REPO = "https://github.com/huanrasan/sdlc-harness"
DESCRIPTION = ("Agent-agnostic SDLC harness: skills for discovery to retirement, change records, human approvals, "
               "deterministic gates and sensors.")


def manifests() -> dict[str, str]:
    plugin = {
        "name": "sdlc-harness",
        "displayName": "SDLC Harness",
        "version": __version__,
        "description": DESCRIPTION,
        "author": {"name": "sdlc-harness contributors", "url": REPO},
        "homepage": REPO,
        "repository": REPO,
        "license": "MIT",
        "keywords": ["sdlc", "governance", "agent-skills", "devsecops", "adr"],
    }
    marketplace = {
        "name": "sdlc-harness",
        "owner": {"name": "sdlc-harness contributors", "url": REPO},
        "description": "Marketplace for the agent-agnostic SDLC harness",
        "plugins": [{"name": "sdlc-harness", "description": DESCRIPTION, "version": __version__, "source": "./",
                     "license": "MIT", "homepage": REPO}],
    }
    gemini = {"name": "sdlc-harness", "version": __version__, "description": DESCRIPTION,
              "contextFileName": "distribution/extension-context.md"}
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
    return {".claude-plugin/plugin.json": dump(plugin), ".claude-plugin/marketplace.json": dump(marketplace),
            "gemini-extension.json": dump(gemini)}


def expected_skills() -> dict[str, Path]:
    out = {}
    for source in SOURCES:
        for f in sorted(source.rglob("*")):
            if f.is_file() and f.name != ".DS_Store":
                out[f"skills/{f.relative_to(source).as_posix()}"] = f
    return out


def main() -> int:
    check = "--check" in sys.argv
    drift = []
    skills = expected_skills()
    actual = {f.relative_to(ROOT).as_posix() for f in (ROOT / "skills").rglob("*")
              if f.is_file() and f.name != ".DS_Store"} \
        if (ROOT / "skills").is_dir() else set()
    for rel, src in skills.items():
        dst = ROOT / rel
        if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
            drift.append(rel)
            if not check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    for rel in sorted(actual - set(skills)):
        drift.append(rel)
        if not check:
            (ROOT / rel).unlink()
    for rel, content in manifests().items():
        dst = ROOT / rel
        if not dst.exists() or dst.read_text(encoding="utf-8") != content:
            drift.append(rel)
            if not check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(content, encoding="utf-8")
    if check and drift:
        print("distribution out of date; run python3 scripts/build_distribution.py:\n  " + "\n  ".join(drift))
        return 1
    print(f"distribution {'up to date' if not drift else f'updated ({len(drift)} file(s))'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
