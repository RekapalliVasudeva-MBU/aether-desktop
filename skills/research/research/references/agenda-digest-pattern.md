# Agenda-Digest-Pattern (2026-07-09 session)

## Scope: RAG-news digest automation for recurring cron jobs

### Core Workflow Pattern

For recurring RAG news digests, the research skill recommends this sequence:

1. **RSS-first for AI news** (most reliable):
   - `https://arstechnica.com/ai/feed/` 
   - `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
   - Always try RSS feeds before HTML scraping

2. **arXiv search strategy**:
   - Use `all:knowledge+AND+retrieval` or `all:memory+augmented` for better RAG-related results
   - General "retrieval augmented generation" searches yield ~975K results
   - Most relevant papers are in adjacent areas (knowledge-augmented, retrieval-based LMs)

3. **Parsing approach**:
   - RSS → structured parsing (feedparser)
   - HTML → BeautifulSoup fallback (more robust)
   - XML → ElementTree or defusedxml ElementTree (secure)

### Key Technical Findings

#### RSS vs HTML trade-offs
- RSS: structured, fast, reliable, less bot-prone
- HTML: up-to-date, but requires bot detection bypass
- Recommendation: RSS first, HTML only as fallback

#### Windows/MSYS path resolution
- `write_file` lands scripts in: `C:\tmp`
- Terminal resolves `/tmp` to: `C:\Users\<user>\AppData\Local\Temp`
- Always use absolute Windows paths in scripts for cross-platform compatibility

#### Security considerations
- Python `xml.etree.ElementTree` vulnerable to XXE/billion-laughs attacks
- Use `defusedxml.ElementTree` in untrusted contexts
- Document security decisions with inline comments

#### Common pitfalls
1. **Topic breadth**: Too general searches (`all:rag`) return too many adjacent-area results
2. **Parsing order**: HTML scraping before RSS → frequent 202 errors
3. **Path handling**: Relative `/tmp` paths break on Windows/MSYS
4. **User-Agent**: Generic Python string blocks modern sites
5. **Error handling**: Silent failures without proper retry logic

### Configuration recommendations for recurring digests

```yaml
{
  "skills": [],
  "prompt": "Use RSS first for AI news, fallback to HTML. Use arXiv knowledge/retrieval searches. Always use absolute paths on Windows. Include User-Agent headers. Retry failed requests with exponential backoff."
}
```

### Pattern summary table

| Task | Recommended approach | Why |
|------|---------------------|-----|
| AI news aggregation | RSS feeds first, HTML fallback | Structured data, less bot-prone |
| arXiv RAG searches | Broader terms: `knowledge+AND+retrieval` | More focused results |
| Cross-platform scripts | Absolute Windows paths | Resolves `/tmp` mismatch |
| XML parsing | `defusedxml` over stdlib | Prevents XXE attacks |
| Error handling | Retry with backoff | Network reliability |

### Performance optimizations

1. **Rate limiting**: 0.5-2 seconds between requests
2. **Concurrency**: Batch similar-domain requests
3. **Caching**: Store recent RSS results locally
4. **Validation**: Check feed health before parsing

This pattern produced:
- Daily RAG news digest file
- Robust arXiv paper selection
- Minimal technical failures
- Clear separation of concerns (RSS vs HTML vs XML)