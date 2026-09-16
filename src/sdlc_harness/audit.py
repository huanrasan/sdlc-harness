"""Per-change, hash-chained, append-only audit log (tamper-evident, not tamper-proof).

Each event embeds the hash of the previous one. Rewriting history requires recomputing every later hash,
and CI rejects any change to lines that already exist on the base branch (`verify --base`).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from .core import Report, git

AUDIT_FILE = "audit.jsonl"
GENESIS = "0" * 64


def _hash(event: dict) -> str:
    body = {k: v for k, v in event.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def actor(root: Path) -> str:
    for var in ("SDLC_ACTOR", "GITHUB_ACTOR", "GITLAB_USER_LOGIN"):
        if os.environ.get(var):
            return os.environ[var]
    return git(root, "config", "user.email", check=False) or "unknown"


def append(root: Path, change_dir: Path, event: str, **details) -> dict:
    log = change_dir / AUDIT_FILE
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    prev = json.loads(lines[-1])["hash"] if lines else GENESIS
    entry = {
        "seq": len(lines) + 1,
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "actor": actor(root),
        "event": event,
        **details,
        "prev": prev,
    }
    entry["hash"] = _hash(entry)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify_chain(root: Path, log: Path) -> Report:
    report = Report()
    rel = log.relative_to(root)
    prev = GENESIS
    for n, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            report.error(f"{rel}:{n}: not valid JSON")
            return report
        if entry.get("seq") != n or entry.get("prev") != prev or entry.get("hash") != _hash(entry):
            report.error(f"{rel}:{n}: hash chain broken (edited, reordered or removed events)")
            return report
        prev = entry["hash"]
    return report


def verify_append_only(root: Path, log: Path, base: str) -> Report:
    report = Report()
    rel = log.relative_to(root).as_posix()
    before = git(root, "show", f"{base}:{rel}", check=False)
    if before and not log.read_text(encoding="utf-8").startswith(before.rstrip("\n")):
        report.error(f"{rel}: existing audit events were modified relative to {base} (append-only)")
    return report
