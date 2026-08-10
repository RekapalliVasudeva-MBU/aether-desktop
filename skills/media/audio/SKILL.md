---
name: audio
description: "Audio generation and analysis: music generation from lyrics, spectrogram visualization, audio feature extraction. Use when generating music from lyrics/tags (HeartMuLa), visualizing audio spectrograms/features (songsee), or analyzing audio files. Covers: HeartMuLa (Suno-like open-source music generation), songsee (spectrograms, mel, chroma, MFCC)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audio, music, generation, spectrogram, heartmula, songsee, analysis]
---

# Audio — Generation and Analysis

## Skill Selection

| Task | Section |
|------|---------|
| Generate music from lyrics | §1 HeartMuLa |
| Visualize audio features | §2 songsee |

---

## §1 — HeartMuLa (Music Generation)

Open-source music foundation model (Apache-2.0) that generates music from lyrics + tags.

### Hardware

- Minimum: 8GB VRAM with `--lazy_load true`
- Recommended: 16GB+ VRAM

### Installation

```bash
git clone https://github.com/HeartMuLa/heartlib.git && cd heartlib
uv venv --python 3.10 .venv && . .venv/bin/activate
uv pip install -e .
uv pip install --upgrade datasets transformers  # fix dependency conflicts
```

### Required Patches (transformers 5.x)

**Patch 1 — RoPE cache** in `src/heartlib/heartmula/modeling_heartmula.py`:
Add RoPE reinitialization after `reset_caches` in `setup_caches` method.

**Patch 2 — HeartCodec loading** in `src/heartlib/pipelines/music_generation.py`:
Add `ignore_mismatched_sizes=True` to ALL `HeartCodec.from_pretrained()` calls.

### Download Models

```bash
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

### Usage

```bash
python ./examples/run_music_generation.py \
  --model_path=./ckpt --version="3B" \
  --lyrics="./assets/lyrics.txt" --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" --lazy_load true
```

**Tags** (comma-separated): `piano,happy,wedding,synthesizer,romantic`

**Lyrics** (bracketed structure):
```
[Intro]
[Verse]
Your lyrics...
[Chorus]
Chorus lyrics...
[Outro]
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max_audio_length_ms` | 240000 | Max length (240s = 4 min) |
| `--cfg_scale` | 1.5 | Classifier-free guidance |
| `--lazy_load` | false | Load/unload models on demand |

### Pitfalls

1. Do NOT use bf16 for HeartCodec — degrades quality. Use fp32.
2. Tags may be ignored (known issue #90).
3. Triton not available on macOS — Linux/CUDA only for GPU.

---

## §2 — songsee (Audio Visualization)

Generate spectrograms and multi-panel audio feature visualizations.

### Installation

```bash
go install github.com/steipete/songsee/cmd/songsee@latest
```

### Usage

```bash
songsee track.mp3                          # basic spectrogram
songsee track.mp3 -o spectrogram.png       # save to file
songsee track.mp3 --viz spectrogram,mel,chroma,mfcc  # multi-panel
songsee track.mp3 --start 12.5 --duration 8           # time slice
```

### Visualization Types

| Type | Description |
|------|-------------|
| `spectrogram` | Standard frequency spectrogram |
| `mel` | Mel-scaled spectrogram |
| `chroma` | Pitch class distribution |
| `hpss` | Harmonic/percussive separation |
| `mfcc` | Mel-frequency cepstral coefficients |
| `flux` | Spectral flux (onset detection) |

### Common Flags

| Flag | Description |
|------|-------------|
| `--viz` | Comma-separated visualization types |
| `--style` | Color palette: classic, magma, inferno, viridis, gray |
| `--start` / `--duration` | Time slice |
| `--format` | Output format: jpg or png |
