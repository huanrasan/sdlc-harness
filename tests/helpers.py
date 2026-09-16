import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sdlc_harness import cli  # noqa: E402

VALID = {
    "spec.md": """# Spec: retries

## Problem and outcome
Payments fail on transient errors.

## Acceptance criteria
| ID | Given / When / Then | Verified by |
|---|---|---|
| AC-1 | Given a transient error, when paying, then the payment is retried 3 times | test |

## Non-functional requirements
| Concern | Requirement (with numbers) |
|---|---|
| Performance | p95 < 300 ms |

## Out of scope
Refunds.
""",
    "design.md": """# Design
## Solution overview
Retry wrapper.
## Failure modes and resilience
Backoff with jitter.
## Rollout and rollback
Feature flag.
""",
    "threat-model.md": """# Threat model
## What can go wrong?
| ID | Element / boundary | STRIDE / OWASP category | Threat | Likelihood | Impact |
|---|---|---|---|---|---|
| T-1 | retry queue | Tampering | duplicate charge | low | high |

## What are we going to do about it?
| Threat | Control | Verifiable by | Owner |
|---|---|---|---|
| T-1 | idempotency key | test_idempotency | team |
""",
    "plan.md": """# Plan
## Traceability
| Requirement / threat | Test(s) | Type |
|---|---|---|
| AC-1 | test_retry | unit |
| T-1 | test_idempotency | unit |

## Tasks
| # | Task | Done when (command or check) | Depends on | Status |
|---|---|---|---|---|
| 1 | add retry | pytest -k retry | | done |
""",
    "verification.md": """# Verification
## Acceptance criteria
| ID | Result | Evidence (test name / manual check) |
|---|---|---|
| AC-1 | pass | `test_retry` |
""",
    "review.md": """# Review
- Reviewer: agent-b
- Fresh context (did not see implementation session): yes
- Verdict: ready-for-human-approval

## Checklist
- [x] Acceptance criteria implemented and tested
""",
    "release.md": """# Release
| Field | Value |
|---|---|
| Version | 1.2.0 |
| Artifacts and digests | sha256:abc |

## Rollout plan
Canary 10%.

## Rollback
Flag off.
""",
    "runbook.md": """# Runbook
## Dashboards and alerts
| Alert | Meaning | First action |
|---|---|---|
| RetryStorm | too many retries | disable flag |

## Safe mitigations
Disable flag.
""",
}

ADR = """# 0001. Use a retry library

**Status:** Proposed

## Options considered
1. Library
2. Custom

## Decision
Library.

## Consequences
Less code.
"""


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue()


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class HarnessCase(unittest.TestCase):
    profile = "standard"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        sh(self.repo, "git", "init", "-q", "-b", "main")
        sh(self.repo, "git", "config", "user.email", "dev@example.com")
        sh(self.repo, "git", "config", "user.name", "dev")
        code, out = run("init", str(self.repo), "--profile", self.profile)
        self.assertEqual(code, 0, out)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cli(self, *argv: str) -> tuple[int, str]:
        return run("--root", str(self.repo), *argv)

    def new_change(self, change_type="feature", risk="medium", slug="retries") -> str:
        code, out = self.cli("new", change_type, slug, "--risk", risk)
        self.assertEqual(code, 0, out)
        return self.change_dir().name

    def change_dir(self) -> Path:
        return next(p for p in (self.repo / "docs/changes").iterdir() if p.is_dir())

    def write_valid(self, *names: str) -> None:
        for name in names:
            (self.change_dir() / name).write_text(VALID[name])

    def set_roster(self, **roles: list[str]) -> None:
        path = self.repo / ".harness/roster.toml"
        text = path.read_text()
        for role, members in roles.items():
            quoted = ", ".join(f'"{m}"' for m in members)
            text = text.replace(f"[roles.{role.replace('_', '-')}]\nmembers = []",
                                f"[roles.{role.replace('_', '-')}]\nmembers = [{quoted}]")
        path.write_text(text)

    def advance(self, cid: str, *phases: str) -> None:
        for ph in phases:
            code, out = self.cli("phase", cid, ph)
            self.assertEqual(code, 0, f"{ph}: {out}")
