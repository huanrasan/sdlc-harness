"""`sdlc status`: one screen with where each change stands and what the next action is.

It answers the three questions people and agents keep asking: what is missing, who has to approve, and which command
to run next. Everything is derived from the same rules the gates use, so status never disagrees with `check`.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import authority, changes, receipts
from .core import PHASES, PLACEHOLDER, VENDORED_CLI, Report, paths, sha256_file


def _next_phase(phase: str) -> str | None:
    idx = PHASES.index(phase)
    return PHASES[idx + 1] if idx + 1 < len(PHASES) else None


def _pending_approvals(root: Path, cfg: dict, change_dir: Path, change: dict, upto: str) -> list[dict]:
    pending = []
    rules = cfg["_profile"].get("rules", [])
    for rule in changes.required_rules(change, rules, upto_phase=upto):
        if not rule.get("approve") or PHASES.index(rule["phase"]) >= PHASES.index(upto):
            continue
        artifacts = change.get("adrs", []) if rule["artifact"] == "adr" else \
            [f"{change_dir.relative_to(root).as_posix()}/{rule['artifact']}"]
        for artifact in artifacts:
            path = root / artifact
            if not path.is_file() or PLACEHOLDER in path.read_text(encoding="utf-8"):
                continue  # it cannot be approved until it is written
            key = authority.artifact_key(cfg, artifact)
            roles = authority.approver_roles(cfg, key)
            digest = sha256_file(path)
            valid = [e for e in receipts.load(change_dir)
                     if e["artifact"] == artifact and e["sha256"] == digest and e["role"] in roles]
            if valid:
                continue
            stale = [e["approver"] for e in receipts.load(change_dir) if e["artifact"] == artifact]
            members = sorted({m.lstrip("@") for role in roles for m in authority.roles(cfg).get(role, [])})
            pending.append({"artifact": artifact, "roles": roles, "who": members,
                            "state": "stale (content changed after approval)" if stale else "not approved"})
    return pending


def collect(root: Path, cfg: dict, only_change: str | None = None) -> dict:
    base = root / paths(cfg)["changes"]
    dirs = sorted(p for p in base.iterdir() if (p / "change.toml").exists()) if base.is_dir() else []
    if only_change:
        dirs = [changes.change_dir(root, cfg, only_change)]
    out = []
    for d in dirs:
        report = Report()
        change = changes.load_change(d, report)
        if change is None:
            out.append({"id": d.name, "errors": report.errors})
            continue
        current = changes.check_change(root, d, cfg)
        target = _next_phase(change["phase"])
        blocking, pending = [], []
        if target:
            hypothetical = {**change, "phase": target}
            blocking = changes.check_against(root, d, cfg, hypothetical).errors
            pending = _pending_approvals(root, cfg, d, change, target)
        approvals = [{"artifact": e["artifact"], "approver": e["approver"], "role": e["role"],
                      "valid": (root / e["artifact"]).is_file() and sha256_file(root / e["artifact"]) == e["sha256"]}
                     for e in receipts.load(d)]
        approval_noise = ("requires approval by one of roles", "is stale (content changed)")
        out.append({
            "id": change.get("id", d.name), "type": change.get("type"), "risk": change.get("risk"),
            "scopes": change.get("scopes", []), "phase": change["phase"], "next_phase": target,
            "ai_assisted": change.get("ai_assisted"),
            "errors_now": current.errors,
            "blocking_next": [e for e in blocking if not any(n in e for n in approval_noise)],
            "pending_approvals": pending,
            "approvals": approvals,
            "next_command": _next_command(change, target, blocking, pending),
        })
    return {"profile": cfg.get("harness", {}).get("profile"), "changes": out}


def _next_command(change: dict, target: str | None, blocking: list[str], pending: list[dict]) -> str:
    cli = f"python3 {VENDORED_CLI}"
    if target is None:
        return "nothing: the change is done"
    if pending:
        p = pending[0]
        who = ", ".join(p["who"]) or "nobody in the roster yet: add members to .harness/roster.toml"
        return (f"a human ({who}) runs: {cli} approve {change['id']} "
                f"{p['artifact'].rsplit('/', 1)[-1] if p['artifact'].startswith('docs/changes/') else p['artifact']} "
                f"--as <username> --role {p['roles'][0]}")
    if blocking:
        return f"fix the evidence listed above, then: {cli} phase {change['id']} {target}"
    return f"{cli} phase {change['id']} {target}"


def render(data: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, indent=2) + "\n"
    if not data["changes"]:
        return ("No change records yet.\n"
                f"Start one with: python3 {VENDORED_CLI} new <fix|feature|architecture|retirement> <slug> "
                "--risk <low|medium|high> [--scope ui,api,data,personal-data,infra,ai]\n")
    lines = [f"profile: {data['profile']}", ""]
    for c in data["changes"]:
        if "errors" in c:
            lines += [f"{c['id']}: invalid change record", *[f"  ! {e}" for e in c["errors"]], ""]
            continue
        scopes = f" scopes={','.join(c['scopes'])}" if c["scopes"] else ""
        arrow = f" -> {c['next_phase']}" if c["next_phase"] else " (done)"
        lines.append(f"{c['id']}  [{c['type']} risk={c['risk']}{scopes}]  phase: {c['phase']}{arrow}")
        for e in c["errors_now"]:
            lines.append(f"  ! current phase: {e}")
        for e in c["blocking_next"]:
            lines.append(f"  - blocks {c['next_phase']}: {e}")
        for p in c["pending_approvals"]:
            who = ", ".join(p["who"]) or "nobody in the roster"
            lines.append(f"  * approval {p['state']}: {p['artifact']} by {'/'.join(p['roles'])} ({who})")
        for a in c["approvals"]:
            lines.append(f"  = approved: {a['artifact']} by {a['approver']} as {a['role']}"
                         f"{'' if a['valid'] else ' (STALE: content changed)'}")
        lines += [f"  next: {c['next_command']}", ""]
    return "\n".join(lines)


def run(root: Path, cfg: dict, only_change: str | None, fmt: str) -> int:
    data = collect(root, cfg, only_change)
    print(render(data, fmt), end="")
    blocked = any(c.get("errors_now") or c.get("blocking_next") or c.get("pending_approvals") or c.get("errors")
                  for c in data["changes"])
    return 1 if blocked else 0


def summary_for_change(root: Path, cfg: dict, change_id: str) -> str:
    """Short text used by the MCP tool and by `phase` when a gate blocks."""
    return render(collect(root, cfg, change_id), "text")

