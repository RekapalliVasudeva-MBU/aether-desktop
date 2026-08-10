# WhatsApp Bridge — Quick Reference

## Bridge Process

The WhatsApp bridge is a Node.js (Baileys) process that runs on `localhost:3000`.
It is **independent** from the Hermes gateway — both must be running.

### Start the bridge

```bash
# macOS / Linux
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
node bridge.js --port 3000 --session ~/.hermes/whatsapp/session --mode self-chat &

# Windows (git-bash)
cd /c/Users/<user>/AppData/Local/hermes/hermes-agent/scripts/whatsapp-bridge
node bridge.js --port 3000 --session "C:\Users\<user>\AppData\Local\hermes\whatsapp\session" --mode self-chat &
```

**Important:** Use `terminal(background=true)` when starting the bridge from Hermes — the bridge is a long-lived process and will block the foreground. Then verify with a separate `terminal` call after a sleep.

### Verify bridge is running

```bash
curl -s http://localhost:3000/health
# {"status":"connected","queueLength":0,"uptime":...}
```

If this returns empty or "bridge not responding", the bridge process is dead even if the PID file exists.

### Check for stale PID

```bash
cat ~/.hermes/whatsapp/session/bridge.pid
# If the PID process doesn't exist, the bridge crashed without cleanup
```

On Windows, use `taskkill /PID <pid> /F` to clean up a stale PID before restarting.

## Sending Messages (Workaround for JID Decode Bug)

When `send_message` tool fails with `Cannot destructure property 'user' of 'jidDecode(...)'`,
use the bridge's HTTP API directly:

```bash
curl -s -X POST http://localhost:3000/send \
  -H "Content-Type: application/json" \
  -H "Host: localhost" \
  -d '{"chatId": "<number>@s.whatsapp.net", "message": "your message"}'
```

Response: `{"success":true,"messageId":"3EB00...","messageIds":["3EB00..."]}`

### Phone number format

- **Always use full international format** with country code: `<country_code><number>@s.whatsapp.net`
- Example: Indian number 8897922065 → `918897922065@s.whatsapp.net`
- The `send_message` tool may fail on bare numbers without country code
- The `send_message` tool may also fail with `Could not resolve '<number>@s.whatsapp.net' on whatsapp` — this is a known JID resolution issue in self-chat mode; use the curl workaround above

### Retry pattern

Do NOT retry `send_message` with the same arguments more than twice — the JID decode error is deterministic. Switch to the curl workaround after the first failure.

## Key Paths (Windows)

| Item | Path |
|------|------|
| `.env` | `C:\Users\<user>\AppData\Local\hermes\.env` |
| Session dir | `C:\Users\<user>\AppData\Local\hermes\whatsapp\session\` |
| Bridge script | `C:\Users\<user>\AppData\Local\hermes\hermes-agent\scripts\whatsapp-bridge\bridge.js` |
| Config | `C:\Users\<user>\AppData\Local\hermes\config.yaml` |
| PID file | `C:\Users\<user>\AppData\Local\hermes\whatsapp\session\bridge.pid` |

## Key Paths (macOS / Linux)

| Item | Path |
|------|------|
| `.env` | `~/.hermes/.env` |
| Session dir | `~/.hermes/whatsapp/session/` |
| Bridge script | `~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js` |
| Config | `~/.hermes/config.yaml` |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Cannot connect to host localhost:3000" | Bridge not running | Start bridge manually (see above) |
| "jidDecode(...)" error | `send_message` can't parse bare phone numbers | Use `curl` to `/send` endpoint directly |
| "Could not resolve '<number>@s.whatsapp.net'" | JID resolution fails in self-chat mode | Use `curl` to `/send` endpoint directly |
| Bridge starts then disconnects | Stale creds or session corruption | Delete session dir, re-pair with `hermes whatsapp` |
| Bridge PID file exists but process is dead | Crash without cleanup | `kill <pid>` (or `taskkill /PID <pid> /F` on Windows), remove stale PID, restart |
| Bridge exits with "stdin is not tty" | Bridge was run in foreground without a TTY | Use `terminal(background=true)` or `&` to run in background |
| `send_message` retries failing identically | JID decode is deterministic, not transient | Switch to curl workaround after first failure |

## Self-Chat Mode Notes

- In self-chat mode, the bot only responds to messages you send to yourself (your own number)
- Messages to other numbers (like sending to Mom) go through the bridge but won't trigger a bot response
- To chat with Hermes on WhatsApp: message your own number, and the bot will reply in that self-chat
- `WHATSAPP_MODE=self-chat` and `WHATSAPP_ALLOWED_USERS=<your_number>` must be set in `.env`

## Gateway vs Bridge: Understanding the Two Processes

Many WhatsApp issues come from confusing these two independent processes:

1. **Hermes Gateway** (`hermes gateway start`) — Python process that routes messages between platforms and the AI. Check with `hermes gateway status`.
2. **WhatsApp Bridge** (`node bridge.js`) — Node.js process on port 3000 that connects to WhatsApp via Baileys. Check with `curl http://localhost:3000/health`.

The gateway can be running while the bridge is down. Always check both when debugging WhatsApp issues.
