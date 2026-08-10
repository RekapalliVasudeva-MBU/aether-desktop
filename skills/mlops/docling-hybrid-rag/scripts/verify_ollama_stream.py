"""Diagnose Ollama streaming + abliterated-model refusal.

Run: python verify_ollama_stream.py
Helps distinguish THREE failure modes that all look like "empty answer":
  1. asyncio.to_thread wrapping -> silent empty tokens (real bug)
  2. dict vs attr access on modern ollama ChatResponse
  3. abliterated model refusing a directive-style test prompt
"""
import asyncio, ollama

MODEL = "richardyoung/qwythos-9b-abliterated:Q4_K_M"


def test_knowledge():
    print("\n[TEST 1] real knowledge question (should produce text):")
    out = ""
    for ch in ollama.chat(model=MODEL,
                          messages=[{"role": "user",
                                     "content": "What is retrieval augmented generation?"}],
                          stream=True):
        out += ch["message"]["content"]
    print("  len:", len(out), "| head:", repr(out[:80]))


def test_directive():
    print("\n[TEST 2] directive test prompt 'Reply with exactly: HELLO':")
    out = ""
    for ch in ollama.chat(model=MODEL,
                          messages=[{"role": "user",
                                     "content": "Reply with exactly: HELLO"}],
                          stream=True):
        out += ch["message"]["content"]
    print("  output:", repr(out[:80]))
    print("  NOTE: abliterated models often refuse with 'I cannot complete this task.'"
          "  That is NOT a streaming bug.")


def test_to_thread():
    print("\n[TEST 3] asyncio.to_thread wrapping (should be EMPTY -> proves the bug):")
    async def go():
        s = await asyncio.to_thread(ollama.chat, MODEL,
                                    [{"role": "user", "content": "hi"}], None, True)
        n, got = 0, ""
        for ch in s:
            n += 1
            got += ch["message"]["content"]
            if n > 6:
                break
        return got
    print("  to_thread got:", repr(asyncio.run(go())[:60]),
          "(empty => confirms: never wrap ollama.chat stream in to_thread)")


if __name__ == "__main__":
    test_knowledge()
    test_directive()
    test_to_thread()
