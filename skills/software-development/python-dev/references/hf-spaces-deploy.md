# HuggingFace Spaces Deployment — Quick Reference

## Why Spaces (not Render) for ML Models

Render free tier = 512MB RAM. PyTorch + Transformers + model always OOMs.
HuggingFace Spaces = 16GB RAM, free, permanent URL, ML-optimized.

## Deployment Steps

1. **Create Space:** https://huggingface.co/new-space
   - SDK: Gradio
   - Hardware: CPU basic (free)
   - Visibility: Public

2. **Upload model to HuggingFace Hub first:**
   - Go to https://huggingface.co/new
   - Create model repo
   - Upload files from local `saved_model/` folder via web or API

3. **Create `app.py` in Space** (see template in SKILL.md)

4. **Create `requirements.txt`:**
   ```
   transformers
   torch
   gradio
   ```

5. **Space auto-deploys** -> live at `https://username-space-name.hf.space`

## Gradio vs FastAPI

For ML demo apps on Spaces, **use Gradio** (not FastAPI):
- Gradio is simpler, built-in UI, less code
- FastAPI requires separate HTML template, more memory
- Gradio is the standard for ML demos on HuggingFace

## Resume Link Format

```
AI Text Summarizer | https://valtarevasu-text-summarizer.hf.space
```

## Common Issues

| Issue | Fix |
|-------|-----|
| Space won't start | Check `requirements.txt` has all deps |
| Model not found | Verify model repo is public |
| Slow first load | Normal -- model downloads on first request |
| Build fails | Check Python version compatibility |
