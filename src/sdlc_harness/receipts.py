"""Approval receipts: a human approval bound to the SHA-256 of the exact artifact content.

Receipts live in `docs/changes/<id>/approvals.toml`. Locally they prove content has not changed since
approval and that the approver holds an authorized role. In CI, `sdlc approvals verify` confirms against
the VCS platform that the named person really approved that content (see platform.py).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import audit, authority
from .core import PLACEHOLDER, HarnessError, Report, load_toml, sha256_file

APPROVALS_FILE = "approvals.toml"


def load(change_dir: Path) -> list[dict]:
    path = change_dir / APPROVALS_FILE
    return load_toml(path).get("approval", []) if path.exists() else []


def _dump(change_dir: Path, entries: list[dict]) -> None:
    out = ["# Approval receipts. Written by `sdlc approve`; verified by `sdlc check` and `sdlc approvals verify`.", ""]
    for e in entries:
        out.append("[[approval]]")
        for key in ("artifact", "sha256", "role", "approver", "approved_at"):
            out.append(f"{key} = {json.dumps(e[key])}")
        out.append("")
    (change_dir / APPROVALS_FILE).write_text("\n".join(out), encoding="utf-8")


def approve(root: Path, cfg: dict, change_dir: Path, artifact: str, approver: str, role: str) -> int:
    """Record a receipt. `artifact` is repo-relative (e.g. docs/changes/<id>/spec.md or docs/adr/0003-x.md)."""
    path = root / artifact
    if not path.is_file():
        raise HarnessError(f"artifact not found: {artifact}")
    if PLACEHOLDER in path.read_text(encoding="utf-8"):
        raise HarnessError(f"{artifact} has unfilled sections; it cannot be approved")
    key = authority.artifact_key(cfg, artifact)
    allowed = authority.approver_roles(cfg, key)
    if role not in allowed:
        raise HarnessError(f"role '{role}' is not authorized to approve '{key}' (allowed: {allowed or 'none'})")
    membership = authority.local_membership(cfg, role, approver)
    if membership is False:
        raise HarnessError(f"'{approver}' is not a member of role '{role}' in .harness/roster.toml")
    if membership is None:
        print(f"WARN membership of '{approver}' in '{role}' depends on a platform team; verified in CI")

    digest = sha256_file(path)
    entries = [e for e in load(change_dir) if not (e["artifact"] == artifact and e["approver"] == approver)]
    entries.append({
        "artifact": artifact,
        "sha256": digest,
        "role": role,
        "approver": approver,
        "approved_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    })
    _dump(change_dir, entries)
    audit.append(root, change_dir, "approved", artifact=artifact, sha256=digest, role=role, approver=approver)
    print(f"receipt recorded: {artifact} sha256={digest[:12]} approver={approver} role={role}")
    print("Commit approvals.toml and audit.jsonl, then approve the pull request on the platform.")
    return 0


def check(root: Path, cfg: dict, change_dir: Path, artifact: str) -> Report:
    """At least one receipt with current content hash, authorized role and roster membership."""
    report = Report()
    path = root / artifact
    if not path.is_file():
        return report  # presence is reported by the artifact rule
    digest = sha256_file(path)
    key = authority.artifact_key(cfg, artifact)
    allowed = authority.approver_roles(cfg, key)
    receipts = [e for e in load(change_dir) if e.get("artifact") == artifact]
    if not allowed:
        report.error(f"{artifact}: approval required but no role may approve '{key}' (roster [authority])")
        return report
    valid, stale = [], []
    for e in receipts:
        if e.get("role") not in allowed or authority.local_membership(cfg, e["role"], e.get("approver", "")) is False:
            report.error(f"{artifact}: receipt by '{e.get('approver')}' as '{e.get('role')}' is not authorized")
        elif e.get("sha256") != digest:
            stale.append(e["approver"])
        else:
            valid.append(e)
    if not valid:
        if stale:
            report.error(f"{artifact}: approval by {', '.join(stale)} is stale (content changed); re-approve")
        else:
            report.error(f"{artifact}: requires approval by one of roles {allowed} (`sdlc approve`)")
    return report
