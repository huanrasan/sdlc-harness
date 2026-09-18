#!/usr/bin/env python3
"""Cross-agent evals: does an agent follow the harness when it matters?

Each scenario installs the harness into a fresh git repository, adds fixture files, runs a headless agent with a
prompt, and grades the resulting repository state with deterministic checks (plus optional soft checks on the
transcript). Results are written as JSON and a Markdown summary with pass rates per scenario and agent.

Usage:
  python3 evals/run.py --agent claude-code [--agent codex ...] [--scenario NAME ...] [--trials 3] [--keep]
  python3 evals/run.py --list
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent
sys.path.insert(0, str(ROOT / "src"))

from sdlc_harness import cli  # noqa: E402
from sdlc_harness.core import PHASES  # noqa: E402

SIMULATED = {"simulated-good", "simulated-bad"}


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def quiet(fn, *args):
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return fn(*args)
        except SystemExit as exc:
            return exc.code


def setup_repo(scenario: dict, name: str, workdir: Path) -> None:
    sh(workdir, "git", "init", "-q", "-b", "main")
    sh(workdir, "git", "config", "user.email", "eval@example.com")
    sh(workdir, "git", "config", "user.name", "eval")
    code = quiet(cli.main, ["init", str(workdir), "--profile", scenario.get("profile", "standard"),
                            "--agents", "claude-code,codex,copilot,cursor,gemini-cli,opencode,windsurf"])
    if code:
        raise RuntimeError(f"harness init failed for {name}")
    roster = workdir / ".harness/roster.toml"
    roster.write_text(roster.read_text().replace('[roles.product-owner]\nmembers = []',
                                                 '[roles.product-owner]\nmembers = ["alice"]'))
    for f in scenario.get("files", []):
        target = workdir / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"])
    if change := scenario.get("change"):
        d = workdir / "docs/changes" / change["id"]
        d.mkdir(parents=True)
        (d / "change.toml").write_text(
            f'id = "{change["id"]}"\ntype = "{change["type"]}"\nrisk = "{change["risk"]}"\n'
            f'phase = "{change["phase"]}"\nscopes = []\nai_assisted = true\nadrs = []\n')
        for artifact in change.get("files", []):
            shutil.copy2(EVALS / "scenarios" / name / artifact, d / artifact)
    quiet(cli.main, ["--root", str(workdir), "sync"])
    sh(workdir, "git", "add", "-A")
    sh(workdir, "git", "commit", "-qm", "chore: eval setup", "--no-verify")


def _matching(workdir: Path, glob: str) -> list[Path]:
    return [p for p in workdir.glob(glob) if p.is_file() and ".git" not in p.parts]


def _changes(workdir: Path) -> list[dict]:
    return [tomllib.loads(p.read_text()) for p in sorted((workdir / "docs/changes").glob("*/change.toml"))]


def _diff_lines(workdir: Path, glob: str, sign: str) -> list[str]:
    sh(workdir, "git", "add", "-A")
    diff = sh(workdir, "git", "diff", "--cached", "--unified=0", "HEAD")
    lines, current = [], None
    for line in diff.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            path = line[6:] if line[4:6] in ("a/", "b/") else None
            if path:
                current = path
            continue
        if current and fnmatch.fnmatch(current, glob) and line.startswith(sign) and not line.startswith(sign * 3):
            lines.append(line[1:])
    return lines


def grade(expect: dict, workdir: Path, transcript: str) -> tuple[bool, str]:
    kind = expect["kind"]
    changes = _changes(workdir)
    if kind == "change_records":
        n = len(changes)
        ok = expect.get("min", 0) <= n <= expect.get("max", 10**6)
        return ok, f"{n} change record(s)"
    if kind == "change_field":
        values = [c.get(expect["field"]) for c in changes]
        ok = bool(values) and all(v in expect["values"] for v in values)
        return ok, f"{expect['field']}={values}"
    if kind == "phase_at_most":
        phases = [c.get("phase") for c in changes]
        ok = all(p in PHASES and PHASES.index(p) <= PHASES.index(expect["phase"]) for p in phases)
        return ok, f"phases={phases}"
    if kind == "any_artifact_matches":
        pattern = re.compile(expect["pattern"])
        hits = [p for p in _matching(workdir, "docs/changes/*/*.md") if pattern.search(p.read_text())]
        return bool(hits), f"{len(hits)} artifact(s) match"
    if kind == "no_path":
        found = _matching(workdir, expect["glob"])
        return not found, f"found {[str(p.relative_to(workdir)) for p in found]}"
    if kind == "path_exists":
        return bool(_matching(workdir, expect["glob"])), expect["glob"]
    if kind == "unchanged":
        sh(workdir, "git", "add", "-A")
        changed = [n for n in sh(workdir, "git", "diff", "--cached", "--name-only", "HEAD").splitlines()
                   if fnmatch.fnmatch(n, expect["glob"])]
        return not changed, f"changed {changed}"
    if kind in ("no_added_pattern", "no_removed_pattern"):
        pattern = re.compile(expect["pattern"])
        lines = [x for x in _diff_lines(workdir, expect["glob"], "+" if kind == "no_added_pattern" else "-")
                 if pattern.search(x)]
        return not lines, f"{lines[:3]}"
    if kind == "file_matches":
        pattern = re.compile(expect["pattern"])
        files = _matching(workdir, expect["glob"])
        return any(pattern.search(p.read_text()) for p in files), expect["glob"]
    if kind == "transcript_matches":
        return bool(re.search(expect["pattern"], transcript)), "transcript"
    raise ValueError(f"unknown grader kind: {kind}")


def run_trial(agent: str, spec: dict, name: str, scenario: dict, keep: bool) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix=f"sdlc-eval-{name}-"))
    try:
        setup_repo(scenario, name, workdir)
        command = [part.replace("{prompt}", scenario["prompt"]).replace("{evals}", str(EVALS))
                   .replace("{scenario}", name) for part in spec["command"]]
        started = time.monotonic()
        try:
            proc = subprocess.run(command, cwd=workdir, capture_output=True, text=True, timeout=spec.get("timeout", 900),
                                  stdin=subprocess.DEVNULL)
            transcript, exit_code = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            transcript, exit_code = (exc.stdout or b"").decode(errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), "timeout"
        duration = round(time.monotonic() - started, 1)
        results = []
        for expect in scenario.get("expect", []):
            ok, detail = grade(expect, workdir, transcript)
            results.append({"kind": expect["kind"], "soft": expect.get("soft", False), "passed": ok, "detail": detail,
                            "why": expect.get("why", "")})
        hard = [r for r in results if not r["soft"]]
        passed = all(r["passed"] for r in hard) and exit_code == 0
        # An agent that exited non-zero without touching the repository never ran: an expired session, a missing
        # credential or a usage limit is not a governance failure, and counting it as one corrupts the measurement.
        untouched = not sh(workdir, "git", "status", "--porcelain").strip()
        status = "error" if exit_code != 0 and untouched else ("pass" if passed else "fail")
        return {"agent": agent, "scenario": name, "passed": passed, "status": status,
                "exit_code": exit_code, "duration_s": duration, "checks": results,
                "transcript_tail": transcript[-2000:], "workdir": str(workdir) if keep else None}
    finally:
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)


def summarize(results: list[dict]) -> str:
    lines = ["# Eval results", "", f"Generated {dt.datetime.now().isoformat(timespec='seconds')}", "",
             "| Agent | Scenario | Passed | Rate | Failed checks |", "|---|---|---|---|---|"]
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in results:
        groups.setdefault((r["agent"], r["scenario"]), []).append(r)
    for (agent, scenario), rs in sorted(groups.items()):
        graded = [r for r in rs if r.get("status") != "error"]
        errored = len(rs) - len(graded)
        passed = sum(1 for r in graded if r["passed"])
        failed = sorted({f"{c['kind']}: {c['detail']}" for r in graded for c in r["checks"]
                         if not c["passed"] and not c["soft"]}
                        | {f"exit {r['exit_code']}" for r in graded if r["exit_code"] != 0})
        if errored:
            failed.append(f"{errored} trial(s) not measured: the agent did not run")
        rate = f"{passed / len(graded):.0%}" if graded else "n/a"
        lines.append(f"| {agent} | {scenario} | {passed}/{len(graded)} | {rate} | "
                     f"{'; '.join(failed)[:300].replace('|', '/') or '-'} |")
    by_agent: dict[str, list[dict]] = {}
    for r in results:
        by_agent.setdefault(r["agent"], []).append(r)
    lines += ["", "| Agent | Overall pass rate | Not measured |", "|---|---|---|"]
    for a, rs in sorted(by_agent.items()):
        graded = [r for r in rs if r.get("status") != "error"]
        passed = sum(r["passed"] for r in graded)
        rate = f"{passed / len(graded):.0%} ({passed}/{len(graded)})" if graded else "n/a (0 trials measured)"
        lines.append(f"| {a} | {rate} | {len(rs) - len(graded)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", action="append", default=[])
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--keep", action="store_true", help="keep working directories for inspection")
    parser.add_argument("--output", default=str(EVALS / "results"))
    parser.add_argument("--agents-file", default=str(EVALS / "agents.toml"),
                        help="adapter definitions (default: evals/agents.toml)")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    agents = tomllib.loads(Path(args.agents_file).read_text())["agents"]
    scenarios = {p.name: tomllib.loads((p / "scenario.toml").read_text())
                 for p in sorted((EVALS / "scenarios").iterdir()) if (p / "scenario.toml").exists()}
    if args.list:
        for name, s in scenarios.items():
            print(f"{name}: {s['description']}")
        print("agents:", ", ".join(f"{a}{'' if a in SIMULATED or shutil.which(spec['command'][0]) else ' (not installed)'}"
                                   for a, spec in agents.items()))
        return 0
    selected = args.scenario or list(scenarios)
    results = []
    for agent in args.agent:
        spec = agents.get(agent)
        if spec is None:
            parser.error(f"unknown agent {agent}")
        if agent not in SIMULATED and not shutil.which(spec["command"][0]):
            print(f"skip {agent}: {spec['command'][0]} not on PATH")
            continue
        for name in selected:
            for trial in range(args.trials):
                r = run_trial(agent, spec, name, scenarios[name], args.keep)
                results.append(r)
                label = {"pass": "PASS", "fail": "FAIL", "error": "ERROR"}[r["status"]]
                note = ""
                if r["status"] == "error":
                    note = f" - agent did not run: {r['transcript_tail'].strip().splitlines()[-1][:80]}" \
                        if r["transcript_tail"].strip() else " - agent did not run"
                print(f"{label} {agent} {name} #{trial + 1} ({r['duration_s']}s){note}")
    if not results:
        return 1
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"{stamp}.json").write_text(json.dumps(results, indent=2))
    summary = summarize(results)
    (out / f"{stamp}.md").write_text(summary)
    print("\n" + summary)
    graded = [r for r in results if r.get("status") != "error"]
    if len(graded) < len(results):
        print(f"\n{len(results) - len(graded)} of {len(results)} trial(s) could not be measured: the agent exited "
              f"without touching the repository. Those are excluded from the rates above; re-run them.")
    if not graded:
        return 2
    return 0 if all(r["passed"] for r in graded) else 1


if __name__ == "__main__":
    sys.exit(main())
