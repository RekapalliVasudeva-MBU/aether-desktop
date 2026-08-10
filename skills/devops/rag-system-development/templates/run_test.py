"""Self-terminating RAG verification harness.
Run as `python run_test.py` — builds the DB over ALL pdfs in SOURCE, prints
collection.count(), runs one sample question, then EXITS (so the run finishes
and can notify). Copy into the project dir and adjust SOURCE / the question.

Do NOT run `main.py` interactively to verify — it blocks on input(). Use this.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main as rag

SOURCE = r"C:\Users\valte\project_rag\rag_pdfs"   # <- point at the real pdf folder
QUESTION = "hi can u tell me about the claude leaked files"  # <- a question that should hit a specific pdf

if __name__ == "__main__":
    print("=== BUILDING RAG DB (all pdfs) ===")
    chunks, collection = rag.process_rag_pipeline(SOURCE)
    if collection is None:
        print("FATAL: collection is None, nothing stored")
        sys.exit(1)
    print(f"\n=== DB CONTAINS {collection.count()} CHUNKS ===")
    print(f"=== ASKING: {QUESTION} ===")
    rag.ask_rag_system(QUESTION, collection)
    print("\n=== DONE ===")
