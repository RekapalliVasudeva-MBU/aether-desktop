# Aether Desktop

A **self-hosted AI agent + RAG desktop app for Windows**, built with Python (FastAPI + pywebview).

It is one half of the **AetherMind** 2-in-1 suite:

| Repo | What it is |
|------|------------|
| [`project_rag`](https://github.com/<your-org>/project_rag) | The **hosted web RAG server** — chat with your PDFs in a browser, served via a public website. |
| **`aether-desktop`** (this repo) | The **desktop companion app** — the same engine packaged as a Windows `.exe` you install and run locally. |

Both share the same hybrid RAG core (Docling parsing + BM25 + reranker + RRF), but are delivered differently:
the web server runs in the cloud, the desktop app runs **entirely on your machine**.

## Features

- **Two modes**
  - *Normal* — a general AI agent with tools, skills, memory, and MCP.
  - *RAG* — the same agent grounded on **your own PDFs** (no data leaves your machine except to your chosen provider).
- **Left sidebar** (Hermes-style): chat sessions, RAG PDFs panel (add / remove / rebuild), provider settings, capability toggles, optional gateway control.
- **Capability toggles**: Skills · Tools · MCP · Memory · RAG — shape what the agent can do.
- **Your key, your machine**: the app ships **with no API key**. Paste your own OpenRouter (or other) key in the UI; it is stored only in `%APPDATA%/aether/.env`.
- **Optional gateway**: a Telegram bridge you can start/stop from the sidebar. Inert unless you configure a token.

## Download

Get `Aether-Setup.exe` from the **Downloads** section of the
[AetherMind website](https://marshy-ancient-rebuild.ngrok-free.dev/#download) (or build it yourself below).
The installer extracts to `%LOCALAPPDATA%/Aether` and adds Desktop + Start-Menu shortcuts.

## Where things live

```
%LOCALAPPDATA%/Aether/Aether.exe     # the app
%LOCALAPPDATA%/Aether/logo.ico       # shortcut icon

%APPDATA%/aether/config.yaml         # settings + capability toggles
%APPDATA%/aether/.env                # YOUR provider key (never ours)
%APPDATA%/aether/skills/             # skill library
%APPDATA%/aether/sessions/           # chat sessions
%APPDATA%/aether/rag_pdfs/           # your PDFs
%APPDATA%/aether/chroma/             # local vector store
```

Full guide: **Aether Desktop documentation** link on the website download page.

## Build from source

```bash
pip install -r requirements.txt
python -m PyInstaller --name Aether --windowed --onefile \
  --add-data "desktop_ui;desktop_ui" build_aether.py
python make_installer.py     # -> dist/Aether-Setup.exe
```

## Privacy

Aether Desktop contains **no credentials**. It contacts only the provider you configure and,
optionally, a gateway you enable. The distributed build is clean.

---

© AetherMind — a 2-in-1 project: a hosted web RAG server and a self-hosted desktop agent.
