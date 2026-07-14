"""Assemble the self-contained cloud deploy bundle.

Copies the premium UI (web_ui/) and the built RAG vector DB (rag_vector_db/)
next to cloud_server.py so the deployed app needs no laptop and no GPU.

Run:  python deploy/build_deploy.py
Result: deploy/ contains everything to upload to Render / HF Spaces / any
container host.
"""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # .../aether
DEPLOY = ROOT / "deploy"
UI_SRC = ROOT.parent / "project_rag" / "web_ui"
DB_SRC = ROOT.parent / "project_rag_hybrid" / "rag_vector_db"


def copy_tree(src: Path, dst: Path):
    if not src.exists():
        print(f"[skip] missing {src}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"[ok] {src.name} -> {dst.relative_to(ROOT)}")


def main():
    copy_tree(UI_SRC, DEPLOY / "web_ui")
    copy_tree(DB_SRC, DEPLOY / "rag_vector_db")
    # cloud_server.py already lives in deploy/; ensure it's there.
    print("\nDeploy bundle ready at:", DEPLOY)
    print("Upload the contents of deploy/ to Render / HF Spaces.")


if __name__ == "__main__":
    main()
