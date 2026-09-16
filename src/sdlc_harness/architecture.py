"""Executable architecture rules: layer dependencies checked against source imports.

`.harness/architecture.toml` declares layers (where their files live and how other code imports them) and rules
(which layers or third-party modules a layer must not depend on). Import extraction is regex-based per language,
so it is fast and dependency-free but not a compiler: dynamic imports and reflection are out of scope.
"""
from __future__ import annotations

import fnmatch
import posixpath
import re
from pathlib import Path

from .core import Report, git, load_toml

ARCH_FILE = ".harness/architecture.toml"

PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|^\s*from\s+(\.*[\w.]*)\s+import\b", re.M)
JS_IMPORT = re.compile(r"""(?:^|\s)(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|^\s*import\s*['"]([^'"]+)['"]"""
                       r"""|\brequire\(\s*['"]([^'"]+)['"]\s*\)|\bimport\(\s*['"]([^'"]+)['"]\s*\)""", re.M)
GO_IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)\)", re.M | re.S)
GO_IMPORT_LINE = re.compile(r'^import\s+(?:\w+\s+)?"([^"]+)"', re.M)
JVM_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)", re.M)
CS_USING = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;", re.M)
RUST_USE = re.compile(r"^\s*(?:pub\s+)?use\s+([\w:]+)", re.M)
PHP_USE = re.compile(r"^\s*use\s+([\w\\]+)", re.M)

LANG = {
    ".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".cjs": "js",
    ".vue": "js", ".svelte": "js", ".go": "go", ".java": "jvm", ".kt": "jvm", ".kts": "jvm", ".scala": "jvm",
    ".cs": "cs", ".rs": "rust", ".php": "php",
}


def _glob(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or (pattern.endswith("/**") and path.startswith(pattern[:-3] + "/"))


def imports(path: str, text: str) -> list[tuple[int, str, str]]:
    """(line, kind, target) where kind is 'module' (import name) or 'path' (repo-relative path)."""
    lang = LANG.get(Path(path).suffix)
    found: list[tuple[int, str, str]] = []

    def line_of(pos: int) -> int:
        return text.count("\n", 0, pos) + 1

    if lang == "python":
        for m in PY_IMPORT.finditer(text):
            if m.group(1):
                for name in m.group(1).split(","):
                    found.append((line_of(m.start()), "module", name.strip()))
            elif m.group(2).startswith("."):
                dots = len(m.group(2)) - len(m.group(2).lstrip("."))
                base = posixpath.dirname(path)
                for _ in range(dots - 1):
                    base = posixpath.dirname(base)
                rest = m.group(2).lstrip(".").replace(".", "/")
                found.append((line_of(m.start()), "path", posixpath.normpath(posixpath.join(base, rest))))
            else:
                found.append((line_of(m.start()), "module", m.group(2)))
    elif lang == "js":
        for m in JS_IMPORT.finditer(text):
            spec = next(g for g in m.groups() if g)
            start = m.start() + (1 if text[m.start()].isspace() else 0)  # the regex may consume the preceding newline
            if spec.startswith("."):
                found.append((line_of(start), "path", posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))))
            else:
                found.append((line_of(start), "module", spec))
    elif lang == "go":
        for block in GO_IMPORT_BLOCK.finditer(text):
            for m in re.finditer(r'"([^"]+)"', block.group(1)):
                found.append((line_of(block.start(1) + m.start()), "module", m.group(1)))
        for m in GO_IMPORT_LINE.finditer(text):
            found.append((line_of(m.start()), "module", m.group(1)))
    elif lang == "jvm":
        found += [(line_of(m.start()), "module", m.group(1)) for m in JVM_IMPORT.finditer(text)]
    elif lang == "cs":
        found += [(line_of(m.start()), "module", m.group(1)) for m in CS_USING.finditer(text)]
    elif lang == "rust":
        found += [(line_of(m.start()), "module", m.group(1).replace("::", ".")) for m in RUST_USE.finditer(text)]
    elif lang == "php":
        found += [(line_of(m.start()), "module", m.group(1).replace("\\", ".")) for m in PHP_USE.finditer(text)]
    return found


def _module_match(name: str, prefix: str) -> bool:
    if name == prefix:
        return True
    return any(name.startswith(prefix + sep) for sep in "./:")


def _layer_of_path(target: str, layers: list[dict]) -> str | None:
    candidates = [target, target + ".py", target + ".ts", target + ".js", target + "/index.ts", target + "/index.js",
                  target + "/__init__.py", target + "/x"]
    for layer in layers:
        if any(_glob(c, g) for c in candidates for g in layer.get("paths", [])):
            return layer["name"]
    return None


def _layer_of_module(name: str, layers: list[dict]) -> str | None:
    best, best_len = None, -1
    for layer in layers:
        for prefix in layer.get("modules", []):
            if _module_match(name, prefix) and len(prefix) > best_len:
                best, best_len = layer["name"], len(prefix)
    return best


def check(root: Path, files: list[str] | None = None) -> Report:
    report = Report()
    path = root / ARCH_FILE
    if not path.exists():
        return report
    spec = load_toml(path)
    layers, rules = spec.get("layers", []), spec.get("rules", [])
    names = {layer["name"] for layer in layers}
    for rule in rules:
        for ref in [rule.get("layer")] + rule.get("forbid_layers", []) + rule.get("allow_layers", []):
            if ref not in names:
                report.error(f"{ARCH_FILE}: rule references unknown layer '{ref}'")
        if rule.get("adr") and not (root / rule["adr"]).exists():
            report.error(f"{ARCH_FILE}: rule for '{rule.get('layer')}' cites missing ADR {rule['adr']}")
    if report.errors or not layers:
        return report

    tracked = files if files is not None else git(root, "ls-files").splitlines()
    by_layer: dict[str, dict] = {}
    for r in rules:
        merged = by_layer.setdefault(r["layer"], {"forbid_layers": [], "forbid_imports": []})
        merged["forbid_layers"] += r.get("forbid_layers", [])
        merged["forbid_imports"] += r.get("forbid_imports", [])
        if "allow_layers" in r:
            merged["allow_layers"] = merged.get("allow_layers", []) + r["allow_layers"]
        if r.get("adr"):
            merged["adr"] = r["adr"]
    for rel in tracked:
        if Path(rel).suffix not in LANG:
            continue
        own = next((layer["name"] for layer in layers if any(_glob(rel, g) for g in layer.get("paths", []))), None)
        rule = by_layer.get(own)
        if rule is None or not (root / rel).is_file():
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        adr = f" [{rule['adr']}]" if rule.get("adr") else ""
        for line, kind, target in imports(rel, text):
            to = _layer_of_path(target, layers) if kind == "path" else _layer_of_module(target, layers)
            if to and to != own:
                if to in rule["forbid_layers"] or ("allow_layers" in rule and to not in rule["allow_layers"]):
                    report.error(f"{rel}:{line}: layer '{own}' must not depend on '{to}' ({target}){adr}")
            elif kind == "module" and not to:
                for banned in rule["forbid_imports"]:
                    if _module_match(target, banned):
                        report.error(f"{rel}:{line}: layer '{own}' must not import '{target}'{adr}")
    return report
