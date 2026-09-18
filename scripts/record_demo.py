#!/usr/bin/env python3
"""Record the harness loop as an animated SVG for the README.

It runs the real commands in a throwaway repository, captures their real output and renders a terminal-looking SVG
whose frames appear in sequence (pure CSS, no JavaScript, so GitHub renders it). Nothing is faked: if a command
changes its output, the recording changes with it.

Usage: python3 scripts/record_demo.py [--output docs/assets/demo.svg] [--check]
"""
from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sdlc_harness import __version__  # noqa: E402

WIDTH, LINE_H, PAD, FONT = 92, 19, 18, 13.2
HOLD = 3.4  # seconds each step stays on screen
MAX_LINES = 13


def run(cwd: Path, *args: str, env: dict | None = None) -> str:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})
    return (proc.stdout + proc.stderr).rstrip()


def record(workdir: Path) -> list[tuple[str, str]]:
    """(command, output) pairs from a real session."""
    sdlc = [sys.executable, "-m", "sdlc_harness"]
    env = {"PYTHONPATH": str(ROOT / "src")}
    steps: list[tuple[str, str]] = []

    def step(label: str, *args: str, cwd: Path = workdir) -> None:
        steps.append((label, run(cwd, *sdlc, *args, env=env)))

    run(workdir, "git", "init", "-q", "-b", "main")
    run(workdir, "git", "config", "user.email", "demo@example.com")
    run(workdir, "git", "config", "user.name", "demo")
    out = run(workdir, *sdlc, "init", str(workdir), "--profile", "standard", "--agents", "claude-code,codex", env=env)
    steps.append(("sdlc init . --profile standard --agents claude-code,codex",
                  "\n".join(line for line in out.splitlines() if line.startswith(("[", "updated", "wrote")))))

    roster = workdir / ".harness/roster.toml"
    roster.write_text(roster.read_text().replace('[roles.product-owner]\nmembers = []',
                                                 '[roles.product-owner]\nmembers = ["pat"]')
                      .replace('[roles.tech-lead]\nmembers = []', '[roles.tech-lead]\nmembers = ["tomas"]'))
    step("sdlc new feature booking-reminders --risk medium --scope ui",
         "new", "feature", "booking-reminders", "--risk", "medium", "--scope", "ui")
    change_id = next(p.name for p in sorted((workdir / "docs/changes").iterdir()) if (p / "change.toml").exists())
    step("sdlc status", "status")

    example = ROOT / "docs/examples/2026-09-17-staff-csv-export"
    target = workdir / "docs/changes" / change_id
    for name in ("discovery.md", "spec.md"):
        shutil.copy2(example / name, target / name)
    step("sdlc phase <id> spec   # the agent filled discovery.md", "phase", change_id, "spec")
    step("sdlc approve <id> discovery.md --as pat --role product-owner   # a human, never the agent",
         "approve", change_id, "discovery.md", "--as", "pat", "--role", "product-owner")
    step("sdlc phase <id> spec", "phase", change_id, "spec")
    (target / "discovery.md").write_text((target / "discovery.md").read_text() + "\nEdited after approval.\n")
    step("sdlc check   # an approved artifact was edited afterwards", "check", "--change", change_id)
    step('sdlc explain "approval by pat is stale (content changed); re-approve"',
         "explain", "approval by pat is stale (content changed); re-approve")
    return steps


def render(steps: list[tuple[str, str]]) -> str:
    frames = []
    for command, output in steps:
        lines = [("cmd", f"$ {command}")]
        for line in output.splitlines():
            kind = "err" if line.startswith(("ERROR", "FAIL", "  ! ", "  - ")) else \
                "warn" if line.startswith(("WARN", "  * ")) else \
                "ok" if line.startswith(("OK:", "  = ", "receipt recorded")) else "out"
            lines.append((kind, line))
        frames.append(lines[:MAX_LINES])

    height = PAD * 2 + 28 + LINE_H * MAX_LINES
    total = HOLD * len(frames)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(WIDTH * FONT * 0.602) + PAD * 2} {int(height)}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{FONT}">',
        "<style>",
        ".bg{fill:#0d1117}.chrome{fill:#161b22}.title{fill:#8b949e}",
        ".cmd{fill:#79c0ff}.out{fill:#c9d1d9}.ok{fill:#7ee787}.warn{fill:#d29922}.err{fill:#ff7b72}",
        "g.frame{opacity:0}",
    ]
    for i in range(len(frames)):
        begin = i * HOLD
        parts.append(f"g.f{i}{{animation:f{i} {total}s linear infinite}}"
                     f"@keyframes f{i}{{0%,{begin / total * 100:.3f}%{{opacity:0}}"
                     f"{(begin + 0.12) / total * 100:.3f}%,{(begin + HOLD - 0.12) / total * 100:.3f}%{{opacity:1}}"
                     f"{(begin + HOLD) / total * 100:.3f}%,100%{{opacity:0}}}}")
    parts += ["</style>",
              '<rect class="bg" width="100%" height="100%" rx="10"/>',
              '<rect class="chrome" width="100%" height="30" rx="10"/>',
              '<circle cx="20" cy="15" r="5" fill="#ff5f56"/><circle cx="38" cy="15" r="5" fill="#ffbd2e"/>'
              '<circle cx="56" cy="15" r="5" fill="#27c93f"/>',
              f'<text class="title" x="76" y="19">sdlc-harness {__version__} - one change, gated</text>']
    for i, lines in enumerate(frames):
        parts.append(f'<g class="frame f{i}">')
        for j, (kind, text) in enumerate(lines):
            y = PAD + 30 + LINE_H * (j + 1)
            parts.append(f'<text class="{kind}" x="{PAD}" y="{y:.0f}" xml:space="preserve">'
                         f'{html.escape(text[:WIDTH])}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "docs/assets/demo.svg"))
    parser.add_argument("--check", action="store_true", help="fail if the recording would change materially")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        svg = render(record(Path(tmp)))
    out = Path(args.output)
    if args.check:
        if not out.exists():
            print(f"{out} does not exist; run scripts/record_demo.py")
            return 1
        before, after = out.read_text(encoding="utf-8").count("<text"), svg.count("<text")
        if before != after:
            print(f"recording changed ({before} -> {after} lines); run scripts/record_demo.py")
            return 1
        print("demo recording up to date")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({svg.count('<g class=')} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
