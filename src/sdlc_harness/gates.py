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
OPEN_RESULTS = {"blocked", "pending"}
# The skills tell teams to write prose in their own language, so the structure check cannot be English-only.
CRITERION_RE = re.compile(r"\b(given|when|then|shall|dad[oa]s?|cuando|entonces|debe|deberá)\b", re.I)
GUARDRAIL_TOPICS = [("a budget", r"budget|presupuesto"),
                    ("alert thresholds", r"alert|threshold|umbral|alarma"),
                    ("allocation tags", r"\btags?\b|etiqueta|allocation|label"),
                    ("an idle policy", r"idle|scale to zero|scale-to-zero|shut ?down|apag|inactiv")]
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
        elif not CRITERION_RE.search(criterion):
            report.warn(f"{rel}: {cell(r, 'id')} is not written as Given/When/Then or EARS "
                         f"(Dado/Cuando/Entonces also counts)")
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
        evidence = cell(r, "evidence")
        if result in OPEN_RESULTS:
            # An honest open state: the record stays truthful, but the phase still cannot advance.
            owner = re.search(r"owner:\s*([^\s,;|]+)(.*)", evidence, re.I)
            if not owner or _blank(owner.group(2)):
                report.error(f"{rel}: {ac} is '{result}' and must name an owner and a reason, e.g. "
                             f"'blocked - owner: rita - needs repository admin to protect the branch'")
            else:
                report.error(f"{rel}: {ac} is {result} (owner: {owner.group(1)}); verify cannot close until it "
                             f"passes, or record it as n/a with the reason")
            continue
        if result not in PASS_RESULTS:
            report.error(f"{rel}: {ac} result is '{result or 'empty'}' "
                         f"(expected pass/verified/n/a, or blocked/pending with an owner and a reason)")
        if _blank(evidence):
            report.error(f"{rel}: {ac} has no evidence")
        elif test_files is not None:
            for token in re.findall(r"`([^`]+)`", evidence):
                if problem := _evidence_token_problem(token, test_files, ctx.root):
                    report.error(f"{rel}: {ac} {problem}")
    for r in table_with(text, "disposition"):
        if not _blank(cell(r, "finding")) and _blank(cell(r, "disposition")):
            report.error(f"{rel}: finding '{cell(r, 'finding')}' has no disposition")
    return report


def _evidence_token_problem(token: str, test_files: list[str], root: Path) -> str | None:
    """What is wrong with one backticked token in a verification row, or None when it checks out.

    A backticked token is a test name, a repository path or a command. Test names can be whole sentences (vitest and
    jest name tests that way), so whitespace cannot tell a command apart; a command is marked with a leading `$ `,
    the shell convention. An unmarked token that is neither a test nor a file is the one thing this gate exists to
    catch: evidence that points at nothing.
    """
    if token.startswith("$ "):
        return None  # a command: as unverifiable as prose, and no weaker for being formatted
    if any(token in content for content in test_files):
        return None
    path, _, test = token.partition("::")  # pytest node ids: tests/test_x.py::test_y
    looks_like_path = "/" in path and not any(c.isspace() for c in path)
    if looks_like_path or (root / path).is_file():
        if not (root / path.split(":")[0]).exists():  # tolerate a trailing :line
            return f"cites `{path}`, which does not exist in the repository"
        if test and not any(test in content for content in test_files):
            return f"cites test `{test}` in `{path}`, not found under verification.test_paths"
        return None
    if re.fullmatch(r"[A-Za-z_][\w.]*", token):  # an identifier is plainly meant as a test name
        return f"cites test `{token}` not found under verification.test_paths"
    return (f"cites `{token}`, which is not a test under verification.test_paths nor a file in the repository "
            f"(write a command as `$ {token}` if that is what it is)")


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


def _decision(text: str, rel: str, allowed: tuple[str, ...], report: Report) -> str | None:
    m = re.search(r"^Decision:\s*`?([a-z-]+)`?\s*$", text, re.M | re.I)
    if not m or m.group(1).lower() not in allowed:
        report.error(f"{rel}: 'Decision:' must be one of {', '.join(allowed)}")
        return None
    return m.group(1).lower()


def _rows(text: str, prefix: str, key: str) -> list[dict]:
    return [r for r in table_with(text, prefix) if not _blank(cell(r, key))]


def check_discovery(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    _require_sections(text, rel, ["Problem", "Target users"], report)
    metrics = _rows(text, "baseline", "metric")
    if not metrics:
        report.error(f"{rel}: needs at least one success metric")
    for r in metrics:
        if _blank(cell(r, "target")) or _blank(cell(r, "measured")):
            report.error(f"{rel}: metric '{cell(r, 'metric')}' needs a target and how it is measured")
    if len(_rows(text, "effort", "option")) < 2:
        report.error(f"{rel}: compare at least two options (including 'Do nothing')")
    if _decision(text, rel, ("go", "no-go", "iterate"), report) == "no-go" and ctx.change["phase"] != "discover":
        report.error(f"{rel}: decision is no-go; the change cannot progress past discovery")
    return report


def check_ux(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    _require_sections(text, rel, ["User flows", "Validation"], report)
    screens = _rows(text, "empty", "screen")
    if not screens:
        report.error(f"{rel}: list at least one screen or component with its states")
    for r in screens:
        missing = [s for s in ("empty", "loading", "error", "success") if _blank(cell(r, s))]
        if missing:
            report.error(f"{rel}: '{cell(r, 'screen')}' does not define states {missing} (write 'n/a' if not applicable)")
    if re.search(r"^- \[ \]", section(text, "Accessibility"), re.M):
        report.error(f"{rel}: accessibility checklist has unchecked items")
    return report


def check_data(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    changes = _rows(text, "classification", "entity")
    if not changes:
        report.error(f"{rel}: list at least one data change")
    for r in changes:
        cls = cell(r, "classification").lower()
        if not any(c in cls for c in ("public", "internal", "confidential", "restricted")):
            report.error(f"{rel}: '{cell(r, 'entity')}' needs a classification")
        if _blank(cell(r, "owner")):
            report.error(f"{rel}: '{cell(r, 'entity')}' needs an owner")
    _require_sections(text, rel, ["Migrations", "Rollback", "Retention and lineage"], report)
    if "personal-data" in ctx.change.get("scopes", []):
        answers = {cell(r, "question").lower(): cell(r, "answer") for r in table_with(text, "question")}
        if not answers:
            report.error(f"{rel}: personal-data scope requires the privacy impact table")
        for question, answer in answers.items():
            if _blank(answer):
                report.error(f"{rel}: privacy question '{question}' is unanswered")
    return report


def check_cost(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    rows = _rows(text, "monthly", "component")
    if not rows:
        report.error(f"{rel}: estimate at least one component")
    for r in rows:
        if not re.search(r"\d", cell(r, "monthly")):
            report.error(f"{rel}: '{cell(r, 'component')}' has no numeric monthly cost")
    # The amount may carry a currency before or after it ("USD 77.40", "77,40 USD", "$77.40"): any digit will do.
    if not re.search(r"^Total monthly \(production\):.*\d", text, re.M):
        report.error(f"{rel}: 'Total monthly (production):' needs an amount "
                     f"(e.g. 'Total monthly (production): USD 77.40')")
    _require_sections(text, rel, ["Assumptions"], report)
    guardrails = section(text, "Guardrails").lower()
    missing = [name for name, pattern in GUARDRAIL_TOPICS if not re.search(pattern, guardrails)]
    if missing:
        report.error(f"{rel}: Guardrails does not cover {', '.join(missing)} "
                     f"(state a monthly budget, the alert thresholds, the cost allocation tags and what is "
                     f"shut down or scaled to zero when idle)")
    return report


def check_ai_risk(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    _require_sections(text, rel, ["Use case", "Risk classification", "Human oversight", "Monitoring"], report)
    risks = [r for r in table_with(text, "mitigation") if re.search(r"\bR-\d+\b", cell(r, "id"))]
    if not risks:
        report.error(f"{rel}: needs at least one risk with id R-n")
    for r in risks:
        if _blank(cell(r, "mitigation")) or _blank(cell(r, "verifiable")):
            report.error(f"{rel}: {cell(r, 'id')} needs a mitigation and how it is verified")
    evals = _rows(text, "threshold", "eval")
    if not evals:
        report.error(f"{rel}: define at least one evaluation with a threshold")
    for r in evals:
        if _blank(cell(r, "threshold")):
            report.error(f"{rel}: eval '{cell(r, 'eval')}' has no threshold")
        if ctx.change["phase"] in ("review", "release", "operate", "done") and _blank(cell(r, "result")):
            report.error(f"{rel}: eval '{cell(r, 'eval')}' has no result before review")
    return report


def check_outcome(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    rows = _rows(text, "actual", "metric")
    if not rows:
        report.error(f"{rel}: report at least one success metric")
    for r in rows:
        if _blank(cell(r, "actual")):
            report.error(f"{rel}: metric '{cell(r, 'metric')}' has no actual value")
    discovery = ctx.read("discovery.md")
    for r in _rows(discovery, "baseline", "metric"):
        if cell(r, "metric") not in {cell(x, "metric") for x in rows}:
            report.error(f"{rel}: success metric '{cell(r, 'metric')}' from discovery.md is not reported")
    _decision(text, rel, ("keep", "iterate", "rollback", "retire"), report)
    return report


def check_retirement(text: str, rel: str, ctx: Context) -> Report:
    report = Report()
    _require_sections(text, rel, ["What is retired", "Data disposition", "Contracts and dependencies",
                                  "Infrastructure teardown", "Rollback"], report)
    consumers = _rows(text, "migration", "consumer")
    if not consumers:
        report.error(f"{rel}: list consumers (write 'none found' with how that was checked)")
    for r in consumers:
        if _blank(cell(r, "migration")) and "none" not in cell(r, "consumer").lower():
            report.error(f"{rel}: consumer '{cell(r, 'consumer')}' has no migration path")
    dates = {cell(r, "milestone").lower(): cell(r, "date") for r in table_with(text, "milestone")}
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", dates.get("sunset", "")):
        report.error(f"{rel}: sunset date must be YYYY-MM-DD")
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
    "discovery.md": check_discovery,
    "ux.md": check_ux,
    "data.md": check_data,
    "cost.md": check_cost,
    "ai-risk.md": check_ai_risk,
    "outcome.md": check_outcome,
    "retirement.md": check_retirement,
}
