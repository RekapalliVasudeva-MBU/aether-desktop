"""PyInstaller entry point for the frozen Aether desktop app.

Runs the FastAPI backend + pywebview window exactly like `python desktop_app.py`.
Never sets OPENROUTER_API_KEY; the app reads it from AETHER_HOME/.env or the
user pastes it in the UI. The distributed build contains ZERO credentials.
"""
from desktop_app import main

if __name__ == "__main__":
    main()
