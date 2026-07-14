"""Minimal MCP (Model Context Protocol) client for Aether.

Supports two transports:
  - stdio:  {command: "npx", args: ["-y", "@modelcontextprotocol/server-..."]}
  - http:   {url: "https://.../mcp"}  (streamable HTTP, JSON-RPC)

We implement a small JSON-RPC client that lists tools (and can call them).
This lets the user connect any MCP server in config.yaml under mcp.servers.
"""
from __future__ import annotations

import json
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
        self.proc = subprocess.Popen(
            [self.spec["command"], *self.spec.get("args", [])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )

    def _rpc_stdio(self, method: str, params: Optional[dict] = None) -> dict:
        with self._lock:
            self._id += 1
            msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    return {}
                try:
                    resp = json.loads(line)
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
        try:
            c = MCPClient(name, spec)
            c.initialize()
            out[name] = c
        except Exception as e:
            print(f"[mcp] failed to connect {name}: {e}")
    return out
