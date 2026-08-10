# Verified Free Models Reference (2026-07-25)

## OpenRouter Free Models (live from API)

Query used:
```bash
curl -s "https://openrouter.ai/api/v1/models" | python -c "
import json, sys
data = json.load(sys.stdin)
for m in data['data']:
    if ':free' in m['id'] or m.get('pricing', {}).get('prompt', '0') == '0':
        print(f'{m[\"id\"]} - {m.get(\"name\", \"\")}')
"
```

## Text Generation Models (verified working)

| Model ID | Name | Notes |
|----------|------|-------|
| `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA: Nemotron 3 Ultra | **Used in this session** — 550B params, reasoning capable, tested ✅ |
| `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA: Nemotron 3 Super | 120B params |
| `nvidia/nemotron-3-nano-30b-a3b:free` | NVIDIA: Nemotron 3 Nano 30B A3B | Smaller, faster |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA: Nemotron 3 Nano Omni | Multimodal? |
| `nvidia/nemotron-nano-12b-v2-vl:free` | NVIDIA: Nemotron Nano 12B V2 VL | **Verified free vision model** — image+video input |
| `nvidia/nemotron-nano-9b-v2:free` | NVIDIA: Nemotron Nano 9B V2 | 9B params |
| `nvidia/nemotron-3.5-content-safety:free` | NVIDIA: Nemotron 3.5 Content Safety | Safety classifier |
| `openrouter/free` | Free Models Router | Auto-selects a free model |
| `openai/gpt-oss-20b:free` | OpenAI: gpt-oss-20b | Open source GPT |
| `google/gemma-4-26b-a4b-it:free` | Google: Gemma 4 26B A4B | Gemma family |
| `google/gemma-4-31b-it:free` | Google: Gemma 4 31B | Larger Gemma |
| `cohere/north-mini-code:free` | Cohere: North Mini Code | Code-focused |
| `poolside/laguna-s-2.1:free` | Poolside: Laguna S 2.1 | Code-focused |
| `poolside/laguna-m.1:free` | Poolside: Laguna M.1 | Code-focused |
| `poolside/laguna-xs-2.1:free` | Poolside: Laguna XS 2.1 | Code-focused |
| `inclusionai/ling-3.0-flash:free` | InclusionAI: Ling 3.0 Flash | Chinese-optimized |

## Vision Models (verified free + image input)

| Model ID | Name | Notes |
|----------|------|-------|
| `nvidia/nemotron-nano-12b-v2-vl:free` | NVIDIA: Nemotron Nano 12B V2 VL | **Recommended** — text+image+video, $0, verified via API |

## Models to AVOID (dead/paid/removed)

| Model ID | Reason |
|----------|--------|
| `openrouter/owl-alpha` | **Removed from OpenRouter** — was rerouted to paid gemini, caused $0.0002 charge |
| `tencent/hunyuan-a13b-instruct:free` | Returns 404 — "model unavailable for free, paid version available" |
| `google/gemini-3-flash-preview` | Paid model (no `:free` suffix) |
| `google/gemini-2.5-flash-preview-tts` | Paid TTS model — removed from config (was dormant under `tts.provider: edge`) |
| `gpt-4o-mini-tts` | Paid TTS model — dormant under `tts.provider: edge` |
| `voxtral-mini-tts-2603` | Paid TTS model — dormant under `tts.provider: edge` |

## Usage in server_config.json

```json
{
  "openrouter_model": "nvidia/nemotron-3-ultra-550b-a55b:free"
}
```

## Usage in hermes config (vision)

```bash
hermes config set auxiliary.vision.model nvidia/nemotron-nano-12b-v2-vl:free
```

## Verification Checklist (run after any model change)

- [ ] Model ID ends with `:free` OR pricing.prompt == "0" via API
- [ ] For vision: architecture.input_modalities includes "image"
- [ ] Test with a simple prompt: `curl -X POST ... -d '{"model":"...", "messages":[...]}'`
- [ ] No charge appears on OpenRouter dashboard within 5 minutes