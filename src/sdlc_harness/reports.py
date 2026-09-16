"""Visibility: traceability per change, delivery flow from audit logs, and DORA-style metrics from git.

All data comes from the repository (change records, audit logs, receipts, tags, commits), so reports work offline
and anyone can reproduce them. DORA metrics use release tags as the deployment proxy; see `dora()` for definitions.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import statistics
from pathlib import Path

from . import gates, receipts
from .core import PHASES, cell, git, load_toml, paths, sha256_file, table_with

UTC = dt.timezone.utc


def parse_since(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime(1970, 1, 1, tzinfo=UTC)
    if m := re.fullmatch(r"(\d+)d", value):
        return dt.datetime.now(UTC) - dt.timedelta(days=int(m.group(1)))
    parsed = dt.datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _ts(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


# --------------------------------------------------------------------------- traceability

def trace(root: Path, cfg: dict, change_dir: Path) -> dict:
    change = load_toml(change_dir / "change.toml")
    read = lambda name: (change_dir / name).read_text(encoding="utf-8") if (change_dir / name).exists() else ""  # noqa: E731
    spec, plan, verification, threat_model = read("spec.md"), read("plan.md"), read("verification.md"), read("threat-model.md")

    planned: dict[str, list[str]] = {}
    for r in table_with(plan, "requirement"):
        for ident in re.findall(r"\b(?:AC|T)-\d+\b", cell(r, "requirement")):
            planned.setdefault(ident, []).append(cell(r, "test"))
    verified = {m: r for r in table_with(verification, "evidence") for m in gates.AC_RE.findall(cell(r, "id"))}

    criteria = []
    for r in table_with(spec, "given"):
        for ac in gates.AC_RE.findall(cell(r, "id")):
            v = verified.get(ac, {})
            criteria.append({"id": ac, "criterion": cell(r, "given"), "tests": planned.get(ac, []),
                             "result": cell(v, "result") if v else "", "evidence": cell(v, "evidence") if v else ""})
    controls = {m: r for r in table_with(threat_model, "verifiable") for m in gates.THREAT_RE.findall(cell(r, "threat"))}
    threats = []
    for r in table_with(threat_model, "id"):
        for t in gates.THREAT_RE.findall(cell(r, "id")):
            c = controls.get(t, {})
            threats.append({"id": t, "threat": cell(r, "threat"), "control": cell(c, "control") if c else "",
                            "verifiable_by": cell(c, "verifiable") if c else "", "tests": planned.get(t, [])})

    approvals = []
    for e in receipts.load(change_dir):
        path = root / e["artifact"]
        state = "valid" if path.exists() and sha256_file(path) == e["sha256"] else "stale"
        approvals.append({"artifact": e["artifact"], "approver": e["approver"], "role": e["role"],
                          "approved_at": e["approved_at"], "state": state})

    rel = change_dir.relative_to(root).as_posix()
    log = git(root, "log", "--format=%H%x09%aI%x09%s", f"--grep=^Change: {change['id']}$", check=False)
    log_paths = git(root, "log", "--format=%H%x09%aI%x09%s", "--", rel, check=False)
    commits = {}
    for line in (log + "\n" + log_paths).splitlines():
        if line.strip():
            sha, date, subject = line.split("\t", 2)
            commits[sha] = {"sha": sha[:10], "date": date, "subject": subject}
    release = {cell(r, "field").lower(): cell(r, "value") for r in table_with(read("release.md"), "field")}
    return {
        "change": {k: change.get(k) for k in ("id", "type", "risk", "phase", "scopes", "ai_assisted")},
        "criteria": criteria, "threats": threats, "adrs": change.get("adrs", []), "approvals": approvals,
        "commits": sorted(commits.values(), key=lambda c: c["date"]), "release": release.get("version", ""),
        "gaps": [f"{c['id']} has no planned test" for c in criteria if not c["tests"]]
                + [f"{c['id']} not verified" for c in criteria if c["result"].lower() not in gates.PASS_RESULTS]
                + [f"{t['id']} has no control" for t in threats if not t["control"]]
                + [f"approval of {a['artifact']} by {a['approver']} is stale" for a in approvals if a["state"] == "stale"],
    }


# --------------------------------------------------------------------------- flow

def flow(root: Path, cfg: dict, since: dt.datetime) -> dict:
    changes_dir = root / paths(cfg)["changes"]
    rows, blocks_by_phase, approvals_by_role = [], {}, {}
    for d in sorted(p for p in changes_dir.iterdir() if (p / "audit.jsonl").exists()) if changes_dir.is_dir() else []:
        events = [json.loads(line) for line in (d / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line]
        created = next((_ts(e["ts"]) for e in events if e["event"] == "created"), _ts(events[0]["ts"]))
        if created < since:
            continue
        meta = load_toml(d / "change.toml")
        entered = {meta.get("phase"): created}
        time_in_phase: dict[str, float] = {}
        blocked_since: dict[str, dt.datetime] = {}
        blocked_hours, blocks = 0.0, 0
        current_at = created
        for e in events:
            ts = _ts(e["ts"])
            if e["event"] == "phase":
                time_in_phase[e["from"]] = time_in_phase.get(e["from"], 0) + (ts - current_at).total_seconds() / 3600
                current_at = ts
                entered[e["to"]] = ts
                if first := blocked_since.pop(e["to"], None):
                    blocked_hours += (ts - first).total_seconds() / 3600
            elif e["event"] == "phase_blocked":
                blocks += 1
                blocks_by_phase[e["to"]] = blocks_by_phase.get(e["to"], 0) + 1
                blocked_since.setdefault(e["to"], ts)
            elif e["event"] == "approved":
                approvals_by_role[e["role"]] = approvals_by_role.get(e["role"], 0) + 1
        done_at = entered.get("done")
        lead_days = ((done_at or dt.datetime.now(UTC)) - created).total_seconds() / 86400
        rows.append({"id": meta.get("id"), "type": meta.get("type"), "risk": meta.get("risk"),
                     "phase": meta.get("phase"), "ai_assisted": meta.get("ai_assisted"), "done": done_at is not None,
                     "lead_time_days": round(lead_days, 2), "blocked_hours": round(blocked_hours, 2),
                     "gate_blocks": blocks,
                     "hours_in_phase": {k: round(v, 2) for k, v in sorted(time_in_phase.items(),
                                                                          key=lambda kv: PHASES.index(kv[0]))}})
    done = [r for r in rows if r["done"]]
    return {
        "since": since.date().isoformat(), "changes": rows,
        "summary": {
            "changes": len(rows), "done": len(done),
            "median_lead_time_days_done": _median([r["lead_time_days"] for r in done]),
            "ai_assisted_share": round(sum(1 for r in rows if r["ai_assisted"]) / len(rows), 2) if rows else None,
            "gate_blocks_by_target_phase": blocks_by_phase, "approvals_by_role": approvals_by_role,
            "median_blocked_hours": _median([r["blocked_hours"] for r in rows if r["gate_blocks"]]),
        },
    }


# --------------------------------------------------------------------------- DORA

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")
FIX_RE = re.compile(r"^(fix|revert)(\(|!|:)|^Revert ")


def dora(root: Path, since: dt.datetime, tag_glob: str = "v*", window_days: int = 7) -> dict:
    """Release tags are deployments. A release is *failed* when the next release is a patch that only contains
    fix/revert commits and ships within `window_days`; that next release is *rework*. Recovery time is the time
    between the failed release and its fixing release. Lead time runs from commit time to the release tag."""
    raw = git(root, "for-each-ref", "--sort=creatordate", "--format=%(refname:short)%09%(creatordate:iso-strict)",
              f"refs/tags/{tag_glob}", check=False)
    tags = [(name, _ts(date)) for name, date in (line.split("\t") for line in raw.splitlines() if line)]
    releases, previous = [], None
    for name, date in tags:
        rng = f"{previous[0]}..{name}" if previous else name
        commits = [line.split("\t", 1) for line in
                   git(root, "log", "--no-merges", "--format=%cI%x09%s", rng, check=False).splitlines() if line]
        releases.append({"tag": name, "date": date, "commits": commits, "previous": previous})
        previous = (name, date)
    in_window = [r for r in releases if r["date"] >= since]

    lead_times, failed, recoveries, rework = [], set(), [], []
    for r in in_window:
        lead_times += [(r["date"] - _ts(c[0])).total_seconds() / 3600 for c in r["commits"]]
        prev = r["previous"]
        cur_v, prev_v = SEMVER_RE.match(r["tag"]), SEMVER_RE.match(prev[0]) if prev else None
        is_patch = bool(cur_v and prev_v and cur_v.group(1, 2) == prev_v.group(1, 2))
        only_fixes = bool(r["commits"]) and all(FIX_RE.match(c[1]) for c in r["commits"])
        if prev and is_patch and only_fixes and (r["date"] - prev[1]).days <= window_days:
            failed.add(prev[0])
            rework.append(r["tag"])
            recoveries.append((r["date"] - prev[1]).total_seconds() / 3600)
    weeks = max((dt.datetime.now(UTC) - max(since, releases[0]["date"] if releases else since)).days / 7, 1)
    count = len(in_window)
    return {
        "since": since.date().isoformat(), "releases": count,
        "deployment_frequency_per_week": round(count / weeks, 2),
        "median_lead_time_hours": _median(lead_times),
        "change_failure_rate": round(len([r for r in in_window if r["tag"] in failed]) / count, 2) if count else None,
        "median_failed_deployment_recovery_hours": _median(recoveries),
        "rework_rate": round(len(rework) / count, 2) if count else None,
        "failed_releases": sorted(failed), "rework_releases": rework,
        "definitions": "deployments = release tags; failure = followed by a fix-only patch release within "
                       f"{window_days} days; lead time = commit to tag",
    }


# --------------------------------------------------------------------------- rendering

def render(kind: str, data: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, default=str) + "\n"
    sections = _sections(kind, data)
    if fmt == "md":
        out = [f"# sdlc report: {kind}", ""]
        for title, rows in sections:
            out += [f"## {title}", ""]
            if isinstance(rows, str):
                out += [rows, ""]
                continue
            if not rows:
                out += ["_none_", ""]
                continue
            headers = list(rows[0])
            out += ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
            out += ["| " + " | ".join(str(r[h]).replace("|", "\\|") for h in headers) + " |" for r in rows]
            out.append("")
        return "\n".join(out)
    parts = []
    for title, rows in sections:
        parts.append(f"<h2>{html.escape(title)}</h2>")
        if isinstance(rows, str):
            parts.append(f"<p>{html.escape(rows)}</p>")
        elif not rows:
            parts.append("<p class=muted>none</p>")
        else:
            headers = list(rows[0])
            head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
            body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r[h]))}</td>" for h in headers) + "</tr>"
                           for r in rows)
            parts.append(f"<div class=scroll><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")
    return HTML.format(title=html.escape(f"sdlc report: {kind}"), body="\n".join(parts),
                       generated=dt.datetime.now(UTC).replace(microsecond=0).isoformat())


def _sections(kind: str, data: dict) -> list[tuple[str, list[dict] | str]]:
    if kind == "trace":
        c = data["change"]
        return [
            ("Change", [c | {"scopes": ", ".join(c.get("scopes") or []), "release": data["release"]}]),
            ("Gaps", [{"gap": g} for g in data["gaps"]]),
            ("Acceptance criteria", [r | {"tests": ", ".join(r["tests"])} for r in data["criteria"]]),
            ("Threats", [r | {"tests": ", ".join(r["tests"])} for r in data["threats"]]),
            ("ADRs", [{"adr": a} for a in data["adrs"]]),
            ("Approvals", data["approvals"]),
            ("Commits", data["commits"]),
        ]
    if kind == "flow":
        s = data["summary"]
        summary = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in s.items()}
        return [("Summary", [summary]),
                ("Changes", [r | {"hours_in_phase": json.dumps(r["hours_in_phase"])} for r in data["changes"]])]
    return [("DORA metrics", [{k: v for k, v in data.items() if not isinstance(v, list)}]),
            ("Failed releases", [{"tag": t} for t in data["failed_releases"]]),
            ("Rework releases", [{"tag": t} for t in data["rework_releases"]])]


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#ffffff; --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; --head:#f6f8fa; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#3d444d; --head:#151b23; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1100px; margin:0 auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:16px; margin:28px 0 8px; }}
.muted {{ color:var(--muted); }} .scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; }}
th, td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ background:var(--head); font-weight:600; }}
</style></head>
<body><main><h1>{title}</h1><p class=muted>Generated {generated} from repository data.</p>
{body}
</main></body></html>
"""
