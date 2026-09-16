"""Brownfield adoption: detect stack, commands, infrastructure, contracts, CI and agent configuration."""
from __future__ import annotations

import json
import os
import re
import tomllib
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv", "__pycache__", ".harness",
             ".agents", ".claude", ".gemini", ".windsurf", ".terraform", ".next", "coverage", "bin", "obj"}
LANGUAGES = {".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript",
             ".go": "Go", ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
             ".scala": "Scala", ".swift": "Swift", ".dart": "Dart", ".tf": "Terraform", ".bicep": "Bicep"}
MAX_FILES = 20000


def _files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            out.append(Path(dirpath, name).relative_to(root).as_posix())
            if len(out) >= MAX_FILES:
                return out
    return out


def _read(root: Path, rel: str, limit: int = 200_000) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def _commands(root: Path, files: set[str]) -> dict[str, list[str]]:
    cmds: dict[str, list[str]] = {"build": [], "test": [], "lint": [], "run": []}

    def add(kind: str, cmd: str) -> None:
        if cmd not in cmds[kind]:
            cmds[kind].append(cmd)

    if "package.json" in files:
        try:
            scripts = json.loads(_read(root, "package.json")).get("scripts", {})
        except json.JSONDecodeError:
            scripts = {}
        runner = "pnpm" if "pnpm-lock.yaml" in files else "yarn" if "yarn.lock" in files else "npm run"
        for name, kind in (("build", "build"), ("test", "test"), ("lint", "lint"), ("dev", "run"), ("start", "run")):
            if name in scripts:
                add(kind, f"{runner} {name}")
    if "pyproject.toml" in files:
        text = _read(root, "pyproject.toml")
        prefix = "uv run " if "uv.lock" in files else "poetry run " if "poetry.lock" in files else ""
        if "pytest" in text or any(f.startswith("tests/") for f in files):
            add("test", f"{prefix}pytest")
        if "ruff" in text:
            add("lint", f"{prefix}ruff check .")
        if "mypy" in text:
            add("lint", f"{prefix}mypy .")
        try:
            if tomllib.loads(text).get("build-system"):
                add("build", "python -m build" if not prefix.startswith("uv") else "uv build")
        except tomllib.TOMLDecodeError:
            pass
    if "go.mod" in files:
        add("build", "go build ./...")
        add("test", "go test ./...")
        add("lint", "go vet ./...")
    if "pom.xml" in files:
        add("build", "mvn -B verify")
        add("test", "mvn -B test")
    if "build.gradle" in files or "build.gradle.kts" in files:
        wrapper = "./gradlew" if "gradlew" in files else "gradle"
        add("build", f"{wrapper} build")
        add("test", f"{wrapper} test")
    if any(f.endswith((".sln", ".csproj")) for f in files):
        add("build", "dotnet build")
        add("test", "dotnet test")
    if "Cargo.toml" in files:
        add("build", "cargo build")
        add("test", "cargo test")
        add("lint", "cargo clippy -- -D warnings")
    if "Gemfile" in files:
        add("test", "bundle exec rspec" if any(f.startswith("spec/") for f in files) else "bundle exec rake test")
    if "Makefile" in files:
        targets = set(re.findall(r"^([A-Za-z0-9_-]+):", _read(root, "Makefile"), re.M))
        for name, kind in (("build", "build"), ("test", "test"), ("lint", "lint"), ("run", "run")):
            if name in targets:
                add(kind, f"make {name}")
    return cmds


def detect(root: Path) -> dict:
    files = _files(root)
    fileset = set(files)
    languages = Counter(LANGUAGES[Path(f).suffix] for f in files if Path(f).suffix in LANGUAGES)

    infra = []
    checks = [
        ("Terraform/OpenTofu", lambda f: f.endswith(".tf")),
        ("Helm", lambda f: f.endswith("Chart.yaml")),
        ("Kustomize", lambda f: f.endswith("kustomization.yaml")),
        ("Docker", lambda f: Path(f).name in ("Dockerfile", "docker-compose.yml", "compose.yaml")),
        ("Pulumi", lambda f: Path(f).name == "Pulumi.yaml"),
        ("AWS CDK", lambda f: Path(f).name == "cdk.json"),
        ("Bicep", lambda f: f.endswith(".bicep")),
        ("Serverless Framework", lambda f: Path(f).name == "serverless.yml"),
    ]
    for label, predicate in checks:
        if any(predicate(f) for f in files):
            infra.append(label)
    if any(f.endswith((".yaml", ".yml", ".json")) and "AWSTemplateFormatVersion" in _read(root, f, 4000)
           for f in files if "cloudformation" in f.lower() or "template" in f.lower()):
        infra.append("CloudFormation")

    contracts = []
    for f in files:
        if f.endswith((".yaml", ".yml", ".json")) and not f.startswith(("docs/changes/", ".github/")):
            head = _read(root, f, 2000)
            if re.search(r'^\s*"?(openapi|swagger|asyncapi)"?\s*:', head, re.M):
                contracts.append(f)

    ci = [label for label, path in (("GitHub Actions", ".github/workflows"), ("GitLab CI", ".gitlab-ci.yml"),
                                    ("Jenkins", "Jenkinsfile"), ("Azure Pipelines", "azure-pipelines.yml"),
                                    ("Bitbucket Pipelines", "bitbucket-pipelines.yml"))
          if any(f == path or f.startswith(path + "/") for f in files)]
    agents = [f for f in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", ".cursorrules")
              if f in fileset] + (["Cursor rules (.cursor/rules)"] if any(f.startswith(".cursor/rules/") for f in files) else [])
    test_files = [f for f in files if re.search(r"(^|/)(tests?|spec|__tests__)/|_test\.|\.test\.|\.spec\.|Test\.java$", f)]
    scopes = []
    if any(Path(f).suffix in (".tsx", ".jsx", ".vue", ".svelte", ".html") for f in files):
        scopes.append("ui")
    if contracts:
        scopes.append("api")
    if any(re.search(r"(migrations?|schema\.sql|alembic|flyway|liquibase)", f) for f in files):
        scopes.append("data")
    if infra:
        scopes.append("infra")
    if any(re.search(r"\b(openai|anthropic|langchain|llama_index|transformers|bedrock|vertexai)\b",
                     _read(root, m, 50_000)) for m in ("package.json", "pyproject.toml", "requirements.txt", "go.mod")
           if m in fileset):
        scopes.append("ai")
    return {
        "languages": dict(languages.most_common()),
        "commands": _commands(root, fileset),
        "infrastructure": infra,
        "contracts": sorted(contracts),
        "ci": ci,
        "agent_files": agents,
        "test_files": len(test_files),
        "likely_scopes": scopes,
        "files_scanned": len(files),
    }


def fill_agents_md(text: str, commands: dict[str, list[str]]) -> str:
    labels = {"build": "Build", "test": "Test", "lint": "Lint/format", "run": "Run locally"}
    for kind, label in labels.items():
        if commands.get(kind):
            joined = " && ".join(commands[kind]) if kind != "run" else commands[kind][0]
            text = text.replace(f"- {label}: `<!-- sdlc:fill -->`", f"- {label}: `{joined}`")
    return text


HARNESS_SECTION_START = "## How work flows here (SDLC harness)"


def harness_block(template_agents_md: str) -> str:
    """Harness sections of the template AGENTS.md, for appending to an existing AGENTS.md."""
    idx = template_agents_md.find(HARNESS_SECTION_START)
    return template_agents_md[idx:] if idx >= 0 else ""


def render_adoption(data: dict, profile: str) -> str:
    cmds = data["commands"]
    lines = [
        "# Harness adoption report",
        "",
        "Generated by `sdlc init --adopt`. Review, then keep or delete this file.",
        "",
        "## Detected",
        "",
        "| Aspect | Result |",
        "|---|---|",
        f"| Languages (files) | {', '.join(f'{k} ({v})' for k, v in data['languages'].items()) or 'none'} |",
        f"| Build | {', '.join(cmds['build']) or 'not detected'} |",
        f"| Test | {', '.join(cmds['test']) or 'not detected'} |",
        f"| Lint | {', '.join(cmds['lint']) or 'not detected'} |",
        f"| Test files | {data['test_files']} |",
        f"| Infrastructure | {', '.join(data['infrastructure']) or 'none'} |",
        f"| API contracts | {', '.join(data['contracts']) or 'none'} |",
        f"| CI | {', '.join(data['ci']) or 'none'} |",
        f"| Existing agent instructions | {', '.join(data['agent_files']) or 'none'} |",
        f"| Likely scopes for changes | {', '.join(data['likely_scopes']) or 'none'} |",
        "",
        "## Applied",
        "",
        f"- Profile `{profile}`; detected commands written into `AGENTS.md` where placeholders existed.",
        f"- `[contracts] files` in `harness.toml`: {', '.join(data['contracts']) or 'none'}.",
        "",
        "## Suggested rollout",
        "",
        "1. Week 1 - `lite` profile, sensors `test_first = \"off\"`, `weakened_tests = \"warn\"`; fill `AGENTS.md`, roster and",
        "   CODEOWNERS; run `sdlc check` in CI without blocking merges.",
        "2. Week 2 - generate scanner evidence, run `sdlc evidence baseline` so existing findings become time-boxed",
        "   exceptions awaiting a security approver; enable branch protection with the `sdlc-gates` check.",
        "3. Week 3-4 - switch to `standard`, turn `weakened_tests` and `contracts` to `error`, start change records for",
        "   new work only (do not backfill history).",
        "4. Later - `test_first = \"error\"`, architecture rules from accepted ADRs, `regulated` where compliance requires it.",
        "",
        "## Open items",
        "",
    ]
    if not data["test_files"]:
        lines.append("- No tests detected: plan a test harness before enabling test-first as an error.")
    if not cmds["test"]:
        lines.append("- Test command not detected: fill it in `AGENTS.md`.")
    if data["agent_files"]:
        lines.append(f"- Existing agent instructions ({', '.join(data['agent_files'])}): merge relevant rules into "
                     "`AGENTS.md` and keep other files as thin pointers to it.")
    if data["infrastructure"]:
        lines.append("- Infrastructure code present: add `iac` to `require_evidence` and declare the `infra` scope.")
    if not data["ci"]:
        lines.append("- No CI detected: gates cannot be enforced until a pipeline runs `sdlc check`.")
    return "\n".join(lines) + "\n"
