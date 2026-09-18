"""Change records: rules, gates and phase transitions."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import tomllib
from pathlib import Path

from . import audit, gates, receipts
from .core import PHASES, PLACEHOLDER, RISKS, SCOPES, TYPES, HarnessError, Report, load_config, load_toml, paths

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def required_rules(change: dict, rules: list[dict], upto_phase: str | None = None) -> list[dict]:
    """Rules whose producing phase is completed (or will be, when `upto_phase` is given)."""
    phase_idx = PHASES.index(upto_phase or change["phase"])
    risk_idx = RISKS.index(change["risk"])
    out = []
    for rule in rules:
        if change["type"] not in rule.get("types", TYPES):
            continue
        if risk_idx < RISKS.index(rule.get("min_risk", "low")):
            continue
        if "scopes" in rule and not set(rule["scopes"]) & set(change.get("scopes", [])):
            continue
        if upto_phase is None and phase_idx <= PHASES.index(rule["phase"]):
            continue
        out.append(rule)
    return out


def load_change(change_dir: Path, report: Report) -> dict | None:
    meta_path = change_dir / "change.toml"
    if not meta_path.exists():
        report.error(f"{change_dir.name}: missing change.toml")
        return None
    try:
        change = load_toml(meta_path)
    except tomllib.TOMLDecodeError as exc:
        report.error(f"{meta_path}: invalid TOML ({exc})")
        return None
    ok = True
    for key, allowed in (("type", TYPES), ("risk", RISKS), ("phase", PHASES)):
        if change.get(key) not in allowed:
            report.error(f"{change_dir.name}/change.toml: '{key}' must be one of {allowed}")
            ok = False
    if unknown := set(change.get("scopes", [])) - set(SCOPES):
        report.error(f"{change_dir.name}/change.toml: unknown scopes {sorted(unknown)} (allowed: {SCOPES})")
        ok = False
    if not isinstance(change.get("ai_assisted"), bool):
        report.error(f"{change_dir.name}/change.toml: 'ai_assisted' must be true or false (AI disclosure control)")
        ok = False
    return change if ok else None


def check_change(root: Path, change_dir: Path, cfg: dict) -> Report:
    report = Report()
    change = load_change(change_dir, report)
    if change is None:
        return report
    return report.extend(check_against(root, change_dir, cfg, change))


def check_against(root: Path, change_dir: Path, cfg: dict, change: dict) -> Report:
    """Gate results for `change` as described by the given metadata (used with a hypothetical phase by `status`)."""
    report = Report()
    rel = change_dir.relative_to(root).as_posix()
    ctx = gates.Context(root, change_dir, cfg, change)
    for rule in required_rules(change, cfg["_profile"].get("rules", [])):
        if rule["artifact"] == "adr":
            _check_adrs(root, cfg, change_dir, change, rule, report)
            continue
        path = change_dir / rule["artifact"]
        artifact = f"{rel}/{rule['artifact']}"
        if not path.exists():
            report.error(f"{artifact}: required after phase '{rule['phase']}'")
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER in text:
            report.error(f"{artifact}: unfilled sections ({PLACEHOLDER})")
            continue
        if checker := gates.CHECKERS.get(rule["artifact"]):
            report.extend(checker(text, artifact, ctx))
        if rule.get("approve"):
            report.extend(receipts.check(root, cfg, change_dir, artifact))
    log = change_dir / audit.AUDIT_FILE
    if log.exists():
        report.extend(audit.verify_chain(root, log))
    return report


def _check_adrs(root: Path, cfg: dict, change_dir: Path, change: dict, rule: dict, report: Report) -> None:
    adrs = change.get("adrs", [])
    if not adrs:
        report.error(f"{change_dir.name}: phase '{rule['phase']}' requires at least one ADR in `adrs`")
    for adr in adrs:
        path = root / adr
        if not path.exists():
            report.error(f"{change_dir.name}: referenced ADR not found: {adr}")
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER in text:
            report.error(f"{adr}: unfilled sections ({PLACEHOLDER})")
            continue
        report.extend(gates.check_adr(text, adr))
        if rule.get("approve"):
            report.extend(receipts.check(root, cfg, change_dir, adr))


def change_dir(root: Path, cfg: dict, change_id: str) -> Path:
    d = root / paths(cfg)["changes"] / change_id
    if not (d / "change.toml").exists():
        raise HarnessError(f"change not found: {change_id}")
    return d


def start_phase(change: dict, rules: list[dict]) -> str:
    """First phase with a required artifact, so small changes skip discovery ceremony."""
    phases = [r["phase"] for r in required_rules(change, rules, upto_phase="done")]
    first = min(phases, key=PHASES.index) if phases else "spec"
    return first if PHASES.index(first) < PHASES.index("spec") else "spec"


def new(root: Path, change_type: str, slug: str, risk: str, ai_assisted: bool, scopes: list[str] | None = None) -> int:
    if not SLUG_RE.match(slug):
        raise HarnessError("slug must be kebab-case")
    cfg = load_config(root)
    p = paths(cfg)
    change_id = f"{dt.date.today().isoformat()}-{slug}"
    d = root / p["changes"] / change_id
    if d.exists():
        raise HarnessError(f"change already exists: {d.relative_to(root)}")
    scopes = scopes or []
    if unknown := set(scopes) - set(SCOPES):
        raise HarnessError(f"unknown scopes {sorted(unknown)} (allowed: {SCOPES})")
    rules = cfg["_profile"].get("rules", [])
    change = {"type": change_type, "risk": risk, "scopes": scopes}
    change["phase"] = start_phase(change, rules)
    d.mkdir(parents=True)
    (d / "change.toml").write_text(
        f'id = "{change_id}"\ntype = "{change_type}"\nrisk = "{risk}"\nphase = "{change["phase"]}"\n'
        f"scopes = {json.dumps(scopes)}\n"
        f"ai_assisted = {'true' if ai_assisted else 'false'}\nadrs = []\n",
        encoding="utf-8",
    )
    created = []
    for rule in required_rules(change, rules, upto_phase="done"):
        tpl = root / p["templates"] / rule["artifact"]
        if rule["artifact"] != "adr" and tpl.exists() and not (d / rule["artifact"]).exists():
            shutil.copy2(tpl, d / rule["artifact"])
            created.append(rule["artifact"])
    audit.append(root, d, "created", type=change_type, risk=risk, scopes=scopes, ai_assisted=ai_assisted)
    print(f"created {d.relative_to(root)}: change.toml {' '.join(created)}")
    return 0


def phase(root: Path, change_id: str, target: str) -> int:
    cfg = load_config(root)
    d = change_dir(root, cfg, change_id)
    meta = d / "change.toml"
    text = meta.read_text(encoding="utf-8")
    current = load_toml(meta).get("phase")
    if current in PHASES and PHASES.index(target) > PHASES.index(current) + 1:
        raise HarnessError(f"cannot skip phases: {current} -> {target}")
    meta.write_text(re.sub(r'^phase = ".*"$', f'phase = "{target}"', text, flags=re.M), encoding="utf-8")
    report = check_change(root, d, cfg)
    if report.errors:
        meta.write_text(text, encoding="utf-8")
        audit.append(root, d, "phase_blocked", **{"from": current, "to": target, "errors": len(report.errors)})
        print(f"gate blocked: {change_id} stays in '{current}'. "
              f"Run `python3 .harness/sdlc.pyz status --change {change_id}` for what is missing and who approves.")
    else:
        audit.append(root, d, "phase", **{"from": current, "to": target})
        print(f"{change_id}: {current} -> {target}")
    return report.print()
