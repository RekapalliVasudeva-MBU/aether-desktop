# Local Model Comparison: Granite 4.1 8B vs LFM2.5 8B (June 2026)

Hardware context: RTX 5070 Laptop (8GB VRAM), 16GB RAM — max practical model size ~6-8GB.

## Granite 4.1 8B (IBM)

- **Size:** 5.3 GB (Q4_K_M)
- **Parameters:** 8B dense
- **Context:** 128K
- **License:** Apache 2.0 (fully open)
- **Languages:** EN, DE, ES, FR, JA, PT, IT, KO, AR, ZH
- **Architecture:** Dense transformer
- **Strengths:**
  - Explicitly designed for RAG (retrieval-augmented generation)
  - Structured JSON output / function calling
  - Enterprise-grade quality and safety
  - Multilingual support
  - Clean Apache 2.0 license for commercial use
- **Best for:** RAG applications, general-purpose chat, coding, multilingual tasks, production deployments
- **Ollama pull:** `ollama pull ibm/granite4.1:8b`
- **Note:** Very new (June 2026) — public benchmarks still emerging

## LFM2.5 8B-A1B (Liquid AI)

- **Size:** 5.2 GB
- **Parameters:** 8.3B total / 1.5B active (MoE — Mixture of Experts)
- **Context:** 128K
- **License:** LFM 1.0 (source-available, not OSI-approved)
- **Languages:** EN, AR, ZH, FR, DE, JA, KO, ES, PT, IT
- **Architecture:** Hybrid MoE (Liquid Foundation Model)
- **Training:** 38 trillion tokens
- **Strengths:**
  - Best-in-class tool calling (BFCLv3: 64.36, BFCLv4: 48.50)
  - Strong math reasoning (MATH500: 88.76, AIME25: 42.53)
  - Excellent instruction following (IFEval: 91.84)
  - Fast inference (MoE = only 1.5B active params per forward pass)
  - Low hallucination rate (AA Non-Hallucination: 63.47%)
  - Domain-specific agentic tasks (Tau Telecom: 88.07%)
- **Best for:** Agentic workflows, tool calling, math/reasoning, high-frequency scanning tasks
- **Ollama pull:** `ollama pull lfm2.5:8b`
- **Note:** Not ideal for heavy knowledge-intensive QA without retrieval

## Recommendation for AI/ML Engineers

| Use Case | Best Model |
|---|---|
| RAG applications | Granite 4.1 8B |
| Tool calling / Agents | LFM2.5 8B |
| General purpose | Granite 4.1 8B |
| Math / Reasoning | LFM2.5 8B |
| Fast inference (MoE speed) | LFM2.5 8B |
| Commercial / Apache 2.0 | Granite 4.1 8B |
| High-frequency background tasks (free local) | LFM2.5 8B (faster) |

**Ideal setup:** Download both (~10GB total). Use Granite 4.1 as primary RAG/general model, LFM2.5 for agentic tool-calling and math-heavy reasoning. They complement each other well.

## Qwythos 9B Abliterated (June 2026)

- **Size:** 5.6 GB (Q4_K_M)
- **Parameters:** 9B (Qwen3.5/qwen35 architecture)
- **Context:** **1M tokens (1048576)** — 4x more than competitors (typically 256K)
- **Quantization:** Q4_K_M (quality sweet spot)
- **Architecture:** Qwen3.5 hybrid state-space + transformer. GQA (16 heads, 4 KV heads), YaRN rope scaling (262K → 1M), SSM state compression layers.
- **Capabilities:** `["completion"]` only — no native tool calling or thinking at model level.
- **Abliterated:** Yes — removes refusal filtering for uncensored output.
- **Strengths:**
  - Massive 1M context window (best-in-class for local models)
  - Superior architecture vs standard transformers (hybrid attention + SSM compression)
  - Excellent for RAG, long documents, large codebases, extended conversations
  - Best quality-per-GB among 9B-class models
- **Best for:** General chat, RAG, long-context retrieval, codebase analysis, creative writing, extended conversations
- **Ollama pull:** `ollama pull richardyoung/qwythos-9b-abliterated:Q4_K_M`
- **Drawback:** Only `["completion"]` capability — tool calling and thinking require orchestration by the agent framework, not built into the model itself.

## Updated Recommendation Matrix (June 2026)

| Use Case | Best Model |
|---|---|
| RAG / long-context / codebase analysis | **qwythos-9b-abliterated** ✅ (1M context) |
| Tool calling / Agents | LFM2.5 8B |
| General purpose | **qwythos-9b-abliterated** ✅ |
| Math / Reasoning | LFM2.5 8B |
| Fast inference (MoE speed) | LFM2.5 8B |
| Commercial / Apache 2.0 | Granite 4.1 8B |
| Vision (OCR, screenshots) | MiniCPM-V |
| Heavyweight reasoning (cloud) | nemotron-3-ultra:550B |

**Verdict:** On raw capability, **qwythos-9b-abliterated** outperforms LFM2.5 and Granite4.1 in general chat, RAG, and long-context tasks. The only gaps are tool-calling (LFM2.5 wins) and vision (MiniCPM-V wins). A 9B Qwen3.5-based model with 1M context at 5.6GB is exceptionally strong for its size.

## Other Models Worth Considering (same hardware class)

| Model | Size | Best For |
|---|---|---|
| `qwen3:1.7b` | ~1.7GB | Lightweight always-on model, background scanning |
| `deepseek-coder-v2:16b-lite-base-q2_K` | ~6GB | Coding tasks |
| `granite4:7b-a1b-h` | ~4GB | Previous gen Granite, still solid all-rounder |
| `richardyoung/qwythos-9b-abliterated:Q4_K_M` | ~5.6GB | Best all-rounder for 9B class (1M context, Qwen3.5 arch) |
| `minicpm-v:latest` | ~6.1GB | **Only local vision model** — OCR, screenshots, document parsing |

## MiniCPM-V 4.5 — Local Vision Model (June 2026)

- **Size:** 6.1GB (quantized GGUF)
- **Parameters:** 8B
- **Context:** 40K
- **Capabilities:** Vision-language model (VLM) — image input, text output (NO image generation)
- **Strengths:** Best-in-class OCR, chart understanding, document parsing, UI analysis, multi-image reasoning
- **Benchmark:** Beats GPT-4o on OCR/docvqa tasks at 1/100th the cost
- **Install:** `ollama pull minicpm-v:latest`
- **Use case for AI/ML engineers:** Screenshot analysis, architecture diagram → code, resume/job-description matching, research paper figure indexing
- **Limitation on 8GB VRAM:** Only ~2GB left for context after model loads — fine for single-image analysis, tight for multi-image conversations
- **NOT an image generator** — for image generation use Stable Diffusion/Flux via ComfyUI

## VRAM Budget Check — Always Verify Before Installing

Before recommending or installing any local model, always verify it fits the user's hardware:

```powershell
# Check current GPU free memory
nvidia-smi --query-gpu=name,memory.used,memory.total,memory.free --format=csv,noheader
```

**Rule:** Model size + 1.5-2GB (context window overhead) must fit within free VRAM. On 8GB RTX 5070 with ~7.6GB free, max practical model size is ~6GB. Larger models will cause OOM or extreme slowdown from CPU offload.

**For vision models specifically:** Images are tokenized into the context window, not stored in VRAM separately. A 6.1GB vision model on 8GB VRAM leaves only ~1.5GB for context — enough for 1-2 images + short conversation, but not for long multi-turn chats with many images. Warn the user about this limitation.
