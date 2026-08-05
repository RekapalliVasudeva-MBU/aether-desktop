# Aether Desktop ⚡🤖

[![GitHub Release](https://img.shields.io/github/v/release/RekapalliVasudeva-MBU/aether-desktop?style=for-the-badge&color=7c6cff)](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest)
[![Windows](https://img.shields.io/badge/OS-Windows-blue?style=for-the-badge&logo=windows)](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

An **AI Operating System & Multi-Agent Desktop Companion for Windows**, powered by **Apache Burr** (`State ➔ Action ➔ State`), local ChromaDB RAG, and multi-model routing.

---

## ⚡ Direct Download & Links

| Link | Description |
| :--- | :--- |
| **⬇️ [Download Aether-Setup.exe (GitHub Releases)](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/download/v1.0.0/Aether-Setup.exe)** | **Fast Direct Download** — Windows setup installer |
| **🌐 [AetherMind Website](https://aethermind.page/#download)** | Official Download Page |
| **📖 [AetherMind Documentation](https://aethermind.page/aether-docs)** | Complete User & Developer Docs |
| **📦 [`project_rag` Web Server Repo](https://github.com/RekapalliVasudeva-MBU/project_rag)** | Sister repository: Hosted Web RAG Server |

> [!TIP]
> **Automatic Shortcuts**: The installer automatically creates **Desktop** (`Aether.lnk`) and **Start Menu** shortcuts on launch.

---

## 🔥 Key Features

### ⚡ 1. Apache Burr State-Machine Engine
- **State-Driven Application Graph**: Built on **Apache Burr** (`State ➔ Action ➔ State`) for explicit, deterministic orchestration.
- **Human-in-the-Loop (HITL) Approvals**: Pauses state execution before running sensitive tools (`exec_command`, `write_file`, `delete_file`), allowing you to **Approve**, **Modify Parameters**, or **Reject**.
- **State Checkpointing & Rollback**: Saves state snapshots to disk so you can pause/resume tasks across app restarts and rollback session history to any previous checkpoint step.

### 🤖 2. Multi-Agent Swarm Mode
- **Coordinator Agent**: Automatically breaks down complex goals into subtask pipelines.
- **Specialized Workers**:
  - `RAGSpecialist`: PDF Knowledge & Document Retrieval
  - `WebResearcher`: External web search & scraping
  - `ToolRunner`: System commands, local file manipulation, Python execution
  - `Synthesizer`: Aggregating findings into polished Markdown output with LaTeX math formulas.

### 📚 3. Personal RAG Vector Store & Background Watcher
- **Local Knowledge Base**: Ground responses on your own PDFs using local ChromaDB vector store.
- **Background Event Watcher**: Monitors `%APPDATA%\aether\watch_folder\` and automatically ingests new files in the background without interrupting your chat.

### 📐 4. TeX & LaTeX Math Formula Rendering
- Built-in KaTeX rendering for mathematical formulas and scientific equations (`\(...\)`, `$$...$$`) directly in the chat timeline.

### ⚙️ 5. Dynamic Multi-LLM Role Routing
- Map custom AI models per action role (**Planner**, **Coder**, **Researcher**, **Synthesizer**) in the **⚡ Burr OS** dashboard.

---

## 📁 Where Things Live

```
%LOCALAPPDATA%/Aether/Aether.exe     # Main Executable
%LOCALAPPDATA%/Aether/logo.ico       # Desktop Icon

%APPDATA%/aether/config.yaml         # App Config & Capabilities
%APPDATA%/aether/.env                # API Keys (Stored locally only)
%APPDATA%/aether/watch_folder/       # Drop-in folder for Auto-Ingest
%APPDATA%/aether/checkpoints/        # Burr State Machine Snapshots
%APPDATA%/aether/rag_pdfs/           # PDF Document Store
%APPDATA%/aether/chroma/             # Vector Database
```

---

## 🛠️ Build from Source

```bash
# 1. Clone repository
git clone https://github.com/RekapalliVasudeva-MBU/aether-desktop.git
cd aether-desktop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run development desktop app
python desktop_app.py

# 4. Build Windows distribution & setup installer
python make_installer.py
```

---

## 🔒 Privacy & Security

Aether Desktop is **100% self-hosted and private**. It ships with **no hardcoded credentials**. API keys are saved locally in `%APPDATA%/aether/.env` and contact only your designated model providers.

---

© **AetherMind** — Multi-Agent AI Operating System & Desktop Companion.
