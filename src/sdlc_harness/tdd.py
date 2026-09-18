"""Git-history sensors: test-first ordering and weakened tests.

Both are heuristics over commits in `base..HEAD`, language-agnostic by file patterns:
- test-first: a behaviour commit (feat/fix/perf or untyped) touching source code must be preceded by, or include,
  a change to test code within the same range;
- weakened tests: added skip/ignore/focus markers or deleted test files.
A commit trailer `TDD-Waiver: <reason>` or `Test-Waiver: <reason>` records a justified exception.
"""
from __future__ import annotations

import functools
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


@functools.lru_cache(maxsize=512)
def _pattern(glob: str) -> re.Pattern:
    """Git-style glob: `**` spans directories (and may match none), `*` and `?` stay within one segment.

    Plain `fnmatch` makes `*` cross `/`, which classifies `src/a/b.ts` as matching `src/*.ts`, and makes `**` require
    at least one directory, so `src/**/*.ts` misses `src/proxy.ts`. Both mistakes are silent, so we translate instead.
    """
    segments, out = glob.split("/"), []
    for i, seg in enumerate(segments):
        last = i == len(segments) - 1
        if seg == "**":  # a trailing '**' matches everything below; otherwise it consumes its own separator
            out.append(".*" if last else "(?:[^/]+/)*")
            continue
        out.append("".join("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c) for c in seg))
        if not last:
            out.append("/")
    return re.compile("^" + "".join(out) + "$")


def _match(path: str, globs: list[str]) -> bool:
    return any(_pattern(g).match(path) for g in globs)


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


def explain(root: Path, cfg: dict) -> Report:
    """Print how every tracked file is classified, so silent misconfiguration is visible before it matters."""
    report = Report()
    tdd_cfg = cfg.get("tdd", {})
    test_globs = tdd_cfg.get("test_globs") or DEFAULT_TEST_GLOBS
    source_globs = tdd_cfg.get("source_globs") or []
    buckets: dict[str, list[str]] = {"test": [], "source": [], "other": []}
    for path in git(root, "ls-files").splitlines():
        buckets[classify(path, cfg)].append(path)
    print(f"test_globs   = {test_globs}{' (default)' if not tdd_cfg.get('test_globs') else ''}")
    print(f"source_globs = {source_globs or 'unset: any file with a known code extension counts as source'}")
    ignored = [p for p in buckets["other"] if p.startswith(IGNORED_PREFIXES)]
    buckets["other"] = [p for p in buckets["other"] if not p.startswith(IGNORED_PREFIXES)]
    for kind in ("test", "source", "other"):
        files = buckets[kind]
        print(f"\n{kind} ({len(files)})")
        for path in files[:20]:
            print(f"  {path}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more")
    print(f"\nnot considered: {len(ignored)} file(s) under docs/ and harness directories")
    missed = [p for p in buckets["other"]
              if Path(p).suffix in CODE_EXTENSIONS and not p.startswith(IGNORED_PREFIXES)]
    if missed and source_globs:
        report.warn(f"{len(missed)} file(s) with a code extension are classified 'other', so the test-first sensor "
                    f"ignores them (e.g. {missed[0]}); widen tdd.source_globs in harness.toml")
    return report
