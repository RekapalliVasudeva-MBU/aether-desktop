# Ollama Registry Network Troubleshooting

## Symptoms
- `ollama pull` starts but stays at 0-10% for 30+ minutes
- Speed reported as < 500 KB/s for multi-GB models
- Download appears "stuck" — same % for many minutes

## Root Cause
`registry.ollama.ai` uses Cloudflare R2. Some ISPs/regions throttle or have poor peering to Cloudflare, resulting in 100-500 KB/s speeds instead of the expected 10-50 MB/s.

## Diagnosis Steps

### 1. Check if it's actually progressing
Watch the output for 60 seconds. If the byte counter doesn't change at all → connection dropped. If it creeps forward slowly → throttled.

### 2. Test raw download speed
```bash
curl -sL -o /dev/null -w "speed: %{speed_download} bytes/s, time: %{time_total}s\n" \
  --max-time 15 "https://registry.ollama.ai/v2/library/<model>/blobs/<sha>"
```
- > 5 MB/s → normal, just a large model
- 500 KB/s - 5 MB/s → mildly throttled, will take 15-30 min for 4GB
- < 500 KB/s → severely throttled, 4GB+ models take 3+ hours

### 3. Check VRAM before pulling
```powershell
nvidia-smi --query-gpu=name,memory.used,memory.total,memory.free --format=csv,noheader
```
Model needs: `model_size + 2GB context ≤ free_VRAM`

## Workarounds

| Approach | Speed | Notes |
|----------|-------|-------|
| Let it run overnight | Same | Set and forget, works if connection is stable |
| VPN (Mullvad, Proton) | Often 5-10x faster | Routes through different peering |
| HuggingFace GGUF mirror | Varies | Some repos on HF, but many require auth (401) |
| Cloud API (OpenRouter) | Instant | No download, costs money but works now |

## Progress Reporting Best Practice
When monitoring a long download:
- Report every 5 minutes, not every few seconds
- Use consistent numbers: check % at T=0 and T=5min, compute rate
- Don't give conflicting "remaining time" estimates — use the actual rate
- If stuck > 10 min at same %, tell the user immediately rather than staying silent

## Example: MiniCPM-V 4.5 Download
- Model: 4.4GB (registry.ollama.ai)
- Observed speed: ~400 KB/s
- Estimated time: 3 hours
- User's GPU: RTX 5070 8GB, 7.6GB free → model fits (6.1GB leaves ~1.5GB context)
- Decision: Too slow for interactive session, suggest overnight or alternative
