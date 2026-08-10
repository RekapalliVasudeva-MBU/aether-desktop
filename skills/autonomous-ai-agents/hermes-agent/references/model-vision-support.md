# Model Vision & Image Input Support

## Symptom
User sends an image but the agent cannot see it. Error:
```
Error code: 404 - {'error': {'message': 'No endpoints found that support image input', 'code': 404}}
```

## Root Cause
The current model does not support image/vision input. Common text-only models on OpenRouter:
- `openrouter/owl-alpha` — text only, no vision

## How to Check
Run in terminal:
```bash
hermes config
```
Look at `model.default`. If it's a text-only model, image input won't work.

## Fix: Switch to a Vision-Capable Model

### Free options on OpenRouter:
```bash
# Qwen 2 VL (7B) — free, supports images
hermes config set model.default openrouter/qwen/qwen-2-vl-7b-instruct

# Gemini 2.0 Flash Lite — very cheap, supports images
hermes config set model.default openrouter/google/gemini-2.0-flash-lite-001
```

After changing, restart the gateway:
```bash
hermes gateway restart
```

## Workaround (without switching models)
If you can't switch models:
1. User describes the image in text
2. User pastes text content from screenshots
3. For web images, provide the URL — the agent can use browser_navigate to view it

## Related
- Config path (Windows): C:\Users\<user>\AppData\Local\hermes\config.yaml
- Config path (Linux/macOS): ~/.hermes/config.yaml
- Provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers
