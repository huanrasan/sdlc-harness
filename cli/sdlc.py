#!/usr/bin/env python3
"""sdlc - agent-agnostic SDLC harness CLI.

Standard library only (Python >= 3.11) so the same file runs on a laptop,
in any CI system and inside air-gapped/private-cloud runners.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "0.1.0"
PHASES = ["spec", "design", "plan", "implement", "verify", "review", "release", "operate", "done"]
RISKS = ["low", "medium", "high"]
TYPES = ["fix", "feature", "architecture"]
PROFILES = ["lite", "standard", "regulated"]
PLACEHOLDER = "<!-- sdlc:fill -->"
SKILLS_START = "<!-- sdlc:skills:start -->"
SKILLS_END = "<!-- sdlc:skills:end -->"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ADR_FILE_RE = re.compile(r"^\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.md$")
ADR_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(Proposed|Accepted|Rejected|Deprecated|Superseded by \d{4})\s*$", re.M)
CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: .+"
)

SOURCE_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- findings

@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def extend(self, other: "Report") -> None:
        self.errors += other.errors
        self.warnings += other.warnings

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
        raise SystemExit(f"harness.toml not found in {root}. Run `sdlc init` first.")
    cfg = load_toml(cfg_path)
    profile = cfg.get("harness", {}).get("profile", "standard")
    profile_path = root / ".harness" / "profiles" / f"{profile}.toml"
    if not profile_path.exists():
        raise SystemExit(f"Profile file not found: {profile_path}")
    cfg["_profile"] = load_toml(profile_path)
    return cfg


def paths(cfg: dict) -> dict:
    p = cfg.get("paths", {})
    return {
        "skills": p.get("skills", ".agents/skills"),
        "changes": p.get("changes", "docs/changes"),
        "adr": p.get("adr", "docs/adr"),
        "templates": p.get("templates", "docs/sdlc/templates"),
    }


# --------------------------------------------------------------------------- frontmatter

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
    body = text[end + 4:].lstrip("\n")
    return data, body


# --------------------------------------------------------------------------- checks

def check_skills(root: Path, skills_dir: str) -> tuple[Report, list[dict]]:
    report, skills = Report(), []
    base = root / skills_dir
    if not base.is_dir():
        report.error(f"skills directory missing: {skills_dir}")
        return report, skills
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        skill_md = d / "SKILL.md"
        rel = skill_md.relative_to(root)
        if not skill_md.exists():
            report.error(f"{d.relative_to(root)}: missing SKILL.md")
            continue
        parsed = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if parsed is None:
            report.error(f"{rel}: missing or malformed YAML frontmatter")
            continue
        meta, body = parsed
        name = meta.get("name", "")
        desc = meta.get("description", "")
        if not (1 <= len(name) <= 64 and SKILL_NAME_RE.match(name)):
            report.error(f"{rel}: invalid name '{name}' (lowercase, digits, single hyphens, <=64)")
        if name != d.name:
            report.error(f"{rel}: name '{name}' must match directory '{d.name}'")
        if not 1 <= len(desc) <= 1024:
            report.error(f"{rel}: description must be 1..1024 characters")
        if "compatibility" in meta and len(meta["compatibility"]) > 500:
            report.error(f"{rel}: compatibility must be <=500 characters")
        if len(body.splitlines()) > 500:
            report.warn(f"{rel}: body exceeds 500 lines; move detail to references/")
        skills.append({"name": name, "description": desc, "path": str(rel)})
    return report, skills


def render_skills_index(skills: list[dict]) -> str:
    lines = [SKILLS_START, "| Skill | Use when | Path |", "|---|---|---|"]
    for s in skills:
        desc = s["description"].replace("|", "\\|")
        lines.append(f"| `{s['name']}` | {desc} | `{s['path']}` |")
    lines.append(SKILLS_END)
    return "\n".join(lines)


def check_agents_md(root: Path, cfg: dict, skills: list[dict]) -> Report:
    report = Report()
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        report.error("AGENTS.md missing")
        return report
    text = agents_md.read_text(encoding="utf-8")
    max_lines = cfg.get("harness", {}).get("agents_md_max_lines", 150)
    n = len(text.splitlines())
    if PLACEHOLDER in text:
        report.warn(f"AGENTS.md still has unfilled sections ({PLACEHOLDER})")
    if n > max_lines:
        report.warn(f"AGENTS.md has {n} lines (> {max_lines}); move conditional knowledge to skills")
    match = re.search(re.escape(SKILLS_START) + ".*?" + re.escape(SKILLS_END), text, re.S)
    if not match:
        report.error("AGENTS.md lacks the skills index markers; run `sdlc sync`")
    elif match.group(0) != render_skills_index(skills):
        report.error("AGENTS.md skills index is stale; run `sdlc sync`")
    return report


def required_artifacts(change: dict, rules: list[dict], upto_phase: str | None = None) -> list[dict]:
    """Rules whose producing phase has been completed (or will be, when upto_phase is given)."""
    phase_idx = PHASES.index(upto_phase or change["phase"])
    risk_idx = RISKS.index(change["risk"])
    out = []
    for rule in rules:
        if change["type"] not in rule.get("types", TYPES):
            continue
        if risk_idx < RISKS.index(rule.get("min_risk", "low")):
            continue
        if upto_phase is None and phase_idx <= PHASES.index(rule["phase"]):
            continue
        out.append(rule)
    return out


def load_change(change_dir: Path, report: Report) -> dict | None:
    meta_path = change_dir / "change.toml"
    if not meta_path.exists():
        report.error(f"{change_dir}: missing change.toml")
        return None
    try:
        change = load_toml(meta_path)
    except tomllib.TOMLDecodeError as exc:
        report.error(f"{meta_path}: invalid TOML ({exc})")
        return None
    ok = True
    for key, allowed in (("type", TYPES), ("risk", RISKS), ("phase", PHASES)):
        if change.get(key) not in allowed:
            report.error(f"{meta_path}: '{key}' must be one of {allowed}")
            ok = False
    if not isinstance(change.get("ai_assisted"), bool):
        report.error(f"{meta_path}: 'ai_assisted' must be true or false (AI disclosure control)")
        ok = False
    return change if ok else None


def check_change(root: Path, change_dir: Path, cfg: dict) -> Report:
    report = Report()
    change = load_change(change_dir, report)
    if change is None:
        return report
    rel = change_dir.relative_to(root)
    rules = cfg["_profile"].get("rules", [])
    for rule in required_artifacts(change, rules):
        artifact = rule["artifact"]
        if artifact == "adr":
            adrs = change.get("adrs", [])
            if not adrs:
                report.error(f"{rel}: phase '{rule['phase']}' requires at least one ADR in `adrs`")
            for adr in adrs:
                if not (root / adr).exists():
                    report.error(f"{rel}: referenced ADR not found: {adr}")
            continue
        path = change_dir / artifact
        if not path.exists():
            report.error(f"{rel}: '{artifact}' required after phase '{rule['phase']}'")
        elif PLACEHOLDER in path.read_text(encoding="utf-8"):
            report.error(f"{rel}/{artifact}: unfilled sections ({PLACEHOLDER})")
    return report


def check_adrs(root: Path, adr_dir: str) -> Report:
    report = Report()
    base = root / adr_dir
    if not base.is_dir():
        return report
    for f in sorted(base.glob("*.md")):
        if f.name.lower() in ("readme.md", "template.md"):
            continue
        rel = f.relative_to(root)
        if not ADR_FILE_RE.match(f.name):
            report.error(f"{rel}: ADR filename must be NNNN-kebab-title.md")
        if not ADR_STATUS_RE.search(f.read_text(encoding="utf-8")):
            report.error(f"{rel}: missing or invalid '**Status:**' line")
    return report


def run_check(root: Path, only_change: str | None = None) -> Report:
    cfg = load_config(root)
    p = paths(cfg)
    report = Report()
    skills_report, skills = check_skills(root, p["skills"])
    if only_change is None:
        report.extend(skills_report)
        report.extend(check_agents_md(root, cfg, skills))
        report.extend(check_adrs(root, p["adr"]))
        report.extend(check_adapters(root, cfg))
    changes = root / p["changes"]
    if changes.is_dir():
        for d in sorted(x for x in changes.iterdir() if x.is_dir()):
            if only_change and d.name != only_change:
                continue
            report.extend(check_change(root, d, cfg))
    if only_change and not (changes / only_change).is_dir():
        report.error(f"change not found: {only_change}")
    return report


# --------------------------------------------------------------------------- adapters

def selected_adapters(root: Path, cfg: dict) -> dict:
    adapters_path = root / ".harness" / "adapters.toml"
    if not adapters_path.exists():
        return {}
    catalog = load_toml(adapters_path).get("adapters", {})
    targets = cfg.get("agents", {}).get("targets", [])
    unknown = [t for t in targets if t not in catalog]
    if unknown:
        raise SystemExit(f"unknown agent targets in harness.toml: {unknown}")
    return {t: catalog[t] for t in targets}


def check_adapters(root: Path, cfg: dict) -> Report:
    report = Report()
    for name, spec in selected_adapters(root, cfg).items():
        for f in spec.get("files", []):
            path = root / f["path"]
            if not path.exists() or f["content"].strip() not in path.read_text(encoding="utf-8"):
                report.error(f"adapter {name}: {f['path']} out of sync; run `sdlc sync`")
        for link in spec.get("links", []):
            path, target = root / link["path"], root / link["target"]
            if not path.exists():
                report.error(f"adapter {name}: {link['path']} missing; run `sdlc sync`")
            elif not path.is_symlink() and _tree_digest(path) != _tree_digest(target):
                report.error(f"adapter {name}: copy at {link['path']} drifted from {link['target']}; run `sdlc sync`")
    return report


def _tree_digest(path: Path) -> dict:
    return {
        str(f.relative_to(path)): f.read_bytes()
        for f in sorted(path.rglob("*"))
        if f.is_file()
    }


def sync(root: Path) -> int:
    cfg = load_config(root)
    p = paths(cfg)
    skills_report, skills = check_skills(root, p["skills"])
    if skills_report.errors:
        return skills_report.print()

    agents_md = root / "AGENTS.md"
    text = agents_md.read_text(encoding="utf-8")
    index = render_skills_index(skills)
    pattern = re.compile(re.escape(SKILLS_START) + ".*?" + re.escape(SKILLS_END), re.S)
    new_text = pattern.sub(lambda _: index, text) if pattern.search(text) else text.rstrip() + "\n\n" + index + "\n"
    if new_text != text:
        agents_md.write_text(new_text, encoding="utf-8")
        print("updated AGENTS.md skills index")

    mode = cfg.get("agents", {}).get("mode", "symlink")
    for name, spec in selected_adapters(root, cfg).items():
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
    return 0


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
    else:
        if path.is_symlink():
            print(f"[{adapter}] WARN {link['path']} is a symlink but mode=copy; left untouched")
            return
        if path.exists():
            shutil.rmtree(path)
        shutil.copytree(target, path)
        print(f"[{adapter}] copied {link['target']} -> {link['path']}")


# --------------------------------------------------------------------------- commands

def cmd_init(args: argparse.Namespace) -> int:
    template = SOURCE_ROOT / "template"
    if not template.is_dir():
        raise SystemExit("`init` must run from a clone of the harness repository (template/ not found)")
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    skipped = []
    for src in sorted(template.rglob("*")):
        rel = src.relative_to(template)
        if src.is_dir() or rel.parts[0] == "ci":
            continue
        if args.ci != "github" and rel.parts[0] == ".github" and "workflows" in rel.parts:
            continue
        dst = target / rel
        if dst.exists():
            skipped.append(str(rel))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if args.ci == "gitlab":
        dst = target / ".gitlab-ci.sdlc.yml"
        if not dst.exists():
            shutil.copy2(template / "ci" / "gitlab" / ".gitlab-ci.sdlc.yml", dst)

    shutil.copy2(Path(__file__).resolve(), target / ".harness" / "sdlc.py")
    for hook in (target / ".harness" / "hooks").iterdir():
        hook.chmod(0o755)

    cfg_path = target / "harness.toml"
    cfg_text = cfg_path.read_text(encoding="utf-8")
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    cfg_text = re.sub(r'^profile = ".*"$', f'profile = "{args.profile}"', cfg_text, flags=re.M)
    cfg_text = re.sub(r"^targets = \[.*\]$", "targets = [" + ", ".join(f'"{a}"' for a in agents) + "]",
                      cfg_text, flags=re.M)
    cfg_text = re.sub(r'^mode = ".*"$', f'mode = "{args.mode}"', cfg_text, flags=re.M)
    if "harness.toml" not in skipped:
        cfg_path.write_text(cfg_text, encoding="utf-8")

    for s in skipped:
        print(f"skipped existing file: {s}")
    sync(target)
    print(
        "\nNext steps:\n"
        "  python3 .harness/sdlc.py hooks      # install git hooks\n"
        "  python3 .harness/sdlc.py doctor     # verify controls\n"
        "  python3 .harness/sdlc.py new feature my-change --risk medium"
    )
    return 0


def cmd_new(args: argparse.Namespace, root: Path) -> int:
    if not SLUG_RE.match(args.slug):
        raise SystemExit("slug must be kebab-case")
    cfg = load_config(root)
    p = paths(cfg)
    change_id = f"{dt.date.today().isoformat()}-{args.slug}"
    change_dir = root / p["changes"] / change_id
    if change_dir.exists():
        raise SystemExit(f"change already exists: {change_dir}")
    change_dir.mkdir(parents=True)
    ai = "true" if args.ai_assisted else "false"
    (change_dir / "change.toml").write_text(
        f'id = "{change_id}"\ntype = "{args.type}"\nrisk = "{args.risk}"\nphase = "spec"\n'
        f"ai_assisted = {ai}\nadrs = []\n",
        encoding="utf-8",
    )
    change = {"type": args.type, "risk": args.risk, "phase": "spec"}
    created = []
    for rule in required_artifacts(change, cfg["_profile"].get("rules", []), upto_phase="done"):
        if rule["artifact"] == "adr":
            continue
        tpl = root / p["templates"] / rule["artifact"]
        if tpl.exists():
            shutil.copy2(tpl, change_dir / rule["artifact"])
            created.append(rule["artifact"])
    print(f"created {change_dir.relative_to(root)} with: change.toml {' '.join(created)}")
    return 0


def cmd_phase(args: argparse.Namespace, root: Path) -> int:
    cfg = load_config(root)
    change_dir = root / paths(cfg)["changes"] / args.change
    meta = change_dir / "change.toml"
    if not meta.exists():
        raise SystemExit(f"change not found: {args.change}")
    text = meta.read_text(encoding="utf-8")
    current = load_toml(meta).get("phase")
    if current in PHASES and PHASES.index(args.phase) > PHASES.index(current) + 1:
        raise SystemExit(f"cannot skip phases: {current} -> {args.phase}")
    candidate = re.sub(r'^phase = ".*"$', f'phase = "{args.phase}"', text, flags=re.M)
    meta.write_text(candidate, encoding="utf-8")
    report = check_change(root, change_dir, cfg)
    if report.errors:
        meta.write_text(text, encoding="utf-8")
        print(f"gate blocked: {args.change} stays in '{current}'")
    else:
        print(f"{args.change}: {current} -> {args.phase}")
    return report.print()


def cmd_commit_msg(args: argparse.Namespace, root: Path) -> int:
    cfg = load_config(root)
    msg = Path(args.file).read_text(encoding="utf-8")
    lines = [l for l in msg.splitlines() if not l.startswith("#")]
    report = Report()
    subject = lines[0] if lines else ""
    if not subject.startswith(("Merge ", "Revert ")) and not CONVENTIONAL_RE.match(subject):
        report.error("subject must follow Conventional Commits: type(scope): summary")
    for trailer in cfg["_profile"].get("commits", {}).get("require_trailers", []):
        if not re.search(rf"^{re.escape(trailer)}: .+$", msg, re.M):
            report.error(f"missing required trailer '{trailer}: <value>' (use 'none' if not applicable)")
    return report.print() if report.errors else 0


def cmd_hooks(root: Path) -> int:
    subprocess.run(["git", "config", "core.hooksPath", ".harness/hooks"], cwd=root, check=True)
    print("git hooks enabled (core.hooksPath=.harness/hooks)")
    return 0


def cmd_doctor(root: Path) -> int:
    cfg = load_config(root)
    profile = cfg.get("harness", {}).get("profile")
    report = Report()
    if sys.version_info < (3, 11):
        report.error("Python >= 3.11 required")
    git = subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=root, capture_output=True, text=True)
    if git.stdout.strip() != ".harness/hooks":
        report.warn("git hooks not installed; run `sdlc hooks` (CI remains the authoritative gate)")
    has_ci = (root / ".github/workflows/sdlc-gates.yml").exists() or (root / ".gitlab-ci.sdlc.yml").exists()
    if not has_ci:
        (report.error if profile == "regulated" else report.warn)("no CI gate found; local hooks can be bypassed")
    codeowners = any((root / p).exists() for p in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"))
    if not codeowners:
        (report.error if profile == "regulated" else report.warn)(
            "no CODEOWNERS: human approval of specs/ADRs cannot be enforced by the platform"
        )
    installed = cfg.get("harness", {}).get("version")
    if installed and installed != VERSION:
        report.warn(f"harness.toml version {installed} != CLI {VERSION}")
    report.extend(run_check(root))
    return report.print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sdlc", description="Agent-agnostic SDLC harness")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="install the harness into a repository")
    p_init.add_argument("target")
    p_init.add_argument("--profile", choices=PROFILES, default="standard")
    p_init.add_argument("--agents", default="claude-code,codex,copilot,cursor,gemini-cli")
    p_init.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    p_init.add_argument("--ci", choices=["github", "gitlab", "none"], default="github")

    sub.add_parser("sync", help="regenerate AGENTS.md skills index and agent adapters")

    p_check = sub.add_parser("check", help="validate skills, ADRs, adapters and change gates")
    p_check.add_argument("--change", help="only validate this change id")

    p_new = sub.add_parser("new", help="start a change record")
    p_new.add_argument("type", choices=TYPES)
    p_new.add_argument("slug")
    p_new.add_argument("--risk", choices=RISKS, default="medium")
    p_new.add_argument("--no-ai", dest="ai_assisted", action="store_false")

    p_phase = sub.add_parser("phase", help="move a change to the next phase if its gate passes")
    p_phase.add_argument("change")
    p_phase.add_argument("phase", choices=PHASES)

    p_msg = sub.add_parser("commit-msg", help="validate a commit message file")
    p_msg.add_argument("file")

    sub.add_parser("hooks", help="enable the harness git hooks")
    sub.add_parser("doctor", help="check controls and configuration")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    match args.command:
        case "init":
            return cmd_init(args)
        case "sync":
            return sync(root)
        case "check":
            return run_check(root, args.change).print()
        case "new":
            return cmd_new(args, root)
        case "phase":
            return cmd_phase(args, root)
        case "commit-msg":
            return cmd_commit_msg(args, root)
        case "hooks":
            return cmd_hooks(root)
        case "doctor":
            return cmd_doctor(root)
    return 2


if __name__ == "__main__":
    sys.exit(main())
