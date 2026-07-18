# TODOS

Organized by component, then priority (P0 top → P4, Completed at bottom).
Update as work ships. Format each item:

```
- [ ] **Priority:** P1
  **Component:** rag
  **Description:** <what + Done definition>
```

## desktop_app
- [ ] **Priority:** P0
  **Component:** app
  **Description:** App fails to open on stale single-instance mutex — verify other instance is actually serving before bailing; take over zombie. (Done: app starts clean on all cases)

## agent
- [ ] **Priority:** P2
  **Component:** agent
  **Description:** Agent loop step discipline — visible thinking/tool/reflect steps in chat transcript. (Done: execution_step animation shipped in v1.2.8)

## rag
- [ ] **Priority:** P1
  **Component:** rag
  **Description:** Batch PDF ingest resilient to one bad file (no full abort). (Done: v1.2.9 ingested 25 PDFs / 344 chunks)

## sessions
- [ ] **Priority:** P1
  **Component:** sessions
  **Description:** Sessions panel: click past chat loads its messages (selectSession switches to Chat view). (Done: v1.3.0)

## Completed
- v1.3.0: full Sessions panel redesign + add-file + context meter
- v1.2.9: sessions select switches view; robust single-instance mutex; RAG batch ingest
- v1.2.8: execution_step animation; two-layer context compaction
- v1.2.7: Sessions panel; web_search fix; DELETE /api/sessions
- v1.2.6: Hermes One → Aether branding; Settings Appearance/Data; frozen-exe fix
