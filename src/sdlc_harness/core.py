"""Shared primitives: configuration, reports, parsing helpers."""
from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__

VERSION = __version__
PHASES = ["discover", "spec", "design", "plan", "implement", "verify", "review", "release", "operate", "done"]
RISKS = ["low", "medium", "high"]
TYPES = ["fix", "feature", "architecture", "retirement"]
# Scopes make artifacts conditional: a rule with `scopes` applies only when the change declares one of them.
SCOPES = ["ui", "api", "data", "personal-data", "infra", "ai"]
PROFILES = ["lite", "standard", "regulated"]
PLACEHOLDER = "<!-- sdlc:fill -->"
VENDORED_CLI = ".harness/sdlc.pyz"


class HarnessError(SystemExit):
    """Fatal configuration or usage error (exit code 2)."""

    def __init__(self, message: str):
        print(f"ERROR {message}")
        super().__init__(2)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def extend(self, other: "Report") -> "Report":
        self.errors += other.errors
        self.warnings += other.warnings
        return self

    def print(self) -> int:
        for w in self.warnings:
            print(f"WARN  {w}")
        for e in self.errors:
            print(f"ERROR {e}")
        status = "FAIL" if self.errors else "OK"
        print(f"{status}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


# --------------------------------------------------------------------------- config

def load_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_config(root: Path) -> dict:
    cfg_path = root / "harness.toml"
    if not cfg_path.exists():
        raise HarnessError(f"harness.toml not found in {root}. Run `sdlc init` first.")
    cfg = load_toml(cfg_path)
    profile = cfg.get("harness", {}).get("profile", "standard")
    profile_path = root / ".harness" / "profiles" / f"{profile}.toml"
    if not profile_path.exists():
        raise HarnessError(f"profile file not found: {profile_path.relative_to(root)}")
    cfg["_profile"] = load_toml(profile_path)
    roster_path = root / ".harness" / "roster.toml"
    cfg["_roster"] = load_toml(roster_path) if roster_path.exists() else {}
    cfg["_root"] = root
    return cfg


def paths(cfg: dict) -> dict:
    p = cfg.get("paths", {})
    return {
        "skills": p.get("skills", ".agents/skills"),
        "changes": p.get("changes", "docs/changes"),
        "adr": p.get("adr", "docs/adr"),
        "templates": p.get("templates", "docs/sdlc/templates"),
    }


# --------------------------------------------------------------------------- hashing / git

def sha256_file(path: Path) -> str:
    # Normalize line endings so a Windows checkout does not invalidate approvals.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise HarnessError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


# --------------------------------------------------------------------------- markdown

def parse_frontmatter(text: str) -> tuple[dict, str] | None:
    """Parse the flat YAML subset used by SKILL.md (scalars + one-level maps)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data: dict = {}
    current_map: str | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw.startswith((" ", "\t"))
        key, sep, value = raw.strip().partition(":")
        if not sep:
            continue
        value = value.strip().strip('"').strip("'")
        if indented and current_map:
            data[current_map][key] = value
        elif value == "":
            current_map = key
            data[key] = {}
        else:
            current_map = None
            data[key] = value
    return data, text[end + 4:].lstrip("\n")


def section(text: str, heading: str) -> str:
    """Body of `## heading` (exact title preferred, else prefix; case-insensitive)."""
    for suffix in (r"[ \t]*\n", r"[^\n]*\n"):  # exact heading first, then prefix
        pattern = re.compile(rf"^##\s+{re.escape(heading)}{suffix}(.*?)(?=^##\s|\Z)", re.M | re.S | re.I)
        if m := pattern.search(text):
            return m.group(1).strip()
    return ""


def tables(text: str) -> list[list[dict]]:
    """All pipe tables in `text` as lists of row dicts keyed by lowercase header."""
    result, lines, i = [], text.splitlines(), 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip().lower() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                rows.append(dict(zip(header, cells + [""] * (len(header) - len(cells)))))
                j += 1
            result.append(rows)
            i = j
        else:
            i += 1
    return result


def table_with(text: str, column_prefix: str) -> list[dict]:
    """First table having a column whose header starts with `column_prefix`."""
    for rows in tables(text):
        if rows and any(k.startswith(column_prefix) for k in rows[0]):
            return rows
    return []


def cell(row: dict, prefix: str) -> str:
    for k, v in row.items():
        if k.startswith(prefix):
            return v
    return ""
