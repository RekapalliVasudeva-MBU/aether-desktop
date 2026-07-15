"""Minimal MCP (Model Context Protocol) client for Aether.

Supports two transports:
  - stdio:  {command: "npx", args: ["-y", "@modelcontextprotocol/server-..."]}
  - http:   {url: "https://.../mcp"}  (streamable HTTP, JSON-RPC)

We implement a small JSON-RPC client that lists tools (and can call them).
This lets the user connect any MCP server in config.yaml under mcp.servers.
"""
from __future__ import annotations

import json
import select
import subprocess
import threading
from typing import Dict, List, Optional

from . import config


class MCPClient:
    def __init__(self, name: str, spec: Dict):
        self.name = name
        self.spec = spec
        self.proc = None
        self._lock = threading.Lock()
        self._id = 0
        self._buf = ""
        self.capabilities = []

    # --- stdio transport ---
    def _start_stdio(self):
        # buf-size 0 (unbuffered binary) + raw byte writes with NO flush() is
        # the only transport that works reliably on Windows here — text=True
        # with flush() raises "Errno 22 Invalid argument" on the pipe.
        self.proc = subprocess.Popen(
            [self.spec["command"], *self.spec.get("args", [])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0,
        )

    def _rpc_stdio(self, method: str, params: Optional[dict] = None) -> dict:
        with self._lock:
            self._id += 1
            msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
            payload = (json.dumps(msg) + "\n").encode("utf-8")
            self.proc.stdin.write(payload)  # unbuffered: sent immediately
            while True:
                # Hard timeout so a dead MCP server can never hang the caller.
                rlist, _, _ = select.select([self.proc.stdout], [], [], 10)
                if not rlist:
                    raise TimeoutError("MCP server did not respond within 10s")
                buf = b""
                while True:
                    ch = self.proc.stdout.read(1)
                    if not ch or ch == b"\n":
                        break
                    buf += ch
                if not buf:
                    return {}
                try:
                    resp = json.loads(buf.decode("utf-8"))
                except Exception:
                    continue
                if resp.get("id") == self._id:
                    return resp

    def initialize(self):
        if "command" in self.spec:
            self._start_stdio()
            self._rpc_stdio("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {}, "clientInfo": {"name": "aether", "version": "0.1"},
            })
            self._rpc_stdio("notifications/initialized", {})
            tools = self._rpc_stdio("tools/list", {})
            self.capabilities = tools.get("result", {}).get("tools", [])
        else:
            # http: single POST per call
            import requests
            url = self.spec["url"]
            r = requests.post(url, json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
            }, headers={"Content-Type": "application/json"}, timeout=20)
            self.capabilities = r.json().get("result", {}).get("tools", [])

    def list_tools(self) -> List[str]:
        return [t["name"] for t in self.capabilities]

    def call(self, tool_name: str, arguments: dict) -> str:
        if "command" in self.spec:
            resp = self._rpc_stdio("tools/call", {"name": tool_name, "arguments": arguments})
            return json.dumps(resp.get("result", {}))
        import requests
        r = requests.post(self.spec["url"], json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }, headers={"Content-Type": "application/json"}, timeout=30)
        return json.dumps(r.json().get("result", {}))


def connect_all() -> Dict[str, MCPClient]:
    out: Dict[str, MCPClient] = {}
    servers = config.load_config()["mcp"]["servers"]
    for name, spec in servers.items():
        if not config.item_enabled("mcp", name, True):
            continue
        try:
            c = MCPClient(name, spec)
            c.initialize()
            out[name] = c
        except Exception as e:
            print(f"[mcp] failed to connect {name}: {e}")
    return out


def list_servers() -> List[Dict[str, object]]:
    """Return [{name, spec, enabled, connected, use_case}] for configured MCP servers."""
    cfg = config.load_config()
    servers = cfg["mcp"]["servers"]
    out = []
    for name, spec in servers.items():
        enabled = config.item_enabled("mcp", name, True)
        use_case = (spec.get("description") or "").strip()
        out.append({
            "name": name,
            "spec": spec,
            "enabled": enabled,
            "connected": False,  # tested on demand via /api/mcp/test (spawns a process)
            "use_case": use_case,
        })
    return out


def test_connection(name: str) -> Dict[str, object]:
    """Best-effort live probe of one server. Spawns a real process for stdio,
    does a network round-trip for http. Returns {ok, detail}."""
    cfg = config.load_config()
    spec = cfg["mcp"]["servers"].get(name)
    if not spec:
        return {"ok": False, "detail": "no such server"}
    try:
        c = MCPClient(name, spec)
        c.initialize()
        tool_count = len(c.capabilities)
        if c.proc:
            c.proc.terminate()
        return {"ok": True, "detail": f"connected ({tool_count} tool(s))"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:300]}


def add_server(name: str, spec: Dict) -> bool:
    """Add an MCP server to config.yaml (stdio or http)."""
    if not name:
        return False
    cfg = config.load_config()
    cfg["mcp"]["servers"][name] = spec
    config.save_config(cfg)
    return True


def remove_server(name: str) -> bool:
    cfg = config.load_config()
    if name not in cfg["mcp"]["servers"]:
        return False
    del cfg["mcp"]["servers"][name]
    config.save_config(cfg)
    return True
