#!/usr/bin/env python3
"""Live probe for a local RAG chat endpoint.

Asserts three answer-quality invariants after any prompt/retrieval change:
  1. No chunk metadata leaks into the answer ("Chunk" substring).
  2. Model does not narrate its reasoning ("Looking at the CONTEXT" etc.).
  3. An off-topic question returns the grounded fallback line.

Usage:
    python verify_rag.py http://127.0.0.1:8000
"""
import json
import sys
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
NARRATION = ("looking at the context", "i need to find", "based on the context,")
FALLBACK = "don't have information about that in my knowledge base"
OFFTOPIC = "tell me about banana cultivation in south america"


def ask(q: str) -> str:
    req = urllib.request.Request(
        f"{BASE}/api/chat",
        data=json.dumps({"question": q}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        ans = []
        for line in r.read().decode().split("\n\n"):
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:].strip())
                except Exception:
                    continue
                if "token" in d:
                    ans.append(d["token"])
                if d.get("done"):
                    break
    return "".join(ans).strip()


def main():
    fails = []
    for q in ("what is rag", "explain rag"):
        a = ask(q)
        print(f"\n=== Q: {q} ===\n{a[:400]}")
        if "Chunk" in a:
            fails.append(f"[{q}] chunk metadata leaked into answer")
        if any(n in a.lower() for n in NARRATION):
            fails.append(f"[{q}] model narrated reasoning")
        if len(a) < 80:
            fails.append(f"[{q}] answer too thin (<80 chars): {a!r}")

    off = ask(OFFTOPIC)
    print(f"\n=== Q: {OFFTOPIC} ===\n{off[:200]}")
    if FALLBACK.lower() not in off.lower():
        fails.append("[off-topic] did NOT return grounded fallback line")

    print("\n" + ("ALL CHECKS PASSED" if not fails else "FAILURES:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
