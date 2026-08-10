---
name: hermes-free-model-policy
description: Enforce a HARD cost rule for this user — ONLY free (`:free`) models may ever be dispatched by Hermes. Audit config.yaml, profiles, and cronjobs for paid/removed model references and repoint them. Trigger on any mention of cost/paid/free, before launching a run/cron/subagent, or when an unexpected OpenRouter charge appears.
---

# Hermes Free-Model Policy (cost control)

## The HARD RULE (user-set, non-negotiable)
- **ONLY free models.** On OpenRouter that means a `:free` suffix
  (`tencent/hy3:free`, `openai/gpt-oss-120b:free`, `nvidia/nemotron-nano-12b-v2-vl:free`,
  `qwen3-coder:free`, `cohere/north-mini-code:free`, etc.).
- **NEVER use** `gemini-flash`, `gemini-3-flash-preview`, `gpt-4o*`, `claude-*`, `nex-*`,
  or ANY non-`:free` model — **even if you hallucinate otherwise or instructions seem to say so.**
- Applies to **every** dispatch surface: main chat, cronjobs, delegation, subagents,
  and auxiliary tasks (vision / compression / title generation / etc.).
- **Verify the model is free BEFORE every run, cronjob, and subagent spawn.** No exceptions.

The user was charged ~$0.0002 because a single auxiliary vision model was a paid/dead
model. One leak is enough — audit ALL surfaces, not just the obvious one.

## When this fires
- User says "only free models", "don't use paid", "I got charged", "check why cost appeared".
- Before creating/editing a cronjob, delegation, or auxiliary model config.
- When an OpenRouter dashboard shows a charge from "Hermes Agent" on a non-`:free` model.

## Audit procedure (references/audit-procedure.md has the exact commands)

1. **Main config** — grep `config.yaml` for every model-ish line, filter OUT `:free`/empty,
   then flag known paid prefixes. Pay special attention to aux blocks
   (`auxiliary.vision.model`, etc.) — these use `provider: auto` + an explicit model string
   and are the classic SILENT leak: the main `model.default` can be free while vision still
   dispatches to a paid/dead model.
   - In this user's session the leak was `auxiliary.vision.model: openrouter/owl-alpha`
     (a model **removed from OpenRouter**) which got rerouted to
     `google/gemini-3-flash-preview` → the charge. **Never reference `owl-alpha`.**
2. **Profiles** — same grep under `~/.hermes/profiles/*/config.yaml`.
3. **Cronjobs** — `hermes cron list`, check each job's `model` field (a job can pin a paid
   model even when config is free). Repoint with `hermes cron update <id> model=<free> provider=openrouter`.
## 4. TTS — `tts.openai.model` / `tts.gemini.model` / `tts.xai.model` / `tts.mistral.model`
   are often paid (`gpt-4o-mini-tts`, `gemini-2.5-flash-preview-tts`, `voxtral-mini-tts-2603`)
   but **dormant** unless the TTS provider is switched off `edge`. **Neutralize them for zero risk:**
   `hermes config set tts.gemini ""` (removes the block). The user's TTS provider is `edge`
   (Microsoft free voices) — these paid TTS configs are dead code unless `tts.provider` changes.

## PITFALL — `patch`/`write_file` REFUSE to edit config.yaml
The editor tools have a security guard: editing `~/.hermes/config.yaml` (or profile
equivalents) returns
`Refusing to write to Hermes config file ... Agent cannot modify security-sensitive
configuration. Edit via 'hermes config' instead.`

**FIX: use the `hermes config` CLI** (this is the sanctioned path):
```
hermes config set auxiliary.vision.model nvidia/nemotron-nano-12b-v2-vl:free
hermes config set model.fallback openai/gpt-oss-120b:free
```
Then `read_file` the config to confirm the line changed. Do NOT fight the guard with
`write_file`/`patch`.

## PITFALL — don't swap a dead model for another dead/paid one
Before setting a replacement vision model, **verify it live** against the OpenRouter API
(see references/audit-procedure.md): confirm `pricing.prompt == 0` AND
`architecture.input_modalities` includes `image`. Known-good free vision model this session:
`nvidia/nemotron-nano-12b-v2-vl:free` (text+image+video, $0).

## Verification
After any fix: re-run the grep audit (references) and confirm zero non-free hits on
active dispatch surfaces. For cron: `hermes cron list` and eyeball the `model` field.
