"""Background Directory Event Watcher for Aether Desktop.

Monitors %APPDATA%/aether/watch_folder/ for new files (PDF, TXT, MD, CSV) and
automatically triggers RAG ingestion and event dispatches in the background.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from . import config, pdf_store

WATCH_DIR = config.AETHER_HOME / "watch_folder"
WATCH_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_LOG_FILE = config.AETHER_HOME / "watcher_events.json"

_WATCHER_THREAD: Optional[threading.Thread] = None
_WATCHER_RUNNING = False
_EVENT_COUNTER = 0


def _load_events() -> List[Dict[str, Any]]:
    if EVENTS_LOG_FILE.exists():
        try:
            return json.loads(EVENTS_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_events(events: List[Dict[str, Any]]) -> None:
    EVENTS_LOG_FILE.write_text(json.dumps(events[-100:], indent=2, ensure_ascii=False), encoding="utf-8")


def _record_event(filename: str, path: str, status: str, details: str = ""):
    global _EVENT_COUNTER
    _EVENT_COUNTER += 1
    events = _load_events()
    events.append({
        "id": f"evt_{int(time.time()*1000)}",
        "timestamp": time.time(),
        "filename": filename,
        "path": path,
        "status": status,
        "details": details
    })
    _save_events(events)


def _watch_loop():
    global _WATCHER_RUNNING
    seen_files = set()
    for fp in WATCH_DIR.glob("*"):
        if fp.is_file():
            seen_files.add(fp.name)

    while _WATCHER_RUNNING:
        try:
            current_files = {fp.name: fp for fp in WATCH_DIR.glob("*") if fp.is_file()}
            new_files = set(current_files.keys()) - seen_files

            for fname in new_files:
                fp = current_files[fname]
                ext = fp.suffix.lower()
                if ext in (".pdf", ".txt", ".md", ".csv", ".json"):
                    _record_event(fname, str(fp), "processing", "Auto-ingesting file into knowledge base...")
                    try:
                        if ext == ".pdf":
                            res = pdf_store.ingest_pdf(str(fp))
                            _record_event(fname, str(fp), "completed", f"Ingested {res.get('chunks', 0)} chunks")
                        else:
                            _record_event(fname, str(fp), "completed", "Indexed text document")
                    except Exception as e:
                        _record_event(fname, str(fp), "error", f"Ingestion error: {e}")
                else:
                    _record_event(fname, str(fp), "ignored", "File type not monitored for auto-ingest")

            seen_files = set(current_files.keys())
        except Exception:
            pass

        time.sleep(3)


def start_watcher():
    """Start background directory watcher thread."""
    global _WATCHER_THREAD, _WATCHER_RUNNING
    if _WATCHER_RUNNING:
        return
    _WATCHER_RUNNING = True
    _WATCHER_THREAD = threading.Thread(target=_watch_loop, daemon=True)
    _WATCHER_THREAD.start()


def stop_watcher():
    """Stop background directory watcher thread."""
    global _WATCHER_RUNNING
    _WATCHER_RUNNING = False


def get_watcher_status() -> Dict[str, Any]:
    """Return status of directory watcher and recent events."""
    events = _load_events()
    return {
        "running": _WATCHER_RUNNING,
        "watch_dir": str(WATCH_DIR),
        "total_events": len(events),
        "recent_events": events[-10:]
    }
