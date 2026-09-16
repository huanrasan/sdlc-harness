"""Model Context Protocol server (stdio, JSON-RPC 2.0) exposing read-mostly harness tools to any MCP client.

Deliberately excluded: approving artifacts, editing receipts or deviations, and changing policy. Those stay human
actions. The only write tool is `memory_add`, whose output is reviewed in a pull request like any other file.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

from . import changes, memory, reports
from .core import VERSION, load_config, paths

PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {"name": "memory_search",
     "description": "Search project and organization memory (decisions, lessons, conventions, pitfalls) before "
                    "starting work. Organization entries take precedence.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string"}, "type": {"type": "string", "enum": memory.TYPES},
         "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["query"]}},
    {"name": "memory_add",
     "description": "Record a durable lesson, decision, convention or pitfall. Never include secrets or personal data.",
     "inputSchema": {"type": "object", "properties": {
         "type": {"type": "string", "enum": memory.TYPES}, "title": {"type": "string"},
         "tags": {"type": "array", "items": {"type": "string"}}, "body": {"type": "string"},
         "source": {"type": "string", "description": "change id, PR or incident reference"}},
         "required": ["type", "title", "body"]}},
    {"name": "change_status",
     "description": "List change records with phase, or show gate results for one change.",
     "inputSchema": {"type": "object", "properties": {"change": {"type": "string"}}}},
    {"name": "check",
     "description": "Run harness gates (optionally for one change, or with a base ref for history sensors).",
     "inputSchema": {"type": "object", "properties": {"change": {"type": "string"}, "base": {"type": "string"}}}},
    {"name": "trace",
     "description": "Traceability report for a change: criteria, tests, verification, threats, approvals, commits.",
     "inputSchema": {"type": "object", "properties": {"change": {"type": "string"}}, "required": ["change"]}},
]


def _call(root: Path, name: str, args: dict) -> tuple[str, bool]:
    from .cli import run_check  # local import: cli imports this module

    out = io.StringIO()
    is_error = False
    with contextlib.redirect_stdout(out):
        try:
            if name == "memory_search":
                for e in memory.search(root, args["query"], args.get("type"), limit=int(args.get("limit", 5))):
                    snippet = " ".join(e["body"].split())[:240]
                    print(f"[{e['origin']}] {e.get('id')} ({e.get('type')}) {e.get('title')}\n  "
                          f"{e['path'].relative_to(root)}\n  {snippet}\n")
            elif name == "memory_add":
                path = memory.add(root, args["type"], args["title"], args.get("tags", []), args["body"],
                                  args.get("source", ""))
                print(f"created {path.relative_to(root)} (commit it for review)")
            elif name == "change_status":
                cfg = load_config(root)
                if args.get("change"):
                    is_error = run_check(root, args["change"]).print() != 0
                else:
                    base = root / paths(cfg)["changes"]
                    for d in sorted(p for p in base.iterdir() if (p / "change.toml").exists()) if base.is_dir() else []:
                        meta = changes.load_toml(d / "change.toml")
                        print(f"{meta.get('id')}: {meta.get('type')} risk={meta.get('risk')} phase={meta.get('phase')}")
            elif name == "check":
                is_error = run_check(root, args.get("change"), args.get("base")).print() != 0
            elif name == "trace":
                cfg = load_config(root)
                data = reports.trace(root, cfg, changes.change_dir(root, cfg, args["change"]))
                print(reports.render("trace", data, "md"))
            else:
                return f"unknown tool: {name}", True
        except SystemExit as exc:
            is_error = bool(exc.code)
        except (KeyError, ValueError) as exc:
            print(f"invalid arguments: {exc}")
            is_error = True
    return out.getvalue(), is_error


def serve(root: Path, stdin=None, stdout=None) -> int:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    for line in stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _send(stdout, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:
            continue  # notification (e.g. notifications/initialized)
        if method == "initialize":
            requested = (msg.get("params") or {}).get("protocolVersion", PROTOCOL_VERSION)
            result = {"protocolVersion": requested or PROTOCOL_VERSION, "capabilities": {"tools": {}},
                      "serverInfo": {"name": "sdlc-harness", "version": VERSION},
                      "instructions": "SDLC harness tools. Search memory before starting; run check before claiming "
                                      "done. Approvals are human-only and not available here."}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = msg.get("params") or {}
            text, is_error = _call(root, params.get("name", ""), params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": text}], "isError": is_error}
        else:
            _send(stdout, {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"method not found: {method}"}})
            continue
        _send(stdout, {"jsonrpc": "2.0", "id": msg_id, "result": result})
    return 0


def _send(stdout, payload: dict) -> None:
    stdout.write(json.dumps(payload) + "\n")
    stdout.flush()


CLIENT_CONFIG = {
    "claude-code": ('.mcp.json', {"mcpServers": {"sdlc": {"command": "python3", "args": [".harness/sdlc.pyz", "mcp"]}}}),
    "cursor": ('.cursor/mcp.json', {"mcpServers": {"sdlc": {"command": "python3", "args": [".harness/sdlc.pyz", "mcp"]}}}),
    "vscode": ('.vscode/mcp.json', {"servers": {"sdlc": {"type": "stdio", "command": "python3",
                                                         "args": [".harness/sdlc.pyz", "mcp"]}}}),
    "gemini-cli": ('.gemini/settings.json', {"mcpServers": {"sdlc": {"command": "python3",
                                                                    "args": [".harness/sdlc.pyz", "mcp"]}}}),
    "codex": ('.codex/config.toml', '[mcp_servers.sdlc]\ncommand = "python3"\nargs = [".harness/sdlc.pyz", "mcp"]\n'),
}


def print_config(client: str) -> int:
    path, config = CLIENT_CONFIG[client]
    body = config if isinstance(config, str) else json.dumps(config, indent=2) + "\n"
    print(f"# {path} (merge with existing settings)\n{body}")
    return 0
