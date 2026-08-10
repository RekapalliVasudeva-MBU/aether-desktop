# Cron Research Patterns — Reference

## Common Pitfalls & Solutions

### 1. Browser Skill Dependency Issue
**Problem**: Cron jobs listing `browser` skill fail because browser tools are built-in, not a skill.
**Solution**: Remove `skills[]` array from cron job config or use only built-in tools.
**Error signature**: "⚠️ Skill(s) not found and skipped: browser"

### 2. curl Fails on JavaScript-Heavy Sites
**Problem**: Sites like The Verge and Ars Technica AI pages are SPAs that only render client-side. curl returns empty shell.
**Solution**: Use RSS feeds instead:
- Ars Technica AI: `https://arstechnica.com/ai/feed/`
- The Verge AI: `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- Hacker News: `https://hacker-news.firebaseio.com/v0/topstories.json`

### 3. curl + Python HTML Parsing
MSYS grep lacks PCRE support. Use Python for reliable parsing:

```python
import sys, re
html = sys.stdin.read()
titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
for t in titles[:20]:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if clean and len(clean) > 10:
        print(clean)
```

### 4. User Agent Required
Many sites block requests without User-Agent header:
```bash
curl -sL "URL" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
```

### 5. Terminal Tool Timeout Issues
When terminal returns empty output:
1. Check exit_code first (0 = success, -1 = shell error)
2. If shell error, the command itself is broken
3. If exit_code 0 but empty output, site returned nothing (JS-rendered, blocked, etc.)

## Reliable News Sources for AI Research

| Source | URL | Notes |
|--------|-----|-------|
| Hacker News | `news.ycombinator.com` | Works well with curl, JSON API available |
| Ars Technica AI RSS | `arstechnica.com/ai/feed/` | Structured, parseable XML |
| The Verge AI RSS | `theverge.com/rss/ai-artificial-intelligence/index.xml` | Structured, parseable XML |
| Ars Technica Tech Lab | `arstechnica.com/technology-lab/feed/` | Broader tech context |
| arXiv cs.AI | `export.arxiv.org/api/query?search_query=cat:cs.AI` | Academic papers |

## Cron Job Configuration Template

```yaml
# Correct cron job config (no skills dependency)
{
  "name": "Daily AI News Digest",
  "schedule": "0 9 * * *",
  "prompt": "[Your research prompt]",
  "skills": [],  # Empty - use built-in tools only
  "delivery": "telegram"
}
```

## Verification Checklist

Before running news research cron:
- [ ] No `browser` skill listed (built-in tools only)
- [ ] Prompt says "Use curl via terminal" not "Use browser tools"
- [ ] RSS feeds used for JS-heavy sites
- [ ] User-Agent header included in curl commands
- [ ] Python parsing fallback ready for MSYS grep limitations