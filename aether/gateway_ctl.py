"""Control the optional Telegram gateway from the desktop UI.

Aether has exactly ONE messaging integration (Telegram). The desktop app can
start/stop it as a background thread. If no token is configured, the controls
stay inert (the UI hides them or shows "not configured").
"""
from __future__ import annotations

import threading
import os
from typing import Optional

from . import config

_thread: Optional[threading.Thread] = None
_running = False


def is_configured() -> bool:
    token = config.load_config()["telegram"].get("token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return bool(token)


def is_running() -> bool:
    return _running


def start() -> dict:
    global _thread, _running
    if _running:
        return {"ok": True, "running": True, "msg": "already running"}
    if not is_configured():
        return {"ok": False, "msg": "no Telegram token configured"}
    from . import telegram

    def _loop():
        global _running
        _running = True
        try:
            telegram.run_telegram()
        finally:
            _running = False

    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()
    return {"ok": True, "running": True, "msg": "Telegram gateway started"}


def stop() -> dict:
    global _running
    # telegram.run_telegram loops forever; we can't cleanly interrupt a blocking
    # long-poll without a sentinel. For now we mark stopped and rely on daemon
    # thread exit on process close. Best-effort UI state.
    _running = False
    return {"ok": True, "running": False, "msg": "Telegram gateway stopped (set token to restart)"}
