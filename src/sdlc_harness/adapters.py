"""Per-agent adapters generated from AGENTS.md and .agents/skills."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .core import HarnessError, Report, load_toml


def selected(root: Path, cfg: dict) -> dict:
    catalog_path = root / ".harness" / "adapters.toml"
    if not catalog_path.exists():
        return {}
    catalog = load_toml(catalog_path).get("adapters", {})
    targets = cfg.get("agents", {}).get("targets", [])
    if unknown := [t for t in targets if t not in catalog]:
        raise HarnessError(f"unknown agent targets in harness.toml: {unknown}")
    return {t: catalog[t] for t in targets}


def _digest(path: Path) -> dict:
    return {str(f.relative_to(path)): f.read_bytes() for f in sorted(path.rglob("*")) if f.is_file()}


def check(root: Path, cfg: dict) -> Report:
    report = Report()
    for name, spec in selected(root, cfg).items():
        for f in spec.get("files", []):
            path = root / f["path"]
            if not path.exists() or f["content"].strip() not in path.read_text(encoding="utf-8"):
                report.error(f"adapter {name}: {f['path']} out of sync; run `sdlc sync`")
        for link in spec.get("links", []):
            path, target = root / link["path"], root / link["target"]
            if not path.exists():
                report.error(f"adapter {name}: {link['path']} missing; run `sdlc sync`")
            elif not path.is_symlink() and _digest(path) != _digest(target):
                report.error(f"adapter {name}: copy at {link['path']} drifted from {link['target']}; run `sdlc sync`")
    return report


def sync(root: Path, cfg: dict) -> None:
    mode = cfg.get("agents", {}).get("mode", "symlink")
    for name, spec in selected(root, cfg).items():
        for f in spec.get("files", []):
            path = root / f["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(f["content"], encoding="utf-8")
                print(f"[{name}] created {f['path']}")
            elif f["content"].strip() not in path.read_text(encoding="utf-8"):
                print(f"[{name}] WARN {f['path']} exists; add this line manually: {f['content'].strip()!r}")
        for link in spec.get("links", []):
            _sync_link(root, name, link, mode)


def _sync_link(root: Path, adapter: str, link: dict, mode: str) -> None:
    path, target = root / link["path"], root / link["target"]
    path.parent.mkdir(parents=True, exist_ok=True)
    rel_target = os.path.relpath(target, path.parent)
    if mode == "symlink":
        if path.is_symlink() and os.readlink(path) == rel_target:
            return
        if path.exists() or path.is_symlink():
            print(f"[{adapter}] WARN {link['path']} exists and is not the expected symlink; left untouched")
            return
        path.symlink_to(rel_target, target_is_directory=target.is_dir())
        print(f"[{adapter}] linked {link['path']} -> {rel_target}")
        return
    if path.is_symlink():
        print(f"[{adapter}] WARN {link['path']} is a symlink but mode=copy; left untouched")
        return
    if path.exists():
        shutil.rmtree(path)
    shutil.copytree(target, path)
    print(f"[{adapter}] copied {link['target']} -> {link['path']}")
