<div align="center">

# ⚡ Aether Desktop 🤖

### *The Self-Hosted AI Operating System & Multi-Agent Desktop Companion for Windows*

[![GitHub Release](https://img.shields.io/github/v/release/RekapalliVasudeva-MBU/aether-desktop?style=for-the-badge&color=7c6cff&logo=github)](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest)
[![Windows](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest)
[![Apache Burr](https://img.shields.io/badge/Orchestrator-Apache_Burr-FF6B6B?style=for-the-badge&logo=apache)](https://github.com/DAGWorks-Inc/burr)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-27C6A1?style=for-the-badge)](LICENSE)

---

### 🌐 [**Visit Official Website (aethermind.page)**](https://aethermind.page) &nbsp;|&nbsp; 📖 [**Read Documentation**](https://aethermind.page/aether-docs) &nbsp;|&nbsp; 📦 [**Sister Web Server (`project_rag`)**](https://github.com/RekapalliVasudeva-MBU/project_rag)

</div>

---

## ⚡ Instant Download

| Platform | Download Link | Package Details |
| :--- | :--- | :--- |
| **Windows 10 / 11 Installer** | [**⬇️ Download Latest Aether-Setup (v2.0.0)**](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest) | **Standalone One-Click Setup** — Auto-creates Desktop & Start Menu shortcuts |
| **GitHub Releases Hub** | [**📦 All Releases & Versions**](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases) | Official GitHub Releases Portal |
| **AetherMind Hub** | [**🌐 aethermind.page/#download**](https://aethermind.page/#download) | Official Download Portal & Release Notes |
| **Sister RAG Server** | [**📦 project_rag Repository**](https://github.com/RekapalliVasudeva-MBU/project_rag) | Hosted Web RAG Server (Cloud Companion) |

> [!TIP]
> **Zero Configuration Setup**: Download `Aether-Setup.exe` from the [Latest Release](https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/latest) and launch! The app automatically creates **Desktop (`Aether.lnk`)** and **Start Menu** shortcuts.

---

## 🏆 Competitive Feature Comparison

Why **Aether Desktop** leads the next generation of AI Desktop applications:

| Feature Capability | ⚡ **Aether Desktop** | 🤖 Hermes Desktop | 🦅 OpenClaw | 💬 Claude Desktop |
| :--- | :---: | :---: | :---: | :---: |
| **Antigravity Precision Tools (`grep`, `view_slice`, `replace`)** | ✅ **Native Suite** | ❌ No | ❌ No | ❌ No |
| **Deep Reasoning Token Scaling (up to 65,536 tokens)** | ✅ **Uncapped Max** | ⚠️ Capped | ❌ No | ⚠️ Capped |
| **Red Square Instant Stop Button & Live 3-Dots Animation** | ✅ **Built-in** | ✅ Built-in | ❌ No | ⚠️ Basic |
| **Concurrent Multi-Tool Thread Pool Dispatch** | ✅ **Parallel 8x** | ⚠️ Sequential | ❌ No | ❌ No |
| **Apache Burr State Machine (`State ➔ Action ➔ State`)** | ✅ **Native** | ❌ No | ❌ No | ❌ No |
| **Human-in-the-Loop (HITL) Interactive Tool Approvals** | ✅ **Full GUI Cards** | ⚠️ Basic CLI | ❌ No | ❌ No |
| **State Checkpointing & Rollback Scrubber** | ✅ **Snapshot Rewind** | ❌ No | ❌ No | ❌ No |
| **Multi-Agent Swarm Orchestration** | ✅ **4 Subagent Roles** | ⚠️ Single Agent | ⚠️ Basic | ❌ No |
| **Role-Based Multi-LLM Routing** | ✅ **Per-Action Model** | ❌ No | ❌ No | ❌ No |
| **Background Directory Watcher (Auto-Ingest)** | ✅ **Automated Watcher** | ❌ No | ❌ No | ❌ No |
| **Local RAG Vector Knowledge Base (ChromaDB)** | ✅ **Native Hybrid RAG** | ❌ No | ❌ No | ❌ No |
| **TeX / LaTeX Math Formula Rendering (KaTeX)** | ✅ **Built-in** | ❌ No | ❌ No | ⚠️ Partial |
| **Model Context Protocol (MCP) GUI Manager** | ✅ **Full GUI Manager** | ⚠️ CLI only | ⚠️ Basic | ✅ Standard |
| **100% Self-Hosted & Local Privacy** | ✅ **Your Key Only** | ✅ Local | ⚠️ Hybrid | ❌ Cloud Only |

---

## 🔥 Deep Dive: What Makes Aether Desktop Powerful

### ⚡ 1. Apache Burr State-Machine Engine
Aether Desktop is built on **Apache Burr** (`State ➔ Action ➔ State`), treating the entire application as a deterministic state graph:
- **Centralized State**: Tracks goals, active subtasks, tool execution outputs, and final answers in a unified state graph.
- **Deterministic Transitions**: Structured pipeline from `Planning` ➔ `Routing` ➔ `Approval Check` ➔ `Execution` ➔ `State Update` ➔ `Synthesis`.

### 🛑 2. Human-in-the-Loop (HITL) Action Approvals
User sovereignty is non-negotiable:
- Any high-impact tool action (`exec_command`, `write_file`, `delete_file`, `mcp_add_server`) automatically **pauses** the Burr state machine.
- The UI renders an interactive approval card with **Approve**, **Modify Parameters**, or **Reject** buttons before execution resumes.

### 📸 3. State Checkpointing & Rollback Scrubber
- **State Snapshots**: Every state transition automatically saves a JSON snapshot to `%APPDATA%\aether\checkpoints\`.
- **Pause & Resume**: Pause long-running agent tasks and resume them anytime—even after restarting the desktop app.
- **Rollback Scrubber**: Rewind chat session state to any previous step if an agent took an incorrect sub-path.

### 🤖 4. Multi-Agent Swarm Orchestration
- **Coordinator Agent**: Decomposes user goals into structured subtask pipelines.
- **Specialized Subagent Workers**:
  - 🧙 `RAGSpecialist`: PDF Knowledge & Document Retrieval
  - 🔍 `WebResearcher`: External web search & deep content extraction
  - 🛠️ `ToolRunner`: System commands, local file manipulation, Python code execution
  - ✍️ `Synthesizer`: Aggregating findings into polished Markdown with LaTeX math formulas.

### 📚 5. Personal RAG & Background Directory Watcher
- **Local Knowledge Base**: Ground responses on your own PDFs using local ChromaDB vector store.
- **Background Event Watcher**: Monitors `%APPDATA%\aether\watch_folder\`. Drop any PDF, TXT, MD, or CSV file in, and Aether automatically indexes it in the background.

### 📐 6. TeX & LaTeX Math Formula Rendering
- Built-in KaTeX rendering for mathematical formulas and scientific equations (`\(...\)`, `$$...$$`) directly in the chat timeline.

### ⚙️ 7. Dynamic Multi-LLM Role Assignment
- Assign different AI models to **Planner**, **Coder**, **Researcher**, and **Synthesis** roles in the **⚡ Burr OS** dashboard tab.

---

## 📁 System Architecture & Directory Layout

```text
%LOCALAPPDATA%/Aether/
├── Aether.exe                   # Main Desktop Executable
└── desktop_ui/logo.ico          # Application Icon

%APPDATA%/aether/
├── config.yaml                  # Settings & Capability Toggles
├── .env                         # Your API Keys (Stored locally only)
├── watch_folder/                # Drop-in Folder for Auto-Ingestion
├── checkpoints/                 # Burr State Machine Snapshots
├── rag_pdfs/                    # PDF Knowledge Base
├── chroma/                      # ChromaDB Vector Store
└── sessions/                    # Chat History Store
```

---

## 🛠️ Build from Source

```bash
# 1. Clone the repository
git clone https://github.com/RekapalliVasudeva-MBU/aether-desktop.git
cd aether-desktop

# 2. Install dependencies (Python & Node)
pip install -r requirements.txt
npm install

# 3. Build & Launch Native Electron Desktop App
npm run build
npm start

# 4. Package Standalone Windows Setup Installer
npm run dist
```

---

## 🔒 Privacy & Security

Aether Desktop is **100% self-hosted and private**. It contains **no credentials or telemetry**. API keys are saved strictly on your local machine in `%APPDATA%/aether/.env` and contact only your designated model providers.

---

<div align="center">

© **AetherMind** — Multi-Agent AI Operating System & Desktop Companion.  
*Built for power users, developers, and privacy-conscious AI workflows.*

</div>
