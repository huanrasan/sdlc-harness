"""Semantic gates: evidence must be internally consistent, not merely present.

Each checker receives the artifact text and a context and reports concrete, fixable problems.
They validate structure and cross-references deterministically; judging quality stays with reviewers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .core import Report, cell, section, table_with

AC_RE = re.compile(r"\bAC-\d+\b")
THREAT_RE = re.compile(r"\bT-\d+\b")
PASS_RESULTS = {"pass", "passed", "verified", "n/a"}
EMPTY = {"", "-", "tbd", "todo", "?"}


@dataclass
class Context:
    root: Path
    change_dir: Path
    cfg: dict
    change: dict

    def read(self, name: str) -> str:
        path = self.change_dir / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def ids(self, name: str, table_prefix: str, regex: re.Pattern) -> list[str]:
        rows = table_with(self.read(name), table_prefix)
        return sorted({m for r in rows for m in regex.findall(cell(r, "id"))}, key=_natural)


def _natural(s: str) -> tuple:
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s))


def _blank(value: str) -> bool:
    return value.strip().lower() in EMPTY


def _require_sections(text: str, rel: str, headings: list[str], report: Report) -> None:
    for h in headings:
        if _blank(section(text, h)):
            report.error(f"{rel}: section '{h}' is empty")


# --------------------------------------------------------------------------- artifacts

def check_spec(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    rows = table_with(text, "given")
    ids = [r for r in rows if AC_RE.search(cell(r, "id"))]
    if not ids:
        report.error(f"{rel}: needs at least one acceptance criterion with id AC-n")
    for r in ids:
        criterion = cell(r, "given")
        if _blank(criterion):
            report.error(f"{rel}: {cell(r, 'id')} has no Given/When/Then text")
        elif not re.search(r"\b(given|when|then|shall)\b", criterion, re.I):
            report.warn(f"{rel}: {cell(r, 'id')} is not written as Given/When/Then or EARS")
    for r in table_with(text, "concern"):
        if _blank(cell(r, "requirement")):
            report.error(f"{rel}: NFR '{cell(r, 'concern')}' is empty (write a number or 'n/a: reason')")
    if ctx.change["type"] == "fix" and _blank(section(text, "Problem")):
        report.error(f"{rel}: a fix must describe the problem and reproduction")
    return report


def check_design(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    _require_sections(text, rel, ["Solution overview", "Failure modes", "Rollout and rollback"], report)
    return report


def check_threat_model(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    threats = sorted({m for r in table_with(text, "id") for m in THREAT_RE.findall(cell(r, "id"))}, key=_natural)
    if not threats:
        report.error(f"{rel}: needs at least one threat with id T-n (or document why none apply as T-1 accepted)")
    mitigations = table_with(text, "verifiable")
    covered = {m for r in mitigations for m in THREAT_RE.findall(cell(r, "threat"))}
    for t in threats:
        if t not in covered:
            report.error(f"{rel}: {t} has no control in 'What are we going to do about it?'")
    for r in mitigations:
        if THREAT_RE.search(cell(r, "threat")) and _blank(cell(r, "verifiable")):
            report.error(f"{rel}: control for {cell(r, 'threat')} has no 'Verifiable by'")
    return report


def check_plan(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    trace_rows = table_with(text, "requirement")
    trace = " ".join(cell(r, "requirement") for r in trace_rows)
    trace_tests = {m for r in trace_rows
                   for m in AC_RE.findall(cell(r, "requirement")) + THREAT_RE.findall(cell(r, "requirement"))
                   if not _blank(cell(r, "test"))}
    for ac in ctx.ids("spec.md", "given", AC_RE):
        if ac not in trace:
            report.error(f"{rel}: {ac} from spec.md is missing in the traceability table")
        elif ac not in trace_tests:
            report.error(f"{rel}: {ac} has no planned test")
    threat_rows = table_with(ctx.read("threat-model.md"), "id")
    for t in sorted({m for r in threat_rows for m in THREAT_RE.findall(cell(r, "id"))}, key=_natural):
        if t not in trace:
            report.error(f"{rel}: {t} from threat-model.md is missing in the traceability table")
    tasks = [r for r in table_with(text, "done when") if not _blank(cell(r, "task"))]
    if not tasks:
        report.error(f"{rel}: needs at least one task")
    for r in tasks:
        if _blank(cell(r, "done when")):
            report.error(f"{rel}: task '{cell(r, 'task')}' has no 'Done when' check")
    return report


def check_verification(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    rows = {m: r for r in table_with(text, "evidence") for m in AC_RE.findall(cell(r, "id"))}
    test_files = _test_files(ctx)
    for ac in ctx.ids("spec.md", "given", AC_RE):
        r = rows.get(ac)
        if r is None:
            report.error(f"{rel}: {ac} from spec.md has no verification result")
            continue
        result = cell(r, "result").lower()
        if result not in PASS_RESULTS:
            report.error(f"{rel}: {ac} result is '{result or 'empty'}' (expected pass/verified/n/a)")
        evidence = cell(r, "evidence")
        if _blank(evidence):
            report.error(f"{rel}: {ac} has no evidence")
        elif test_files is not None:
            for name in re.findall(r"`([^`]+)`", evidence):
                if not any(name in content for content in test_files):
                    report.error(f"{rel}: {ac} cites test `{name}` not found under verification.test_paths")
    for r in table_with(text, "disposition"):
        if not _blank(cell(r, "finding")) and _blank(cell(r, "disposition")):
            report.error(f"{rel}: finding '{cell(r, 'finding')}' has no disposition")
    return report


def _test_files(ctx: Context) -> list[str] | None:
    globs = ctx.cfg.get("verification", {}).get("test_paths", [])
    if not globs:
        return None
    contents = []
    for pattern in globs:
        for f in ctx.root.glob(pattern):
            if f.is_file():
                contents.append(f.read_text(encoding="utf-8", errors="ignore"))
    return contents


def check_review(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    verdict = re.search(r"Verdict:\s*`?(changes-requested|ready-for-human-approval)`?\s*$", text, re.M | re.I)
    fresh = re.search(r"Fresh context[^:]*:\s*`?(yes|no)`?\s*$", text, re.M | re.I)
    if not verdict:
        report.error(f"{rel}: 'Verdict:' must be exactly changes-requested or ready-for-human-approval")
    elif verdict.group(1).lower() == "changes-requested":
        report.error(f"{rel}: verdict is changes-requested; address findings and review again")
    if not fresh or fresh.group(1).lower() != "yes":
        report.error(f"{rel}: review must be done from a fresh context ('Fresh context ...: yes')")
    if re.search(r"^- \[ \]", section(text, "Checklist"), re.M):
        report.error(f"{rel}: checklist has unchecked items")
    return report


def check_release(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    fields = {cell(r, "field").lower(): cell(r, "value") for r in table_with(text, "field")}
    for name in ("version", "artifacts and digests"):
        if _blank(fields.get(name, "")):
            report.error(f"{rel}: '{name}' is empty")
    _require_sections(text, rel, ["Rollout plan", "Rollback"], report)
    return report


def check_runbook(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    alerts = [r for r in table_with(text, "alert") if not _blank(cell(r, "alert"))]
    if not alerts:
        report.error(f"{rel}: needs at least one alert with its meaning and first action")
    _require_sections(text, rel, ["Safe mitigations"], report)
    return report


def check_adr(text: str, rel: str) -> Report:
    report = Report()
    options = re.findall(r"^\s*\d+\.\s+\S", section(text, "Options considered"), re.M)
    if len(options) < 2:
        report.error(f"{rel}: 'Options considered' needs at least two numbered options")
    _require_sections(text, rel, ["Decision", "Consequences"], report)
    return report


CHECKERS = {
    "spec.md": check_spec,
    "design.md": check_design,
    "threat-model.md": check_threat_model,
    "plan.md": check_plan,
    "verification.md": check_verification,
    "review.md": check_review,
    "release.md": check_release,
    "runbook.md": check_runbook,
}
