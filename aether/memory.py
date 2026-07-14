"""Long-term memory for Aether.

A simple, durable JSONL store of facts (Hermes-style: memory.md as notes,
fact_store for structured recall). Here we implement a lightweight JSONL
memory with add / search / list. Keeps it dependency-free.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict

from . import config


class Memory:
    def __init__(self):
        cfg = config.load_config()
        self.path = config.AETHER_HOME / cfg["memory"]["path"]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def add(self, content: str, target: str = "memory") -> None:
        entry = {"target": target, "content": content}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def all(self) -> List[Dict]:
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        q = query.lower()
        hits = []
        for e in self.all():
            text = (e.get("content") or "").lower()
            if q in text or re.search(r"\b" + re.escape(q) + r"\b", text):
                hits.append(e)
        return hits[:limit]

    def render_for_prompt(self) -> str:
        items = [e["content"] for e in self.all() if e.get("target") == "memory"]
        if not items:
            return ""
        return "## Memory (durable user facts)\n" + "\n".join(f"- {i}" for i in items[-40:])
