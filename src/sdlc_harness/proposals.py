"""Propose and approve time-boxed deviations and sensor exceptions.

An agent may write the proposal (what, why, until when) but never the approval: `propose` leaves `approver` empty,
which every gate reads as pending, and `approve` fills it in for a human who holds an authorized role. Without this
path the alternative was to leave accepted risk in prose, where nothing makes it expire.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import tomllib
from pathlib import Path

from . import authority
from .core import VENDORED_CLI, HarnessError, Report, load_toml

DEVIATIONS_FILE = ".harness/deviations.toml"
EXCEPTIONS_FILE = ".harness/exceptions.toml"
KINDS = {
    "deviation": (DEVIATIONS_FILE, "deviation", ("policy",), ("policy", "reason", "approver", "role", "expires")),
    "exception": (EXCEPTIONS_FILE, "exception", ("rule", "path"), ("rule", "path", "reason", "approver", "expires")),
}


def _expiry(days: int | None, expires: str | None) -> str:
    if expires:
        try:
            return dt.date.fromisoformat(expires).isoformat()
        except ValueError as exc:
            raise HarnessError(f"--expires must be YYYY-MM-DD: {exc}") from exc
    return (dt.date.today() + dt.timedelta(days=days or 90)).isoformat()


def _entries(root: Path, kind: str) -> list[dict]:
    filename, table, _, _ = KINDS[kind]
    path = root / filename
    return load_toml(path).get(table, []) if path.exists() else []


def _identity(kind: str, entry: dict) -> tuple:
    return tuple(str(entry.get(k, "*" if k == "path" else "")) for k in KINDS[kind][2])


def propose(root: Path, kind: str, fields: dict, reason: str, days: int | None, expires: str | None) -> int:
    filename, table, id_keys, order = KINDS[kind]
    if not reason.strip():
        raise HarnessError("--reason is required: a deviation without a stated reason cannot be reviewed")
    entry = {**fields, "reason": reason.strip(), "approver": "", "expires": _expiry(days, expires)}
    if kind == "deviation":
        entry["role"] = ""
    wanted = _identity(kind, entry)
    for existing in _entries(root, kind):
        if _identity(kind, existing) == wanted:
            state = "approved" if existing.get("approver") else "already pending"
            raise HarnessError(f"{filename}: an entry for {dict(zip(id_keys, wanted))} is {state}")
    lines = ["", f"[[{table}]]"]
    for key in order:
        value = entry[key]
        lines.append(f"{key} = {value}" if key == "expires" else f"{key} = {json.dumps(value)}")
    path = root / filename
    path.write_text((path.read_text(encoding="utf-8") if path.exists() else "") + "\n".join(lines) + "\n",
                    encoding="utf-8")
    print(f"proposed in {filename}, expires {entry['expires']}, pending approval.")
    print(f"A human approves with: sdlc {kind} approve {' '.join(str(v) for v in wanted)} --as <username> --role <role>")
    return 0


def approve(root: Path, cfg: dict, kind: str, identity: tuple, approver: str, role: str) -> int:
    filename, table, id_keys, _ = KINDS[kind]
    allowed = authority.approver_roles(cfg, kind)
    if role not in allowed:
        raise HarnessError(f"role '{role}' may not approve {kind}s (roster [authority] {kind} = {allowed or 'none'})")
    if authority.local_membership(cfg, role, approver) is False:
        raise HarnessError(f"'{approver}' is not a member of role '{role}' in .harness/roster.toml")
    pending = [e for e in _entries(root, kind) if _identity(kind, e) == identity and not e.get("approver")]
    if not pending:
        known = [_identity(kind, e) for e in _entries(root, kind)]
        raise HarnessError(f"{filename}: no pending {kind} for {dict(zip(id_keys, identity))} "
                           f"(entries: {known or 'none'})")
    path = root / filename
    blocks = re.split(rf"(?m)^(?=\[\[{table}\]\])", path.read_text(encoding="utf-8"))
    for i, block in enumerate(blocks):
        if not block.startswith(f"[[{table}]]"):
            continue
        parsed = tomllib.loads(block).get(table, [{}])[0]
        if _identity(kind, parsed) != identity or parsed.get("approver"):
            continue
        block = re.sub(r'(?m)^approver\s*=\s*""\s*$', f"approver = {json.dumps(approver)}", block)
        if kind == "deviation":
            block = re.sub(r'(?m)^role\s*=\s*""\s*$', f"role = {json.dumps(role)}", block)
        blocks[i] = block
        break
    path.write_text("".join(blocks), encoding="utf-8")
    print(f"{kind} approved by {approver} ({role}) in {filename}; it expires as recorded and then fails the gate.")
    return 0


def pending(root: Path, cfg: dict) -> Report:
    """Proposals waiting for a human. Visible even without an organization policy, so they are not forgotten."""
    report = Report()
    for kind, (filename, _, id_keys, _) in KINDS.items():
        allowed = authority.approver_roles(cfg, kind) or ["<no role in roster [authority]>"]
        for entry in _entries(root, kind):
            if entry.get("approver"):
                continue
            identity = " ".join(_identity(kind, entry))
            report.warn(f"{filename}: {kind} '{identity}' is proposed and awaits approval; a human runs: "
                        f"python3 {VENDORED_CLI} {kind} approve {identity} --as <username> --role {allowed[0]}")
    return report
