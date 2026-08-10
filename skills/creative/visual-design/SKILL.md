---
name: visual-design
description: "Visual design and creative coding: ASCII art, animations, diagrams, and generative visuals. Use when creating ASCII art, Excalidraw diagrams, architecture diagrams (SVG/HTML), p5js generative art, manim math animations, infographics, or pretext text-layout demos. For image generation with Stable Diffusion/Flux, use the comfyui skill."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [visual, design, ascii, diagram, generative, animation, creative]
---

# Visual Design & Creative Coding

## Skill Selection

| Task | Tool | Section |
|------|------|---------|
| ASCII art banners | pyfiglet, cowsay, boxes | §1 ASCII Art |
| ASCII video (video→ASCII MP4) | Python + ffmpeg | §2 ASCII Video |
| Hand-drawn diagrams (JSON) | Excalidraw format | §3 Excalidraw |
| Architecture diagrams (SVG/HTML) | Dark-themed SVG | §4 Architecture Diagrams |
| Generative art (browser) | p5.js | §5 p5.js |
| Math animations | Manim CE | §6 Manim |
| Infographics (image generation) | baoyu-infographic | §7 Infographics |
| Text layout demos | @chenglou/pretext | §8 Pretext |
| Stable Diffusion / Flux | ComfyUI | §9 ComfyUI |

---

## §1 — ASCII Art

Multiple tools for different ASCII art needs.

### Text Banners (pyfiglet)

```bash
pip install pyfiglet
python3 -m pyfiglet "TEXT" -f slant
python3 -m pyfiglet --list_fonts
```

Recommended fonts: `slant` (clean), `doom` (bold), `big` (banners), `small` (compact).

### Cowsay

```bash
cowsay "Hello World"
cowsay -f tux "Linux rules"
cowthink "Hmm..."
```

### Boxes

```bash
echo "Hello" | boxes -d stone
```

### Image to ASCII

```bash
ascii-image-converter image.png -C    # color
jp2a --width=80 image.jpg            # lightweight
```

### Search Pre-Made Art

```bash
curl -s 'https://ascii.co.uk/art/cat' | python3 -c "
import re, html
# Extract <pre> blocks
"
```

---

## §2 — ASCII Video

Convert video/audio to colored ASCII MP4/GIF.

Single self-contained Python script per project. Stack: Python + NumPy + SciPy + Pillow + ffmpeg.

Modes: Video-to-ASCII, Audio-reactive, Generative, Hybrid, Lyrics/text.

Key pipeline: `INPUT → ANALYZE → SCENE_FN → TONEMAP → SHADE → ENCODE`

Critical: Always disable FES (`p5.disableFriendlyErrors = true`), use adaptive tonemap (not linear multipliers), never `stderr=subprocess.PIPE` with long-running ffmpeg.

---

## §3 — Excalidraw (reference)

See the `excalidraw` skill for full Excalidraw JSON diagram reference.

Key: Use container binding (boundElements + containerId) for labeled shapes. Never use `"label"` property on shapes.

Save as `.excalidraw` files, open at excalidraw.com.

---

## §4 — Architecture Diagrams (SVG/HTML)

Dark-themed SVG architecture diagrams as standalone HTML.

Color palette:
- Frontend: cyan-400 (`#22d3ee`)
- Backend: emerald-400 (`#34d399`)
- Database: violet-400 (`#a78bfa`)
- AWS/Cloud: amber-400 (`#fbbf24`)

Background: Slate-950 (`#020617`) with 40px grid pattern.
Font: JetBrains Mono from Google Fonts.

---

## §5 — p5.js

Browser-based generative art and interactive visualizations.

### Setup

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.11.3/p5.min.js"></script>
```

Always: `randomSeed(CONFIG.seed)` + `noiseSeed(CONFIG.seed)` for reproducibility.
Use `colorMode(HSB, 360, 100, 100, 100)` for generative art.

### Export

- PNG: `saveCanvas('output', 'png')`
- GIF: `saveGif('output', 5)`
- MP4: Puppeteer headless + ffmpeg

---

## §6 — Manim (Math Animations)

3Brown1Brown-style explainer videos.

```bash
pip install manim
manim -ql script.py Scene1 Scene2  # draft
manim -qh script.py Scene1 Scene2  # production
```

Key: Use monospace fonts only (Pango breaks proportional). Minimum font_size=18.
Always wait after animations: `self.wait(1.0)` minimum.

---

## §7 — Infographics

21 layouts × 21 styles for visual summaries.

Default: `bento-grid` + `craft-handmade`, landscape 16:9.

Use `clarify` tool to confirm layout×style combination with user before generating.

---

## §8 — Pretext

DOM-free multiline text measurement and layout via `@chenglou/pretext`.

Two use cases:
1. **Measure then render with CSS/DOM** — virtualized lists, card heights
2. **Measure and render yourself** — text flowing around obstacles, kinetic typography

Key: Pin version (`@0.0.6`), use `esm.sh`, never re-prepare in animation loop.

---

## §9 — ComfyUI

For image/video/audio generation with Stable Diffusion, Flux, etc.

Skill covers: comfy-cli setup, REST/WebSocket API execution, workflow format, model management.

Key scripts: `run_workflow.py`, `health_check.py`, `extract_schema.py`.
