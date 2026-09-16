"""Agent Skills validation and the generated AGENTS.md index."""
from __future__ import annotations

import re
from pathlib import Path

from .core import PLACEHOLDER, Report, parse_frontmatter

SKILLS_START = "<!-- sdlc:skills:start -->"
SKILLS_END = "<!-- sdlc:skills:end -->"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
INDEX_RE = re.compile(re.escape(SKILLS_START) + ".*?" + re.escape(SKILLS_END), re.S)


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
        name, desc = meta.get("name", ""), meta.get("description", "")
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


def render_index(skills: list[dict]) -> str:
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
    if PLACEHOLDER in text:
        report.warn(f"AGENTS.md still has unfilled sections ({PLACEHOLDER})")
    if (n := len(text.splitlines())) > max_lines:
        report.warn(f"AGENTS.md has {n} lines (> {max_lines}); move conditional knowledge to skills")
    match = INDEX_RE.search(text)
    if not match:
        report.error("AGENTS.md lacks the skills index markers; run `sdlc sync`")
    elif match.group(0) != render_index(skills):
        report.error("AGENTS.md skills index is stale; run `sdlc sync`")
    return report


def write_index(root: Path, skills: list[dict]) -> bool:
    agents_md = root / "AGENTS.md"
    text = agents_md.read_text(encoding="utf-8")
    index = render_index(skills)
    new = INDEX_RE.sub(lambda _: index, text) if INDEX_RE.search(text) else text.rstrip() + "\n\n" + index + "\n"
    if new != text:
        agents_md.write_text(new, encoding="utf-8")
    return new != text
