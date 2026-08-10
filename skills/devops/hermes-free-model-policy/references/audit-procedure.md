# Free-model audit procedure (exact commands)

## 1. Grep the live config for non-free models
Run from `C:\Users\valte\AppData\Local\hermes` (use MSYS paths in the terminal):
```bash
cd /c/Users/valte/AppData/Local/hermes
# active (default) profile
grep -iE "model:|fallback:|default:|delegation:|fallback_model:" config.yaml \
  | grep -ivE ":free|: ''|: \"" \
  | grep -iE "openrouter/|google/|anthropic/|gemini|gpt-|claude|nex-|owl"
# also every profile
grep -riE "model:|fallback:|default:" profiles/*/config.yaml \
  | grep -ivE ":free|: ''" \
  | grep -iE "openrouter/|google/|anthropic/|gemini|gpt-|claude|nex-|owl"
```
Expected clean result: only `openrouter/free` (literal, not a real model),
`gpt-4o-mini-tts` and `gemini-2.5-flash-preview-tts` (both DORMANT — TTS provider is
`edge`, never invoked). Everything else must carry `:free`.

## 2. Cronjobs
```bash
hermes cron list
```
For each job check `model`. If paid/empty, repoint:
```bash
hermes cron update <job_id> model=openai/gpt-oss-120b:free provider=openrouter
```

## 3. Live-verify a candidate free model (OpenRouter API)
Read-only GET, no install. Confirms $0 cost AND image support before you trust it as a
vision replacement:
```bash
curl -s --max-time 30 "https://openrouter.ai/api/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ms=d.get('data',[])
cands=['nvidia/nemotron-nano-12b-v2-vl:free','qwen/qwen2.5-vl-72b-instruct:free',
       'google/gemini-2.0-flash-exp:free']
for m in ms:
    if m['id'] in cands:
        arch=m.get('architecture',{})
        inp=arch.get('input_modalities',[]) if isinstance(arch,dict) else []
        print(m['id'],'| input=',inp,'| prompt=$',m.get('pricing',{}).get('prompt'))
"
```
Known-good free vision model (verified this session):
`nvidia/nemotron-nano-12b-v2-vl:free` — modality text+image+video, prompt $0.

## 4. Apply a fix via the sanctioned CLI (patch/write_file are BLOCKED on config.yaml)
```bash
hermes config set auxiliary.vision.model nvidia/nemotron-nano-12b-v2-vl:free
```
Then `read_file` `config.yaml` to confirm the line changed.
