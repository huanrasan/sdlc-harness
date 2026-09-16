"""Install the harness into a repository and build the vendored single-file CLI."""
from __future__ import annotations

import re
import shutil
import tempfile
import zipapp
from pathlib import Path

from . import adapters, memory, skills
from .core import VENDORED_CLI, load_config, paths

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "template"


def build_pyz(target: Path) -> None:
    """Zip the package (without templates) into a stdlib-only executable archive."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "sdlc_harness"
        shutil.copytree(PACKAGE_DIR, pkg, ignore=shutil.ignore_patterns("template", "__pycache__", "*.pyc"))
        target.parent.mkdir(parents=True, exist_ok=True)
        zipapp.create_archive(tmp, target, interpreter="/usr/bin/env python3", main="sdlc_harness.cli:main")


def init(target: Path, profile: str, agents: list[str], mode: str, ci: str) -> int:
    if not TEMPLATE_DIR.is_dir():
        raise SystemExit("`init` needs the installed package (templates are not bundled in sdlc.pyz)")
    target.mkdir(parents=True, exist_ok=True)
    skipped = []
    for src in sorted(TEMPLATE_DIR.rglob("*")):
        rel = src.relative_to(TEMPLATE_DIR)
        if src.is_dir() or "__pycache__" in rel.parts or rel.parts[0] == "ci":
            continue
        if ci != "github" and rel.parts[0] == ".github" and "workflows" in rel.parts:
            continue
        dst = target / rel
        if dst.exists():
            skipped.append(rel.as_posix())
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if ci == "gitlab" and not (target / ".gitlab-ci.sdlc.yml").exists():
        shutil.copy2(TEMPLATE_DIR / "ci" / "gitlab" / ".gitlab-ci.sdlc.yml", target / ".gitlab-ci.sdlc.yml")

    build_pyz(target / VENDORED_CLI)
    for hook in (target / ".harness" / "hooks").iterdir():
        hook.chmod(0o755)

    if "harness.toml" not in skipped:
        cfg_path = target / "harness.toml"
        text = cfg_path.read_text(encoding="utf-8")
        text = re.sub(r'^profile = ".*"$', f'profile = "{profile}"', text, flags=re.M)
        text = re.sub(r"^targets = \[.*\]$", "targets = [" + ", ".join(f'"{a}"' for a in agents) + "]", text, flags=re.M)
        text = re.sub(r'^mode = ".*"$', f'mode = "{mode}"', text, flags=re.M)
        cfg_path.write_text(text, encoding="utf-8")
    if "roster.toml" not in (Path(s).name for s in skipped) and ci == "gitlab":
        roster = target / ".harness" / "roster.toml"
        roster.write_text(roster.read_text(encoding="utf-8").replace('platform = "github"', 'platform = "gitlab"'),
                          encoding="utf-8")

    for s in skipped:
        print(f"skipped existing file: {s}")
    sync(target)
    print(
        "\nNext steps:\n"
        "  1. Edit .harness/roster.toml (people/teams per role), then: python3 .harness/sdlc.pyz codeowners\n"
        "  2. python3 .harness/sdlc.pyz hooks && python3 .harness/sdlc.pyz doctor\n"
        "  3. python3 .harness/sdlc.pyz new feature my-change --risk medium"
    )
    return 0


def sync(root: Path) -> int:
    cfg = load_config(root)
    report, found = skills.check_skills(root, paths(cfg)["skills"])
    if report.errors:
        return report.print()
    if skills.write_index(root, found):
        print("updated AGENTS.md skills index")
    if (root / memory.MEMORY_DIR).is_dir():
        memory.write_index(root)
    adapters.sync(root, cfg)
    return 0
