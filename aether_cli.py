#!/usr/bin/env python
"""Aether CLI.

Commands:
  aether chat                 interactive chat (Normal mode)
  aether chat --rag          interactive chat (RAG / knowledge-base mode)
  aether chat "question"     one-shot answer
  aether doctor              diagnose install/config issues
  aether doctor --fix        diagnose + attempt auto-fixes
  aether skills              list skills
  aether skills copy         copy your Hermes skills into Aether
  aether telegram            run the Telegram bot (needs token)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# make the package importable when run as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aether import config, agent, rag, skills, provider, memory, mcp  # noqa: E402


def cmd_chat(args):
    config.ensure_persona_files()
    mode = "rag" if args.rag else "normal"
    if args.message:
        rag_ctx = rag.retrieve(args.message) if mode == "rag" else ""
        answer = agent.run_agent(args.message, mode=mode, rag_context=rag_ctx)
        print(answer)
        return
    print(f"Aether ({mode} mode). Type 'exit' to quit.\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit"):
            break
        if not q:
            continue
        rag_ctx = rag.retrieve(q) if mode == "rag" else ""
        try:
            answer = agent.run_agent(q, mode=mode, rag_context=rag_ctx)
        except Exception as e:
            print(f"[error] {e}")
            continue
        print("\naether>", answer, "\n")


def cmd_skills(args):
    if args.sub == "copy":
        n = skills.copy_user_skills()
        print(f"Copied {n} skills from Hermes into Aether.")
        return
    if args.sub == "create":
        if not args.name:
            print("Usage: aether skills create <name> --content '...'")
            return
        path = skills.create_skill(args.name, args.content or "# SKILL.md\n")
        print(f"Created skill at {path}")
        return
    found = skills.discover()
    if not found:
        print("No skills found. Run `aether skills copy` to import your Hermes skills.")
        return
    for name in sorted(found):
        print(f" - {name}")


def cmd_telegram(args):
    from aether import telegram
    telegram.run_telegram()


def cmd_doctor(args):
    issues = []
    fixes = []

    # 1) OpenRouter key
    key = config.get_api_key()
    if not key:
        issues.append("OpenRouter API key not found (OPENROUTER_API_KEY env or AETHER_HOME/.env).")
        if args.fix:
            p = input("Paste your OWN OpenRouter API key (or empty to skip): ").strip()
            if p:
                # SECURITY: write to Aether's OWN .env, never the user's personal Hermes .env
                own_env = config.AETHER_HOME / ".env"
                config.AETHER_HOME.mkdir(parents=True, exist_ok=True)
                lines = []
                if own_env.exists():
                    lines = [l for l in own_env.read_text(encoding="utf-8").splitlines()
                             if not l.startswith("OPENROUTER_API_KEY=")]
                lines.append(f"OPENROUTER_API_KEY={p}")
                own_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
                fixes.append("Wrote OPENROUTER_API_KEY into Aether's own .env (AETHER_HOME/.env).")
    else:
        issues.append(f"OpenRouter key present ({key[:8]}...). OK")

    # 2) python deps
    needed = [("openai", "openai"), ("yaml", "pyyaml"), ("chromadb", "chromadb"), ("requests", "requests")]
    missing = []
    for mod, pkg in needed:
        try:
            __import__(mod)
        except Exception:
            missing.append(pkg)
    if missing:
        issues.append(f"Missing Python packages: {', '.join(missing)}")
        if args.fix:
            print(f"Installing: {', '.join(missing)} ...")
            os.system(f"pip install {' '.join(missing)}")
            fixes.append(f"Ran pip install for {', '.join(missing)}.")
    else:
        issues.append("Core Python packages present. OK")

    # 3) RAG DB reachable
    try:
        c = rag.get_collection()
        n = c.count()
        issues.append(f"RAG collection reachable ({n} chunks). OK")
    except Exception as e:
        issues.append(f"RAG collection not reachable: {e}")
        if args.fix:
            issues.append("  -> Run the project_rag_hybrid pipeline to build rag_vector_db first.")

    # 4) persona files
    config.ensure_persona_files()
    issues.append("SOUL.md / USER.md present. OK")

    print("\n=== Aether Doctor ===")
    for i in issues:
        print(" -", i)
    if fixes:
        print("\nFixes applied:")
        for f in fixes:
            print(" *", f)
    if not issues:
        print("All good.")


def main():
    ap = argparse.ArgumentParser(prog="aether", description="Aether AI agent + RAG assistant")
    sub = ap.add_subparsers(dest="cmd")

    p_chat = sub.add_parser("chat", help="chat with Aether")
    p_chat.add_argument("--rag", action="store_true", help="use RAG/knowledge-base mode")
    p_chat.add_argument("message", nargs="?", help="one-shot question")
    p_chat.set_defaults(func=cmd_chat)

    p_sk = sub.add_parser("skills", help="manage skills")
    p_sk.add_argument("sub", nargs="?", default="list")
    p_sk.add_argument("name", nargs="?", default=None, help="skill name (for create)")
    p_sk.add_argument("--content", default=None, help="skill SKILL.md content (for create)")
    p_sk.set_defaults(func=cmd_skills)

    p_tg = sub.add_parser("telegram", help="run Telegram bot")
    p_tg.set_defaults(func=cmd_telegram)

    p_doc = sub.add_parser("doctor", help="diagnose / fix install")
    p_doc.add_argument("--fix", action="store_true", help="attempt auto-fixes")
    p_doc.set_defaults(func=cmd_doctor)

    args = ap.parse_args()
    if not getattr(args, "cmd", None):
        ap.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
