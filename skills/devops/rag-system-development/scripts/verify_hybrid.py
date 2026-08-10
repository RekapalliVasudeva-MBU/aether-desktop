"""Verify the hybrid provider pattern WITHOUT a real OpenRouter key or network.

Drop this into a RAG project that has a `main.py` exposing:
  - PROJECT_DIR, DEFAULT_OPENROUTER_MODEL
  - OpenAI (the symbol used inside generate_answer)
  - generate_answer(user_question, context, settings)
  - configure_settings()
  - SETTINGS_PATH / rag_settings.json handling

Run:  python verify_hybrid.py

It checks two things:
  1. The OpenRouter branch builds the correct OpenAI-compatible streaming
     request (model, stream=True, message roles) using a fake client.
  2. The first-run menu writes rag_settings.json, and a second run with
     configured=True returns the stored provider WITHOUT re-prompting.
"""
import sys
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main


# ---- Fake OpenAI client (OpenAI-compatible) ----
class FakeDelta:
    def __init__(self, c):
        self.content = c


class FakeChoice:
    def __init__(self, c):
        self.delta = FakeDelta(c)


class FakeChunk:
    def __init__(self, c):
        self.choices = [FakeChoice(c)]


class FakeStream:
    def __iter__(self):
        for c in ["Hello ", "from ", "OpenRouter ", "API!"]:
            yield FakeChunk(c)


class FakeCompletions:
    last = None

    def create(self, **kw):
        FakeCompletions.last = kw
        return FakeStream()


class FakeChat:
    completions = FakeCompletions()


class FakeClient:
    chat = FakeChat()


def verify_openrouter_branch():
    main.OpenAI = lambda *a, **k: FakeClient()  # patch the constructor
    settings = {
        "provider": "openrouter",
        "openrouter_model": "mistralai/mistral-7b-instruct:free",
        "openrouter_api_key": "sk-or-test-dummy",
    }
    print("=== OpenRouter branch (mocked) ===")
    main.generate_answer("What is RAG?", "RETRIEVED CONTEXT", settings)
    last = FakeCompletions.last
    assert last.get("model") == "mistralai/mistral-7b-instruct:free"
    assert last.get("stream") is True
    assert [m["role"] for m in last.get("messages", [])] == ["system", "user"]
    print("-> request shape + streaming OK\n")


def verify_setup_flow():
    SETTINGS = main.PROJECT_DIR / "rag_settings.json"
    if SETTINGS.exists():
        SETTINGS.unlink()

    print("=== First run (input: 1 <key> <enter>) ===")
    sys.stdin = io.StringIO("1\nsk-or-faketest123\n\n")
    s1 = main.configure_settings()
    assert s1["configured"] is True
    assert s1["provider"] == "openrouter"
    assert s1["openrouter_api_key"] == "sk-or-faketest123"
    assert SETTINGS.exists()
    print("-> wrote:", json.load(open(SETTINGS)))

    print("=== Second run (no input) should NOT prompt ===")
    sys.stdin = io.StringIO("")
    s2 = main.configure_settings()
    assert s2["provider"] == "openrouter"
    print("-> reused config without prompting. provider =", s2["provider"])

    print("=== User edits file to switch to ollama ===")
    s2["provider"] = "ollama"
    main.save_settings(s2)
    sys.stdin = io.StringIO("")
    s3 = main.configure_settings()
    assert s3["provider"] == "ollama"
    print("-> reads edited file. provider =", s3["provider"])


if __name__ == "__main__":
    verify_openrouter_branch()
    verify_setup_flow()
    print("\n✅ HYBRID PATTERN VERIFIED")
