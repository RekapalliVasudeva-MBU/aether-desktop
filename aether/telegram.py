"""Single Telegram integration for Aether.

The user requested exactly ONE Telegram connection (no other messaging
integrations). This is a minimal long-poll bot: it receives messages and runs
them through the Aether agent (normal mode by default; /rag to switch).
"""
from __future__ import annotations

import time
import os
import requests
from typing import Optional

from . import config, agent


def run_telegram() -> None:
    cfg = config.load_config()["telegram"]
    token = cfg.get("token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("[telegram] no token configured; set telegram.token in config or TELEGRAM_BOT_TOKEN env.")
        return
    base = f"https://api.telegram.org/bot{token}"
    offset = 0
    print("[telegram] bot started (long-poll). Ctrl+C to stop.")
    mode = {"default": "normal"}
    while True:
        try:
            r = requests.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40)
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg:
                    continue
                text = msg.get("text", "")
                chat_id = msg["chat"]["id"]
                if text == "/rag":
                    mode[chat_id] = "rag"
                    _send(base, chat_id, "RAG mode enabled.")
                    continue
                if text == "/normal":
                    mode[chat_id] = "normal"
                    _send(base, chat_id, "Normal mode enabled.")
                    continue
                m = mode.get(chat_id, "normal")
                rag_ctx = ""
                if m == "rag":
                    from . import rag as ragmod
                    rag_ctx = ragmod.retrieve(text)
                answer = agent.run_agent(text, mode=m, rag_context=rag_ctx)
                _send(base, chat_id, answer[:4000])
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[telegram] error: {e}")
            time.sleep(5)


def _send(base: str, chat_id: int, text: str) -> None:
    requests.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=20)
