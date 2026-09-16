"""Breaking-change detection for API contracts (OpenAPI 3.x, AsyncAPI 2.x/3.x) against a git base.

Policy: a breaking change is allowed only when the contract's `info.version` major is increased
(minor for 0.x versions, following Semantic Versioning). Direction matters:
- request-like data (what clients send / what the service receives) breaks when it becomes stricter;
- response-like data (what clients receive) breaks when it loses or loosens guarantees.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import yamlish
from .core import Report, git

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def _load(text: str, name: str):
    return json.loads(text) if name.endswith(".json") else yamlish.loads(text)


class _Doc:
    def __init__(self, data: dict):
        self.data = data

    def resolve(self, node, seen: frozenset = frozenset()):
        while isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/"):
            ref = node["$ref"]
            if ref in seen:
                return {}
            seen = seen | {ref}
            target = self.data
            for part in ref[2:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                target = target.get(part, {}) if isinstance(target, dict) else {}
            node = target
        return node if node is not None else {}


def _types(schema: dict) -> set[str]:
    t = schema.get("type")
    if t is None:
        return set()
    types = set(t) if isinstance(t, list) else {t}
    if schema.get("nullable"):
        types.add("null")
    return types


class Differ:
    def __init__(self, old: dict, new: dict):
        self.old, self.new = _Doc(old), _Doc(new)
        self.breaking: list[str] = []
        self.notes: list[str] = []
        self._seen: set[tuple[int, int, str]] = set()

    def brk(self, where: str, msg: str) -> None:
        self.breaking.append(f"{where}: {msg}")

    # ------------------------------------------------------------------ schemas
    def schema(self, old, new, direction: str, where: str) -> None:
        old, new = self.old.resolve(old or {}), self.new.resolve(new or {})
        key = (id(old), id(new), direction)
        if key in self._seen or not isinstance(old, dict) or not isinstance(new, dict):
            return
        self._seen.add(key)
        ot, nt = _types(old), _types(new)
        if ot and nt and ot != nt:
            widened = ot < nt or (ot == {"integer"} and "number" in nt)
            if direction == "request" and widened:
                self.notes.append(f"{where}: type widened {sorted(ot)} -> {sorted(nt)}")
            else:
                self.brk(where, f"type changed {sorted(ot)} -> {sorted(nt)}")
        if old.get("format") and new.get("format") != old.get("format"):
            self.brk(where, f"format changed {old.get('format')} -> {new.get('format')}")
        if "enum" in old or "enum" in new:
            before, after = set(map(str, old.get("enum", []))), set(map(str, new.get("enum", [])))
            if direction == "request" and "enum" in new and (before - after or "enum" not in old):
                self.brk(where, f"enum values no longer accepted: {sorted(before - after) or 'restricted'}")
            if direction == "response" and "enum" in old and (after - before or "enum" not in new):
                self.brk(where, f"new enum values may be returned: {sorted(after - before) or 'unrestricted'}")
        if direction == "request":
            for name, stricter in (("maxLength", lambda o, n: n < o), ("maxItems", lambda o, n: n < o),
                                   ("maximum", lambda o, n: n < o), ("minLength", lambda o, n: n > o),
                                   ("minItems", lambda o, n: n > o), ("minimum", lambda o, n: n > o)):
                if name in new and (name not in old or stricter(old[name], new[name])):
                    self.brk(where, f"{name} tightened {old.get(name)} -> {new[name]}")
            if old.get("pattern") != new.get("pattern") and new.get("pattern"):
                self.brk(where, "pattern added or changed")

        oprops, nprops = old.get("properties", {}) or {}, new.get("properties", {}) or {}
        oreq, nreq = set(old.get("required", []) or []), set(new.get("required", []) or [])
        if direction == "request":
            for prop in sorted(nreq - oreq):
                self.brk(where, f"property '{prop}' is now required")
            if new.get("additionalProperties") is False:
                for prop in sorted(set(oprops) - set(nprops)):
                    self.brk(where, f"property '{prop}' removed and additional properties are rejected")
        else:
            for prop in sorted(set(oprops) - set(nprops)):
                self.brk(where, f"property '{prop}' removed from response")
            for prop in sorted(oreq - nreq):
                self.brk(where, f"property '{prop}' is no longer guaranteed (removed from required)")
        for prop in sorted(set(oprops) & set(nprops)):
            self.schema(oprops[prop], nprops[prop], direction, f"{where}.{prop}")
        if "items" in old and "items" in new:
            self.schema(old["items"], new["items"], direction, f"{where}[]")

    # ------------------------------------------------------------------ OpenAPI
    def _params(self, doc: _Doc, path_item: dict, op: dict) -> dict:
        out = {}
        for p in list(path_item.get("parameters", [])) + list(op.get("parameters", [])):
            p = doc.resolve(p)
            if isinstance(p, dict) and "name" in p:
                out[(p["name"], p.get("in"))] = p
        return out

    def _content(self, doc: _Doc, holder: dict) -> dict:
        return (doc.resolve(holder) or {}).get("content", {}) or {}

    def openapi(self) -> None:
        opaths, npaths = self.old.data.get("paths", {}) or {}, self.new.data.get("paths", {}) or {}
        for path in opaths:
            if path not in npaths:
                self.brk(path, "path removed")
                continue
            oitem, nitem = self.old.resolve(opaths[path]), self.new.resolve(npaths[path])
            for method in HTTP_METHODS:
                if method not in oitem:
                    continue
                where = f"{method.upper()} {path}"
                if method not in nitem:
                    self.brk(where, "operation removed")
                    continue
                self._operation(where, oitem, nitem, oitem[method], nitem[method])

    def _operation(self, where, oitem, nitem, oop, nop) -> None:
        oparams, nparams = self._params(self.old, oitem, oop), self._params(self.new, nitem, nop)
        for key, p in nparams.items():
            label = f"{where} parameter {key[1]}:{key[0]}"
            if key not in oparams:
                if p.get("required"):
                    self.brk(label, "new required parameter")
                continue
            if p.get("required") and not oparams[key].get("required"):
                self.brk(label, "parameter became required")
            self.schema(oparams[key].get("schema"), p.get("schema"), "request", label)
        for key in oparams.keys() - nparams.keys():
            self.notes.append(f"{where} parameter {key[1]}:{key[0]} removed")

        obody, nbody = self.old.resolve(oop.get("requestBody") or {}), self.new.resolve(nop.get("requestBody") or {})
        if nbody.get("required") and not obody.get("required"):
            self.brk(f"{where} requestBody", "request body became required")
        ocontent, ncontent = obody.get("content", {}) or {}, nbody.get("content", {}) or {}
        for media in ocontent:
            if media not in ncontent:
                self.brk(f"{where} requestBody", f"media type {media} no longer accepted")
            else:
                self.schema(ocontent[media].get("schema"), ncontent[media].get("schema"), "request",
                            f"{where} request {media}")

        oresp, nresp = oop.get("responses", {}) or {}, nop.get("responses", {}) or {}
        for status in oresp:
            if str(status).startswith(("2", "3")) and status not in nresp:
                self.brk(f"{where} response {status}", "response removed")
                continue
            if status not in nresp:
                continue
            oc, nc = self._content(self.old, oresp[status]), self._content(self.new, nresp[status])
            for media in oc:
                if media not in nc:
                    self.brk(f"{where} response {status}", f"media type {media} removed")
                else:
                    self.schema(oc[media].get("schema"), nc[media].get("schema"), "response",
                                f"{where} response {status} {media}")

        osec = oop.get("security", self.old.data.get("security", [])) or []
        nsec = nop.get("security", self.new.data.get("security", [])) or []
        if not osec and nsec and {} not in nsec:
            self.brk(where, "authentication is now required")

    # ------------------------------------------------------------------ AsyncAPI
    def _messages(self, doc: _Doc, holder) -> dict:
        holder = doc.resolve(holder or {})
        if isinstance(holder, dict) and "oneOf" in holder:
            items = [doc.resolve(m) for m in holder["oneOf"]]
        elif isinstance(holder, dict) and ("payload" in holder or "name" in holder):
            items = [holder]
        elif isinstance(holder, dict):
            items = [doc.resolve(m) for m in holder.values()]
        elif isinstance(holder, list):
            items = [doc.resolve(m) for m in holder]
        else:
            items = []
        return {m.get("name") or m.get("messageId") or str(i): m for i, m in enumerate(items) if isinstance(m, dict)}

    def asyncapi(self) -> None:
        ochan, nchan = self.old.data.get("channels", {}) or {}, self.new.data.get("channels", {}) or {}
        for name in ochan:
            if name not in nchan:
                self.brk(f"channel {name}", "channel removed")
        major = str(self.new.data.get("asyncapi", "2")).split(".")[0]
        if major == "2":
            for name in set(ochan) & set(nchan):
                for action, direction in (("publish", "request"), ("subscribe", "response")):
                    oop, nop = (ochan[name] or {}).get(action), (nchan[name] or {}).get(action)
                    if oop and not nop:
                        self.brk(f"channel {name}", f"{action} operation removed")
                    elif oop and nop:
                        self._compare_messages(f"{action} {name}", oop.get("message"), nop.get("message"), direction)
        else:
            oops, nops = self.old.data.get("operations", {}) or {}, self.new.data.get("operations", {}) or {}
            for op_name, oop in oops.items():
                if op_name not in nops:
                    self.brk(f"operation {op_name}", "operation removed")
                    continue
                direction = "response" if oop.get("action") == "send" else "request"
                omsgs = oop.get("messages") or self.old.resolve(oop.get("channel", {})).get("messages", {})
                nmsgs = nops[op_name].get("messages") or self.new.resolve(nops[op_name].get("channel", {})).get("messages", {})
                self._compare_messages(f"operation {op_name}", omsgs, nmsgs, direction)

    def _compare_messages(self, where: str, old, new, direction: str) -> None:
        omsgs, nmsgs = self._messages(self.old, old), self._messages(self.new, new)
        for key, msg in omsgs.items():
            if key not in nmsgs:
                if direction == "response":
                    self.brk(where, f"message '{key}' no longer produced")
                else:
                    self.brk(where, f"message '{key}' no longer accepted")
                continue
            self.schema(msg.get("payload"), nmsgs[key].get("payload"), direction, f"{where} message {key}")


def _semver(version) -> tuple[int, int, int] | None:
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", str(version or ""))
    return tuple(int(x or 0) for x in m.groups()) if m else None


def diff(old: dict, new: dict) -> Differ:
    d = Differ(old, new)
    if "openapi" in new or "swagger" in new:
        d.openapi()
    elif "asyncapi" in new:
        d.asyncapi()
    return d


def check(root: Path, cfg: dict, base: str) -> Report:
    report = Report()
    for rel in cfg.get("contracts", {}).get("files", []):
        path = root / rel
        if not path.exists():
            report.error(f"contract not found: {rel}")
            continue
        before = git(root, "show", f"{base}:{rel}", check=False)
        if not before:
            report.warn(f"{rel}: new contract (no base version to compare)")
            continue
        try:
            old, new = _load(before, rel), _load(path.read_text(encoding="utf-8"), rel)
        except (yamlish.YamlError, json.JSONDecodeError) as exc:
            report.error(f"{rel}: cannot parse contract ({exc})")
            continue
        if not isinstance(old, dict) or not isinstance(new, dict) or not ({"openapi", "asyncapi", "swagger"} & new.keys()):
            report.error(f"{rel}: not an OpenAPI 3.x or AsyncAPI document")
            continue
        d = diff(old, new)
        for note in d.notes:
            report.warn(f"{rel}: {note}")
        if not d.breaking:
            continue
        ov, nv = _semver(old.get("info", {}).get("version")), _semver(new.get("info", {}).get("version"))
        allowed = bool(ov and nv and (nv[0] > ov[0] or (ov[0] == 0 and nv[0] == 0 and nv[1] > ov[1])))
        for b in d.breaking:
            if allowed:
                report.warn(f"{rel}: breaking (allowed by version {'.'.join(map(str, ov))} -> "
                            f"{'.'.join(map(str, nv))}): {b}")
            else:
                report.error(f"{rel}: breaking change without major version bump: {b}")
    return report
