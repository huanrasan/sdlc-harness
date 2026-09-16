"""Git-history sensors: test-first ordering and weakened tests.

Both are heuristics over commits in `base..HEAD`, language-agnostic by file patterns:
- test-first: a behaviour commit (feat/fix/perf or untyped) touching source code must be preceded by, or include,
  a change to test code within the same range;
- weakened tests: added skip/ignore/focus markers or deleted test files.
A commit trailer `TDD-Waiver: <reason>` or `Test-Waiver: <reason>` records a justified exception.
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .core import Report, git

CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".kts", ".scala",
                   ".cs", ".fs", ".rb", ".php", ".rs", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".dart",
                   ".ex", ".exs", ".clj", ".vue", ".svelte"}
DEFAULT_TEST_GLOBS = ["test/**", "tests/**", "**/test/**", "**/tests/**", "**/__tests__/**", "**/test_*.py",
                      "**/*_test.py", "**/*_test.go", "**/*.test.*", "**/*.spec.*", "**/*Test.java", "**/*Tests.java",
                      "**/*Test.kt", "**/*Tests.cs", "**/*_spec.rb", "spec/**", "**/src/test/**"]
IGNORED_PREFIXES = ("docs/", ".harness/", ".agents/", ".claude/", ".gemini/", ".windsurf/", ".github/", ".gitlab")
BEHAVIOUR_TYPES = {"feat", "fix", "perf"}
NON_BEHAVIOUR_RE = re.compile(r"^(docs|style|refactor|test|build|ci|chore|revert)(\(|!|:)")
WEAKENING_PATTERNS = [
    (re.compile(r"@(pytest\.mark\.(skip|xfail)|unittest\.skip)|pytest\.skip\("), "python skip/xfail"),
    (re.compile(r"\b(it|test|describe|context)\.(skip|only|todo)\(|\bx(it|describe|test)\(|\bf(it|describe)\("),
     "js/ts skip/only/focus"),
    (re.compile(r"@(Disabled|Ignore)\b"), "JUnit @Disabled/@Ignore"),
    (re.compile(r"\bt\.Skip(f|Now)?\("), "go t.Skip"),
    (re.compile(r"\[(Ignore|Explicit)\b|\bSkip\s*=\s*\""), "C# ignore/skip"),
    (re.compile(r"#\[ignore\]"), "rust #[ignore]"),
]
RUBY_WEAKENING = re.compile(r"^\s*(skip|pending|xit)\b")


def _match(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or (g.startswith("**/") and fnmatch.fnmatch(path, g[3:])) for g in globs)


def classify(path: str, cfg: dict) -> str:
    """'test', 'source' or 'other'."""
    tdd_cfg = cfg.get("tdd", {})
    if path.startswith(IGNORED_PREFIXES):
        return "other"
    if _match(path, tdd_cfg.get("test_globs") or DEFAULT_TEST_GLOBS):
        return "test"
    source_globs = tdd_cfg.get("source_globs") or []
    if source_globs:
        return "source" if _match(path, source_globs) else "other"
    return "source" if Path(path).suffix in CODE_EXTENSIONS else "other"


def _commits(root: Path, base: str) -> list[tuple[str, str]]:
    shas = git(root, "rev-list", "--reverse", "--no-merges", f"{base}..HEAD").split()
    return [(sha, git(root, "log", "-1", "--format=%B", sha)) for sha in shas]


def _changed(root: Path, sha: str) -> list[tuple[str, str]]:
    out = git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", "--root", sha)
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        rows.append((parts[0][0], parts[-1]))
    return rows


def _waived(message: str, trailer: str) -> bool:
    return re.search(rf"^{trailer}: \S.*$", message, re.M) is not None


def check_test_first(root: Path, cfg: dict, base: str) -> Report:
    report = Report()
    tests_seen = False
    for sha, message in _commits(root, base):
        changed = _changed(root, sha)
        kinds = {classify(p, cfg) for status, p in changed if status != "D"}
        tests_seen = tests_seen or "test" in kinds
        subject = message.splitlines()[0] if message else ""
        typed = subject.split(":")[0].split("(")[0].rstrip("!")
        behaviour = typed in BEHAVIOUR_TYPES or not NON_BEHAVIOUR_RE.match(subject)
        if "source" in kinds and behaviour and not tests_seen and not _waived(message, "TDD-Waiver"):
            report.error(f"test-first: commit {sha[:10]} '{subject}' changes source before any test change "
                         f"(add tests first or a 'TDD-Waiver: <reason>' trailer)")
        elif "source" in kinds and _waived(message, "TDD-Waiver") and not tests_seen:
            report.warn(f"test-first waived in {sha[:10]}: {re.search(r'^TDD-Waiver: (.*)$', message, re.M).group(1)}")
    return report


def check_weakened_tests(root: Path, cfg: dict, base: str) -> Report:
    report = Report()
    commits = _commits(root, base)
    waiver = next((m for _, m in commits if _waived(m, "Test-Waiver")), None)
    findings = []
    for status, path in _diff_names(root, base):
        if classify(path, cfg) != "test":
            continue
        if status == "D":
            findings.append(f"test file deleted: {path}")
            continue
        diff = git(root, "diff", f"{base}...HEAD", "--unified=0", "--", path)
        for line in diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                patterns = WEAKENING_PATTERNS + ([(RUBY_WEAKENING, "ruby skip/pending")] if path.endswith(".rb") else [])
                for pattern, label in patterns:
                    if pattern.search(line[1:]):
                        findings.append(f"{path}: added {label}: {line[1:].strip()[:80]}")
                        break
    for f in findings:
        if waiver:
            report.warn(f"weakened test (waived: {re.search(r'^Test-Waiver: (.*)$', waiver, re.M).group(1)}): {f}")
        else:
            report.error(f"weakened test: {f} (fix the test or add a 'Test-Waiver: <reason>' trailer)")
    return report


def _diff_names(root: Path, base: str) -> list[tuple[str, str]]:
    rows = []
    for line in git(root, "diff", "--name-status", f"{base}...HEAD").splitlines():
        parts = line.split("\t")
        rows.append((parts[0][0], parts[-1]))
    return rows
