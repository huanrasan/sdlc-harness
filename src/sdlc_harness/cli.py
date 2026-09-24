"""Command-line interface."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from . import (adapters, architecture, audit, authority, changes, contracts, evidence, explain, installer, mcp,
               memory, platform, policy, proposals, receipts, reports, skills, status, tdd)
from .core import (PHASES, PROFILES, RISKS, SCOPES, TYPES, VERSION, HarnessError, Report, git,
                   load_config, paths)

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: .+"
)
ADR_FILE_RE = re.compile(r"^\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.md$")
ADR_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(Proposed|Accepted|Rejected|Deprecated|Superseded by \d{4})\s*$", re.M)


def sensor_level(cfg: dict, name: str, default: str = "error") -> str:
    return cfg["_profile"].get("sensors", {}).get(name, default)


def apply_level(report: Report, level: str) -> Report:
    if level == "off":
        return Report()
    if level == "warn":
        return Report(errors=[], warnings=report.warnings + report.errors)
    return report


def run_sensors(root: Path, cfg: dict, base: str | None) -> Report:
    report = Report()
    report.extend(apply_level(architecture.check(root), sensor_level(cfg, "architecture")))
    if base:
        report.extend(apply_level(tdd.check_test_first(root, cfg, base), sensor_level(cfg, "test_first", "warn")))
        report.extend(apply_level(tdd.check_weakened_tests(root, cfg, base), sensor_level(cfg, "weakened_tests")))
        report.extend(apply_level(contracts.check(root, cfg, base), sensor_level(cfg, "contracts")))
    return report


def staged_changes(root: Path, cfg: dict) -> list[str]:
    """Change ids touched by the staged files, for a pre-commit hook that stays fast in a long-lived repository."""
    prefix = paths(cfg)["changes"].rstrip("/") + "/"
    names = git(root, "diff", "--cached", "--name-only", check=False).splitlines()
    ids = {n[len(prefix):].split("/")[0] for n in names if n.startswith(prefix)}
    return sorted(i for i in ids if (root / prefix / i / "change.toml").is_file())


def run_check(root: Path, only_change: str | None = None, base: str | None = None,
              only_changes: list[str] | None = None) -> Report:
    cfg = load_config(root)
    p = paths(cfg)
    report = Report()
    if only_change is None:
        skills_report, found = skills.check_skills(root, p["skills"])
        report.extend(skills_report)
        report.extend(skills.check_agents_md(root, cfg, found))
        report.extend(check_adr_files(root, p["adr"]))
        report.extend(adapters.check(root, cfg))
        report.extend(authority.check_roster(cfg, strict=False))
        report.extend(run_sensors(root, cfg, base))
        report.extend(policy.check(root, cfg))
        report.extend(proposals.pending(root, cfg))
        report.extend(memory.check(root))
    base_dir = root / p["changes"]
    if only_changes is not None:
        for cid in only_changes:
            report.extend(changes.check_change(root, changes.change_dir(root, cfg, cid), cfg))
    elif only_change:
        report.extend(changes.check_change(root, changes.change_dir(root, cfg, only_change), cfg))
    elif base_dir.is_dir():
        for d in sorted(x for x in base_dir.iterdir() if x.is_dir()):
            report.extend(changes.check_change(root, d, cfg))
            if base and (d / audit.AUDIT_FILE).exists():
                report.extend(audit.verify_append_only(root, d / audit.AUDIT_FILE, base))
    return report


def check_adr_files(root: Path, adr_dir: str) -> Report:
    report = Report()
    base = root / adr_dir
    if not base.is_dir():
        return report
    for f in sorted(base.glob("*.md")):
        if f.name.lower() in ("readme.md", "template.md"):
            continue
        rel = f.relative_to(root)
        if not ADR_FILE_RE.match(f.name):
            report.error(f"{rel}: ADR filename must be NNNN-kebab-title.md")
        if not ADR_STATUS_RE.search(f.read_text(encoding="utf-8")):
            report.error(f"{rel}: missing or invalid '**Status:**' line")
    return report


def cmd_commit_msg(root: Path, file: str) -> int:
    cfg = load_config(root)
    msg = Path(file).read_text(encoding="utf-8")
    lines = [line for line in msg.splitlines() if not line.startswith("#")]
    report = Report()
    subject = lines[0] if lines else ""
    if not subject.startswith(("Merge ", "Revert ")) and not CONVENTIONAL_RE.match(subject):
        report.error("subject must follow Conventional Commits: type(scope): summary")
    for trailer in cfg["_profile"].get("commits", {}).get("require_trailers", []):
        if not re.search(rf"^{re.escape(trailer)}: .+$", msg, re.M):
            report.error(f"missing required trailer '{trailer}: <value>' (use 'none' if not applicable)")
    return report.print() if report.errors else 0


def cmd_codeowners(root: Path, check_only: bool) -> int:
    cfg = load_config(root)
    content, report = authority.render_codeowners(cfg)
    target = authority.codeowners_path(root, cfg)
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if check_only:
        if current != content:
            report.error(f"{target.relative_to(root)} is out of date; run `sdlc codeowners`")
        return report.print()
    if current and not current.startswith(authority.CODEOWNERS_HEADER):
        report.error(f"{target.relative_to(root)} was not generated by sdlc; move custom rules to roster [codeowners]")
        return report.print()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"wrote {target.relative_to(root)}")
    return report.print()


def cmd_doctor(root: Path) -> int:
    cfg = load_config(root)
    regulated = cfg.get("harness", {}).get("profile") == "regulated"
    report = Report()
    strict = report.error if regulated else report.warn
    if sys.version_info < (3, 11):
        report.error("Python >= 3.11 required")
    if git(root, "config", "--get", "core.hooksPath", check=False) != ".harness/hooks":
        report.warn("git hooks not installed; run `sdlc hooks` (CI remains the authoritative gate)")
    if not ((root / ".github/workflows/sdlc-gates.yml").exists() or (root / ".gitlab-ci.sdlc.yml").exists()):
        strict("no CI gate found; local hooks can be bypassed")
    codeowners = authority.codeowners_path(root, cfg)
    if not codeowners.exists():
        strict(f"no {codeowners.relative_to(root)}: run `sdlc codeowners` so the platform enforces approvals")
    elif authority.render_codeowners(cfg)[0] != codeowners.read_text(encoding="utf-8"):
        report.warn(f"{codeowners.relative_to(root)} differs from roster; run `sdlc codeowners`")
    report.extend(authority.check_roster(cfg, strict=regulated))
    if (installed := cfg.get("harness", {}).get("version")) and installed != VERSION:
        report.warn(f"harness.toml version {installed} != CLI {VERSION}")
    report.extend(run_check(root))
    return report.print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sdlc", description="Agent-agnostic SDLC harness")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="install the harness into a repository")
    p.add_argument("target")
    p.add_argument("--profile", choices=PROFILES, default="standard")
    p.add_argument("--agents", default="claude-code,codex,copilot,cursor,gemini-cli")
    p.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    p.add_argument("--ci", choices=["github", "gitlab", "none"], help="default: gitlab if .gitlab-ci.yml exists, else github")
    p.add_argument("--interactive", "-i", action="store_true", help="ask for profile, agents, CI and roster")
    p.add_argument("--adopt", action="store_true",
                   help="existing repository: detect stack and commands, keep existing AGENTS.md, write an adoption report")

    sub.add_parser("sync", help="regenerate AGENTS.md skills index and agent adapters")

    p = sub.add_parser("upgrade", help="upgrade harness files with a 3-way merge that keeps customizations")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("bundle", help="build a single-file sdlc.pyz (stdlib only)")
    p.add_argument("--output", required=True)
    p.add_argument("--full", action="store_true", help="include templates so the file can run `init` and `upgrade`")

    p = sub.add_parser("check", help="validate skills, ADRs, adapters, roster and change gates")
    p.add_argument("--change", help="only validate this change id")
    p.add_argument("--base", help="git ref; also enforce append-only audit logs against it (CI)")
    p.add_argument("--staged", action="store_true",
                   help="only validate change records touched by the staged files (pre-commit hook)")

    p = sub.add_parser("new", help="start a change record")
    p.add_argument("type", choices=TYPES)
    p.add_argument("slug")
    p.add_argument("--risk", choices=RISKS, default="medium")
    p.add_argument("--no-ai", dest="ai_assisted", action="store_false")
    p.add_argument("--scope", default="", help=f"comma-separated scopes: {','.join(SCOPES)}")

    p = sub.add_parser("phase", help="move a change to the next phase if its gate passes")
    p.add_argument("change")
    p.add_argument("phase", choices=PHASES)

    p = sub.add_parser("approve", help="record a human approval receipt for an artifact")
    p.add_argument("change")
    p.add_argument("artifact", help="file in the change record (spec.md) or repo-relative path (docs/adr/0001-x.md)")
    p.add_argument("--as", dest="approver", required=True, help="your platform username")
    p.add_argument("--role", required=True)

    p = sub.add_parser("amend", help="show what changed since an approval and re-approve in one step (human only)")
    p.add_argument("change")
    p.add_argument("artifact")
    p.add_argument("--as", dest="approver", required=True, help="your platform username")
    p.add_argument("--role", required=True)

    p = sub.add_parser("approvals", help="verify approval receipts against GitHub/GitLab (CI)")
    p.add_argument("action", choices=["verify"])
    p.add_argument("--platform", choices=["github", "gitlab"])
    p.add_argument("--base", required=True, help="base ref of the pull/merge request")
    p.add_argument("--pr", type=int, help="pull/merge request number (default: from CI environment)")

    for kind, ident in (("deviation", "policy"), ("exception", "rule")):
        p = sub.add_parser(kind, help=f"propose or approve a time-boxed {kind}")
        p.add_argument("action", choices=["propose", "approve"])
        p.add_argument(ident, help=f"{'policy key reported by `sdlc check`' if kind == 'deviation' else 'SARIF ruleId or license:<SPDX id>'}")
        if kind == "exception":
            p.add_argument("path", nargs="?", default="*", help="file glob or package purl (default: *)")
        p.add_argument("--reason", help="propose: why the rule cannot be met now")
        p.add_argument("--days", type=int, help="propose: lifetime in days (default 90)")
        p.add_argument("--expires", help="propose: explicit expiry date (YYYY-MM-DD)")
        p.add_argument("--as", dest="approver", help="approve: the approving human's username")
        p.add_argument("--role", help="approve: their role")

    p = sub.add_parser("config", help="print a configuration value (dotted key) for scripts and CI")
    p.add_argument("key", help="e.g. release.sbom_source")
    p.add_argument("--default", default="", help="printed when the key is not set")

    p = sub.add_parser("audit", help="verify audit log hash chains")
    p.add_argument("action", choices=["verify"])
    p.add_argument("--base", help="also enforce append-only against this git ref")

    p = sub.add_parser("tdd", help="test-first ordering and weakened tests over base..HEAD")
    p.add_argument("--base")
    p.add_argument("--explain", action="store_true", help="show how each tracked file is classified and exit")
    p.add_argument("paths", nargs="*", help="with --explain: only these files, with the rule that decided each")

    sub.add_parser("arch", help="check layer dependencies from .harness/architecture.toml")

    p = sub.add_parser("contracts", help="detect breaking changes in API contracts against a base ref")
    p.add_argument("--base", required=True)

    p = sub.add_parser("evidence", help="enforce policy on SARIF findings and CycloneDX SBOMs")
    p.add_argument("action", choices=["check", "baseline"],
                   help="baseline: record current findings as exceptions awaiting a human approver")
    p.add_argument("--days", type=int, default=90, help="baseline exception lifetime")
    p.add_argument("--dir", help="evidence directory (default: [evidence] dir or sdlc-evidence)")
    p.add_argument("--require", help="comma-separated evidence kinds, overriding the profile (e.g. sbom)")

    p = sub.add_parser("status", help="where each change stands, what is missing and the next command")
    p.add_argument("--change", help="only this change id")
    p.add_argument("--format", choices=["text", "json"], default="text")

    p = sub.add_parser("explain", help="explain a phase, artifact, role, concept or gate message")
    p.add_argument("topic", nargs="?", help="phase, artifact, role, scope, concept, or a pasted gate message")

    p = sub.add_parser("org", help="vendor the organization policy, skills and memory")
    p.add_argument("action", choices=["pull"])
    p.add_argument("--source", help="local directory or git URL (default: [organization] source)")
    p.add_argument("--ref", help="git branch or tag (default: [organization] ref)")

    p = sub.add_parser("memory", help="curated project/organization memory")
    msub = p.add_subparsers(dest="memory_action", required=True)
    m = msub.add_parser("add")
    m.add_argument("--type", required=True, choices=memory.TYPES)
    m.add_argument("--title", required=True)
    m.add_argument("--tags", default="")
    m.add_argument("--body", required=True)
    m.add_argument("--source", default="")
    m.add_argument("--review-days", type=int, default=180)
    m = msub.add_parser("search")
    m.add_argument("query")
    m.add_argument("--type", choices=memory.TYPES)
    m.add_argument("--tags", default="")
    m.add_argument("--limit", type=int, default=5)
    m.add_argument("--all", action="store_true", help="include superseded entries")
    msub.add_parser("index")

    p = sub.add_parser("report", help="traceability, delivery flow and DORA metrics")
    p.add_argument("kind", choices=["trace", "flow", "dora"])
    p.add_argument("--change", help="change id (trace)")
    p.add_argument("--since", help="YYYY-MM-DD or Nd (flow, dora)")
    p.add_argument("--tags", default="v*", help="release tag glob (dora)")
    p.add_argument("--window-days", type=int, default=7, help="hotfix window for failed releases (dora)")
    p.add_argument("--format", choices=["md", "json", "html"], default="md")
    p.add_argument("--output", help="write to file instead of stdout")

    p = sub.add_parser("mcp", help="serve harness tools over MCP (stdio)")
    p.add_argument("--print-config", choices=sorted(mcp.CLIENT_CONFIG), help="print client configuration and exit")

    p = sub.add_parser("codeowners", help="generate CODEOWNERS from .harness/roster.toml")
    p.add_argument("--check", action="store_true", help="fail if CODEOWNERS is out of date")

    p = sub.add_parser("commit-msg", help="validate a commit message file")
    p.add_argument("file")

    sub.add_parser("hooks", help="enable the harness git hooks")
    sub.add_parser("doctor", help="check controls and configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    match args.command:
        case "init":
            target = Path(args.target).resolve()
            agents = [a.strip() for a in args.agents.split(",") if a.strip()]
            profile, mode, ci, adopt, answers = args.profile, args.mode, args.ci, args.adopt, None
            if args.interactive:
                catalog = sorted(installer.adapter_catalog())
                answers = installer.interactive_options(target, catalog, authority.TEMPLATE_ROLES)
                profile, agents, ci, mode, adopt = (answers["profile"], answers["agents"], answers["ci"],
                                                    answers["mode"], answers["adopt"])
            code = installer.init(target, profile, agents, mode, ci, adopt)
            if code == 0 and answers:
                installer.apply_roster(target, answers["members"], answers["separation_of_duties"])
                print("roster updated; review .harness/roster.toml then run `codeowners`")
            return code
        case "sync":
            return installer.sync(root)
        case "upgrade":
            return installer.upgrade(root, args.dry_run)
        case "bundle":
            installer.build_pyz(Path(args.output).resolve(), full=args.full)
            print(f"wrote {args.output}")
            return 0
        case "check":
            staged = staged_changes(root, load_config(root)) if args.staged else None
            return run_check(root, args.change, args.base, staged).print()
        case "new":
            scopes = [x.strip() for x in args.scope.split(",") if x.strip()]
            return changes.new(root, args.type, args.slug, args.risk, args.ai_assisted, scopes)
        case "phase":
            return changes.phase(root, args.change, args.phase)
        case "approve":
            cfg = load_config(root)
            d = changes.change_dir(root, cfg, args.change)
            artifact = args.artifact if "/" in args.artifact else f"{d.relative_to(root).as_posix()}/{args.artifact}"
            return receipts.approve(root, cfg, d, artifact, args.approver, args.role)
        case "amend":
            cfg = load_config(root)
            d = changes.change_dir(root, cfg, args.change)
            artifact = args.artifact if "/" in args.artifact else f"{d.relative_to(root).as_posix()}/{args.artifact}"
            return receipts.amend(root, cfg, d, artifact, args.approver, args.role)
        case "approvals":
            cfg = load_config(root)
            name = args.platform or authority.settings(cfg)["platform"]
            client = platform.client_from_env(root, name, args.pr)
            return platform.verify(root, client, args.base).print()
        case "deviation" | "exception":
            kind = args.command
            fields = ({"policy": args.policy} if kind == "deviation" else {"rule": args.rule, "path": args.path})
            if args.action == "propose":
                return proposals.propose(root, kind, fields, args.reason or "", args.days, args.expires)
            if not args.approver or not args.role:
                raise HarnessError(f"{kind} approve needs --as <username> and --role <role>")
            identity = tuple(str(v) for v in fields.values())
            return proposals.approve(root, load_config(root), kind, identity, args.approver, args.role)
        case "config":
            value = load_config(root)
            for part in args.key.split("."):
                value = value.get(part) if isinstance(value, dict) else None
                if value is None:
                    break
            print(args.default if value is None else
                  (" ".join(str(v) for v in value) if isinstance(value, list) else value))
            return 0
        case "audit":
            cfg = load_config(root)
            report = Report()
            for log in sorted((root / paths(cfg)["changes"]).glob(f"*/{audit.AUDIT_FILE}")):
                report.extend(audit.verify_chain(root, log))
                if args.base:
                    report.extend(audit.verify_append_only(root, log, args.base))
            return report.print()
        case "tdd":
            cfg = load_config(root)
            if args.explain:
                return tdd.explain(root, cfg, args.paths).print()
            if not args.base:
                raise HarnessError("tdd needs --base (or --explain)")
            report = tdd.check_test_first(root, cfg, args.base).extend(tdd.check_weakened_tests(root, cfg, args.base))
            return report.print()
        case "arch":
            load_config(root)
            return architecture.check(root).print()
        case "contracts":
            return contracts.check(root, load_config(root), args.base).print()
        case "evidence":
            if args.action == "baseline":
                return evidence.baseline(root, load_config(root), args.dir, args.days)
            require = [k for k in args.require.split(",") if k] if args.require is not None else None
            return evidence.check(root, load_config(root), args.dir, require).print()
        case "status":
            return status.run(root, load_config(root), args.change, args.format)
        case "explain":
            cfg = None
            try:
                cfg = load_config(root)
            except SystemExit:
                pass  # explain works outside an installed repository too
            return explain.explain(args.topic, cfg, root)
        case "org":
            return policy.pull(root, load_config(root), args.source, args.ref)
        case "memory":
            load_config(root)
            if args.memory_action == "add":
                tags = [t.strip() for t in args.tags.split(",") if t.strip()]
                path = memory.add(root, args.type, args.title, tags, args.body, args.source, args.review_days)
                print(f"created {path.relative_to(root)}")
                return 0
            if args.memory_action == "index":
                memory.write_index(root)
                print(f"wrote {memory.MEMORY_DIR}/{memory.INDEX_FILE}")
                return 0
            tags = [t.strip() for t in args.tags.split(",") if t.strip()]
            for e in memory.search(root, args.query, args.type, tags, args.limit, args.all):
                print(f"[{e['origin']}] {e.get('id')} ({e.get('type')}) {e.get('title')} -> {e['path'].relative_to(root)}")
            return 0
        case "report":
            cfg = load_config(root)
            if args.kind == "trace":
                if not args.change:
                    raise SystemExit("report trace requires --change")
                data = reports.trace(root, cfg, changes.change_dir(root, cfg, args.change))
            elif args.kind == "flow":
                data = reports.flow(root, cfg, reports.parse_since(args.since))
            else:
                data = reports.dora(root, reports.parse_since(args.since), args.tags, args.window_days)
            text = reports.render(args.kind, data, args.format)
            if args.output:
                Path(args.output).write_text(text, encoding="utf-8")
                print(f"wrote {args.output}")
            else:
                print(text)
            return 0
        case "mcp":
            if args.print_config:
                return mcp.print_config(args.print_config)
            load_config(root)
            return mcp.serve(root)
        case "codeowners":
            return cmd_codeowners(root, args.check)
        case "commit-msg":
            return cmd_commit_msg(root, args.file)
        case "hooks":
            subprocess.run(["git", "config", "core.hooksPath", ".harness/hooks"], cwd=root, check=True)
            print("git hooks enabled (core.hooksPath=.harness/hooks)")
            return 0
        case "doctor":
            return cmd_doctor(root)
    return 2


if __name__ == "__main__":
    sys.exit(main())
