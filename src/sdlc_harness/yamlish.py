"""Minimal YAML reader for API contracts (standard library only).

Supports the subset used by typical OpenAPI/AsyncAPI documents: block mappings and sequences, quoted and plain
scalars, flow collections, literal/folded block scalars and comments. Anchors, aliases, tags and multi-document
streams are rejected explicitly instead of being misread; convert such files to JSON or simplify them.
"""
from __future__ import annotations

import json
import re


class YamlError(ValueError):
    pass


_INT_RE = re.compile(r"^[-+]?(0|[1-9][0-9_]*)$")
_FLOAT_RE = re.compile(r"^[-+]?(\.[0-9]+|[0-9][0-9_]*(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")


def loads(text: str):
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return _Parser(text).parse()


def _strip_comment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote and (quote == "'" or line[i - 1] != "\\"):
                quote = None
        elif ch in "'\"" and (i == 0 or line[i - 1] in " \t[{,:-"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
            "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0",
            "L": "\u2028", "P": "\u2029"}
_HEX = {"x": 2, "u": 4, "U": 8}


def _fold(body: str) -> str:
    """YAML flow-scalar line folding: single breaks become spaces, empty lines become newlines."""
    lines = body.split("\n")
    if len(lines) == 1:
        return body
    out, pending = lines[0].rstrip(" \t"), 0
    for i, line in enumerate(lines[1:], start=1):
        last = i == len(lines) - 1
        line = line.lstrip(" \t") if last else line.strip(" \t")
        if not line and not last:
            pending += 1
            continue
        out += ("\n" * pending if pending else " ") + line
        pending = 0
    return out


def _double_quoted(body: str) -> str:
    # Line folding of multi-line double-quoted scalars, then YAML escapes.
    body = _fold(re.sub(r"\\\n[ \t]*", "", body))
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        code = body[i + 1] if i + 1 < len(body) else ""
        if code in _HEX:
            n = _HEX[code]
            out.append(chr(int(body[i + 2:i + 2 + n], 16)))
            i += 2 + n
        elif code in _ESCAPES:
            out.append(_ESCAPES[code])
            i += 2
        else:
            raise YamlError(f"invalid escape \\{code}")
    return "".join(out)


def _scalar(token: str):
    token = token.strip()
    if not token:
        return None
    if token[0] in "&*!":
        raise YamlError(f"anchors, aliases and tags are not supported: {token[:30]}")
    if token[0] == '"':
        if not token.endswith('"') or len(token) == 1:
            raise YamlError(f"unterminated string: {token[:30]}")
        return _double_quoted(token[1:-1])
    if token[0] == "'":
        if not token.endswith("'") or len(token) == 1:
            raise YamlError(f"unterminated string: {token[:30]}")
        return _fold(token[1:-1]).replace("''", "'")
    if token[0] in "[{":
        value, pos = _flow(token, 0)
        if token[pos:].strip():
            raise YamlError(f"unexpected text after flow collection: {token[pos:][:30]}")
        return value
    low = token.lower()
    if low in ("true", "yes", "on") and token in ("true", "True", "TRUE"):
        return True
    if token in ("false", "False", "FALSE"):
        return False
    if low in ("null", "~"):
        return None
    if _INT_RE.match(token):
        return int(token.replace("_", ""))
    if _FLOAT_RE.match(token) and any(c.isdigit() for c in token):
        return float(token.replace("_", ""))
    return token


def _flow(s: str, pos: int):
    def skip(p):
        while p < len(s) and s[p] in " \t\n":
            p += 1
        return p

    pos = skip(pos)
    if s[pos] == "[":
        items, pos = [], skip(pos + 1)
        while s[pos] != "]":
            value, pos = _flow(s, pos)
            items.append(value)
            pos = skip(pos)
            if s[pos] == ",":
                pos = skip(pos + 1)
        return items, pos + 1
    if s[pos] == "{":
        obj, pos = {}, skip(pos + 1)
        while s[pos] != "}":
            key, pos = _flow(s, pos)
            pos = skip(pos)
            if s[pos] != ":":
                raise YamlError(f"expected ':' in flow mapping: {s[:40]}")
            value, pos = _flow(s, pos + 1)
            obj[key] = value
            pos = skip(pos)
            if s[pos] == ",":
                pos = skip(pos + 1)
        return obj, pos + 1
    if s[pos] in "'\"":
        quote, end = s[pos], pos + 1
        while end < len(s) and not (s[end] == quote and (quote == "'" or s[end - 1] != "\\")):
            end += 1
        return _scalar(s[pos:end + 1]), end + 1
    end = pos
    while end < len(s) and s[end] not in ",]}" and not (s[end] == ":" and (end + 1 == len(s) or s[end + 1] in " ,]}")):
        end += 1
    return _scalar(s[pos:end]), end


def _split_key(content: str) -> tuple[str, str] | None:
    quote = None
    for i, ch in enumerate(content):
        if quote:
            if ch == quote and (quote == "'" or content[i - 1] != "\\"):
                quote = None
        elif ch in "'\"" and i == 0:
            quote = ch
        elif ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
            return content[:i], content[i + 1:].strip()
    return None


class _Parser:
    def __init__(self, text: str):
        self.raw = text.replace("\t", "    ").splitlines()
        self.lines: list[tuple[int, str, int]] = []  # (indent, content, raw index)
        for idx, raw in enumerate(self.raw):
            content = _strip_comment(raw)
            if not content.strip() or content.strip() in ("---", "..."):
                if raw.startswith("---") and self.lines:
                    raise YamlError("multi-document streams are not supported")
                continue
            self.lines.append((len(content) - len(content.lstrip()), content.strip(), idx))
        self.i = 0

    def parse(self):
        if not self.lines:
            return None
        value = self._node(self.lines[0][0])
        if self.i < len(self.lines):
            raise YamlError(f"unexpected content at line {self.lines[self.i][2] + 1}")
        return value

    def _node(self, indent: int):
        ind, content, _ = self.lines[self.i]
        if content == "-" or content.startswith("- "):
            return self._sequence(ind)
        if _split_key(content) is None:
            self.i += 1
            return _scalar(content)
        return self._mapping(ind)

    def _mapping(self, indent: int) -> dict:
        obj: dict = {}
        while self.i < len(self.lines):
            ind, content, raw_idx = self.lines[self.i]
            if ind < indent:
                break
            if ind > indent:
                raise YamlError(f"bad indentation at line {raw_idx + 1}")
            if content.startswith("- ") or content == "-":
                break
            split = _split_key(content)
            if split is None:
                raise YamlError(f"expected 'key: value' at line {raw_idx + 1}")
            key, rest = _scalar(split[0]), split[1]
            if key in obj:
                raise YamlError(f"duplicate key '{key}' at line {raw_idx + 1}")
            self.i += 1
            obj[key] = self._value(rest, indent, raw_idx)
        return obj

    def _value(self, rest: str, indent: int, raw_idx: int):
        if rest and rest[0] in "|>":
            return self._block_scalar(rest, indent, raw_idx)
        if rest:
            return _scalar(self._continuation(rest, indent, raw_idx))
        if self.i < len(self.lines):
            nind, ncontent, nraw = self.lines[self.i]
            if nind > indent and ncontent[0] in "[{":
                self.i += 1
                return _scalar(self._continuation(ncontent, indent, nraw))
            if nind > indent:
                return self._node(nind)
            if nind == indent and (ncontent.startswith("- ") or ncontent == "-"):
                return self._sequence(nind)
        return None

    def _continuation(self, first: str, indent: int, raw_idx: int) -> str:
        """Join following, more-indented raw lines into a multi-line flow collection or scalar."""
        def balanced(text: str) -> bool:
            depth, quote = 0, None
            for i, ch in enumerate(text):
                if quote:
                    if ch == quote and (quote == "'" or text[i - 1] != "\\"):
                        quote = None
                elif ch in "'\"":
                    quote = ch
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
            return depth <= 0 and quote is None

        text, j = first, raw_idx + 1
        is_flow = first[0] in "[{"
        is_quoted = first[0] in "'\""
        while j < len(self.raw):
            if is_flow or is_quoted:
                if balanced(text):
                    break
            else:
                nxt = self.raw[j]
                if not nxt.strip():
                    k = j
                    while k < len(self.raw) and not self.raw[k].strip():
                        k += 1
                    if k == len(self.raw) or len(self.raw[k]) - len(self.raw[k].lstrip()) <= indent:
                        break
                elif len(nxt) - len(nxt.lstrip()) <= indent or nxt.strip().startswith("#"):
                    break
            text += "\n" + (self.raw[j] if is_flow else self.raw[j].strip())
            j += 1
        if (is_flow or is_quoted) and not balanced(text):
            raise YamlError(f"unterminated flow collection or string starting at line {raw_idx + 1}")
        while self.i < len(self.lines) and self.lines[self.i][2] < j:
            self.i += 1
        if not (is_flow or is_quoted):
            text = _fold("\n".join(_strip_comment(line) for line in text.split("\n")))
        return text

    def _sequence(self, indent: int) -> list:
        items = []
        while self.i < len(self.lines):
            ind, content, raw_idx = self.lines[self.i]
            if ind != indent or not (content.startswith("- ") or content == "-"):
                if ind > indent:
                    raise YamlError(f"bad indentation at line {raw_idx + 1}")
                break
            item = content[1:].lstrip()
            if not item:
                self.i += 1
                items.append(self._node(self.lines[self.i][0]) if self.i < len(self.lines)
                             and self.lines[self.i][0] > indent else None)
                continue
            offset = indent + (len(content) - len(item))
            if item == "-" or item.startswith("- "):
                self.lines[self.i] = (offset, item, raw_idx)
                items.append(self._sequence(offset))
            elif _split_key(item) is not None and item[0] not in "[{":
                self.lines[self.i] = (offset, item, raw_idx)
                items.append(self._mapping(offset))
            else:
                self.i += 1
                if item[0] in "|>":
                    items.append(self._block_scalar(item, indent, raw_idx))
                else:
                    items.append(_scalar(self._continuation(item, indent, raw_idx)))
        return items

    def _block_scalar(self, header: str, indent: int, raw_idx: int) -> str:
        folded, flags = header[0] == ">", header[1:].strip()
        chomp = "".join(c for c in flags if c in "+-")
        digits = "".join(c for c in flags if c.isdigit())
        body: list[str] = []
        j = raw_idx + 1
        block_indent = indent + int(digits) if digits else None
        while j < len(self.raw):
            line = self.raw[j].replace("\t", "    ")
            if line.strip():
                ind = len(line) - len(line.lstrip())
                if ind <= indent:
                    break
                block_indent = ind if block_indent is None else block_indent
                body.append(line[block_indent:])
            else:
                body.append("")
            j += 1
        while self.i < len(self.lines) and self.lines[self.i][2] < j:
            self.i += 1
        while body and body[-1] == "" and chomp != "+":
            body.pop()
        text = " ".join(body) if folded else "\n".join(body)
        return text if chomp == "-" else text + "\n"
