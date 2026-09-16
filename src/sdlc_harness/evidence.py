"""Tool-agnostic sensor evidence: SARIF 2.1.0 findings and CycloneDX SBOMs.

Any scanner that emits SARIF (Semgrep, CodeQL, Trivy, Checkov, gitleaks, KICS, ...) and any SBOM generator that emits
CycloneDX JSON (Syft, cdxgen, Trivy) plugs in without harness code. The policy lives in harness.toml / profiles:
required evidence kinds, severity threshold, license deny list. Exceptions expire and name an approver.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
from pathlib import Path

from .core import Report, load_toml

SEVERITIES = ["low", "medium", "high", "critical"]
LEVEL_SEVERITY = {"error": "high", "warning": "medium", "note": "low", "none": "low"}
EXCEPTIONS_FILE = ".harness/exceptions.toml"


def _severity(result: dict, rules: dict) -> str:
    props = dict(rules.get(result.get("ruleId"), {}).get("properties", {}))
    props.update(result.get("properties", {}))
    score = props.get("security-severity")
    try:
        value = float(score)
    except (TypeError, ValueError):
        tags = " ".join(props.get("tags", [])).lower()
        for sev in reversed(SEVERITIES):
            if sev in tags:
                return sev
        level = result.get("level") or rules.get(result.get("ruleId"), {}).get("defaultConfiguration", {}).get("level")
        return LEVEL_SEVERITY.get(level or "warning", "medium")
    return "critical" if value >= 9 else "high" if value >= 7 else "medium" if value >= 4 else "low"


def _location(result: dict) -> str:
    for loc in result.get("locations", []):
        uri = loc.get("physicalLocation", {}).get("artifactLocation", {}).get("uri")
        if uri:
            return uri.removeprefix("file://").removeprefix("./")
    return ""


def load_exceptions(root: Path, report: Report) -> list[dict]:
    path = root / EXCEPTIONS_FILE
    if not path.exists():
        return []
    today = dt.date.today()
    valid = []
    for e in load_toml(path).get("exception", []):
        missing = [k for k in ("rule", "reason", "approver", "expires") if not e.get(k)]
        if missing:
            report.error(f"{EXCEPTIONS_FILE}: exception for '{e.get('rule')}' lacks {missing}")
            continue
        expires = e["expires"] if isinstance(e["expires"], dt.date) else dt.date.fromisoformat(str(e["expires"]))
        if expires < today:
            report.error(f"{EXCEPTIONS_FILE}: exception for '{e['rule']}' expired on {expires}; renew or fix")
            continue
        if (expires - today).days > 180:
            report.warn(f"{EXCEPTIONS_FILE}: exception for '{e['rule']}' lasts more than 180 days")
        valid.append(e)
    return valid


def _excepted(rule: str, location: str, exceptions: list[dict]) -> dict | None:
    for e in exceptions:
        if fnmatch.fnmatch(rule, e["rule"]) and fnmatch.fnmatch(location or "", e.get("path", "*")):
            return e
    return None


def check_sarif(path: Path, threshold: str, exceptions: list[dict], report: Report, floor: str = "low") -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.error(f"{path.name}: not valid SARIF JSON ({exc})")
        return 0
    limit = SEVERITIES.index(threshold)
    count = 0
    for run in data.get("runs", []):
        tool = run.get("tool", {}).get("driver", {}).get("name", "tool")
        rules = {r.get("id"): r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
        for result in run.get("results", []):
            count += 1
            if result.get("suppressions") or result.get("baselineState") == "absent":
                continue
            sev = max(_severity(result, rules), floor, key=SEVERITIES.index)
            if SEVERITIES.index(sev) < limit:
                continue
            rule, loc = result.get("ruleId", "?"), _location(result)
            msg = next(iter((result.get("message", {}).get("text") or "").splitlines()), "")[:100]
            if e := _excepted(rule, loc, exceptions):
                report.warn(f"{tool}: {sev} {rule} at {loc} excepted until {e['expires']} ({e['reason']})")
            else:
                report.error(f"{tool}: {sev} {rule} at {loc or 'n/a'}: {msg}")
    return count


def _licenses(component: dict) -> list[str]:
    out = []
    for lic in component.get("licenses", []):
        if "expression" in lic:
            out.append(lic["expression"])
        else:
            inner = lic.get("license", {})
            out.append(inner.get("id") or inner.get("name") or "")
    return [x for x in out if x]


def check_sbom(path: Path, deny: list[str], exceptions: list[dict], report: Report) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.error(f"{path.name}: not valid CycloneDX JSON ({exc})")
        return 0
    if data.get("bomFormat") != "CycloneDX":
        report.error(f"{path.name}: bomFormat must be CycloneDX")
        return 0
    components = data.get("components", [])
    if not components:
        report.warn(f"{path.name}: SBOM has no components")
    for c in components:
        ref = c.get("purl") or f"{c.get('name')}@{c.get('version')}"
        for expression in _licenses(c):
            for denied in deny:
                if denied in expression.replace("(", " ").replace(")", " ").split():
                    rule = f"license:{denied}"
                    if e := _excepted(rule, ref, exceptions):
                        report.warn(f"{ref}: denied license {denied} excepted until {e['expires']}")
                    else:
                        report.error(f"{ref}: license {expression} is denied by policy")
    return len(components)


def check(root: Path, cfg: dict, directory: str | None = None, require: list[str] | None = None) -> Report:
    report = Report()
    ev_cfg = cfg.get("evidence", {})
    base = root / (directory or ev_cfg.get("dir", "sdlc-evidence"))
    required = require if require is not None else cfg["_profile"].get("sensors", {}).get("require_evidence", [])
    threshold = ev_cfg.get("fail_on", "high")
    if threshold not in SEVERITIES:
        report.error(f"harness.toml [evidence] fail_on must be one of {SEVERITIES}")
        return report
    exceptions = load_exceptions(root, report)
    files = sorted(base.glob("*")) if base.is_dir() else []
    for kind in required:
        pattern = "sbom*.json" if kind == "sbom" else f"{kind}*.sarif"
        if not any(fnmatch.fnmatch(f.name, pattern) for f in files):
            report.error(f"missing evidence '{kind}': expected {base.relative_to(root)}/{pattern}")
    for f in files:
        if f.suffix == ".sarif":
            # Secret scanners rarely set severities; any unsuppressed secret is critical.
            floor = "critical" if f.name.startswith("secrets") else "low"
            n = check_sarif(f, threshold, exceptions, report, floor)
            print(f"{f.name}: {n} result(s)")
        elif f.name.startswith("sbom") and f.suffix == ".json":
            n = check_sbom(f, ev_cfg.get("license_deny", []), exceptions, report)
            print(f"{f.name}: {n} component(s)")
    return report
