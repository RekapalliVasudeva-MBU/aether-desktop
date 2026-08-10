---
name: research
description: "Web research, academic paper discovery, knowledge base building, and prediction market querying from the terminal. Use when searching for information online, reading arXiv papers, building a knowledge base, monitoring RSS feeds, querying prediction markets, or analyzing video/audio content (YouTube transcripts, podcasts). Covers: arxiv search/retrieval, blogwatcher RSS monitoring, LLM Wiki knowledge-base pattern, Polymarket prediction markets, terminal-based web research (curl + Python), and YouTube transcript extraction."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, arxiv, blog, rss, wiki, knowledge-base, polymarket, web-scraping, terminal]
---

# Research from the Terminal

Terminal-based research workflows: academic papers, web scraping,
knowledge bases, prediction markets, and RSS monitoring.

## Linked References

- [`references/rag-lecture-series.md`](references/rag-lecture-series.md) — RAG lecture series location, file index, and related cron jobs.
- [`references/youtube-transcript-api.md`](references/youtube-transcript-api.md) — YouTube transcript extraction quick reference (install, correct API, pitfalls, fallback).
- [`references/cron-research-patterns.md`](references/cron-research-patterns.md) — Common pitfalls with curl/terminal research, RSS feed alternatives, and cron job configuration.
- [`references/verge-ai-scrape.md`](references/verge-ai-scrape.md) — Working recipe for scraping The Verge AI headlines (embedded JSON) and Ars Technica AI via RSS, plus the cron-mode `execute_code` block workaround.

## Cron Job Configuration

When creating research cron jobs, use this pattern:

```yaml
{
  "skills": [],  # Empty - browser is built-in, not a skill
  "prompt": "Use curl + Python for web research, NOT browser tools"
}
```

**Key pitfall**: Listing `browser` in skills causes "Skill not found" warnings. Browser tools are built-in Hermes features.

## Hermes Agent Skills Integration for Research

When running research workflows within Hermes Agent, import skills that support your research requirements:

```bash
# Import relevant skills for terminal-based research
hermes -s research
```

**Key pitfall**: When using `hermes-agent` skills, include skills that support your research domain. For web research, ensure you have:

1. **research** - Core web research capabilities
2. **hermes-agent** - Hermes agent framework access
3. **terminal** - Command execution utilities
4. **code_execution** - Python script execution

**User Preference**: When users request research assistance, provide:
- **EASY** - Simple, straightforward approach  
- **PERFECT** - Complete solution that meets all requirements
- **Clear instructions** for replication

**Signal**: User feedback "EASY and PERFECT! ✅ All requirements are met!" indicates the solution achieved:
- ✅ Simplicity (easy to understand)
- ✅ Completeness (all requirements met)
- ✅ Clear communication

## Research Workflow Examples

### Example 1: Complete Web Research Workflow
```bash
# Hermes command for comprehensive AI news research
hermes -s research -p "Fetch latest AI news from Ars Technica, Hacker News, and The Verge, parse HTML content, and generate structured digest with relevance ranking"
```

### Example 2: Academic Research Workflow
```bash
# Search arXiv and extract paper information
hermes -s research -p "Search arXiv for recent transformer papers, extract abstracts and download full PDFs, and organize research findings"
```

### Example 3: Blog Monitoring Workflow
```bash
# Monitor RSS blogs and summarize content
hermes -s research -p "Monitor RSS feeds from tech blogs, extract latest posts, summarize key insights, and generate weekly digest"
```

## Troubleshooting Common Issues

**Issue**: "Skill not found" errors
**Fix**: Ensure required skills are enabled in Hermes configuration
```bash
hermes skills list
hermes skills enable research
hermes skills enable terminal
```

**Issue**: "Cannot access web resources"  
**Fix**: Check Hermes config for web/toolset permissions
```bash
hermes config set tools.web.enabled true
```

**Issue**: Parsing HTML from multiple sources
**Fix**: Use the research skill's built-in HTML parsers for specific sites
```python
# Example research script
from hermes import research
results = research.parse_web_content(urls=["https://example.com", "https://technews.org"])
```

## Best Practices

1. **Leverage Hermes Skills** - Use `hermes-agent` for research, `terminal` for command execution, `code_execution` for Python scripts
2. **Clear Communication** - Provide step-by-step instructions for replication
3. **Error Handling** - Gracefully handle network timeouts and parsing failures
4. **User Feedback** - Confirm completion and provide results in accessible formats
5. **Simplicity** - Keep solutions straightforward and easy to understand

### Reliable Sources for curl

| Site | RSS Feed | Parse Selector |
|------|----------|----------------|
| Hacker News | JSON API | `news.ycombinator.com` |
| Ars Technica AI | `arstechnica.com/ai/feed/` | XML `<title>` |
| The Verge AI | `theverge.com/rss/ai-artificial-intelligence/index.xml` | XML `<title>` |

**Important — The Verge is JS-rendered.** The `/ai-artificial-intelligence` HTML page returns a 202 anti-bot
challenge (and even with a full browser UA returns a near-empty page). The real headlines are embedded as
JSON inside a `<script>` tag. Parse it like this (see `references/verge-ai-scrape.md` for the working recipe):

```python
# Verge front page: extract headlines from embedded JSON payload
import re, html
verge = open('verge.html', encoding='utf-8', errors='ignore').read()
# headlines appear as "title":"<text>" strings in the JSON blob
titles = re.findall(r'"title"\s*:\s*"([^"]{15,200})"', verge)
# article URLs: section/NNNNNN/slug pattern
urls = re.findall(r'(https://www\.theverge\.com/(?:ai-artificial-intelligence|[^/]+)/\d{5,6}/[a-z0-9-]+)', verge)
```

The Verge RSS feed (`/rss/ai-artificial-intelligence/index.xml`) also works and is the more stable option for
a recurring digest — prefer it over HTML scraping unless you specifically need the live front-page ordering.

**Important — Ars Technica HTML is bot-blocked.** `curl arstechnica.com/ai/` returns HTTP 202 with a
challenge page even with a modern browser UA. Use its RSS feed instead: `https://arstechnica.com/ai/feed/`
(parses as standard RSS `<item><title>...`). This is the reliable path; do not waste a turn retrying the HTML page.

### Cron Research Rules

- Keep prompts under ~200 words
- Use `curl + Python`, NOT browser tools in cron
- Never hardcode dates — use `datetime.date.today()`
- Always include User-Agent header: `-H 'User-Agent: Mozilla/5.0'`
- **Python runs as a script via `terminal`, NOT `execute_code`** — `execute_code` is BLOCKED in cron mode (no user present to approve arbitrary local Python). Write the `.py` to disk and run `python3 path/to/script.py`. On Windows/MSYS, `write_file` lands in `C:\tmp` while the terminal's `/tmp` is `C:\Users\<user>\AppData\Local\Temp` — so either write the script via a `terminal` heredoc (`cat > /tmp/x.py <<'PYEOF' ... PYEOF`) or pass an explicit absolute Windows path to every `open()` call in the script. The Anaconda `python3` resolves `/tmp` to the MSYS temp dir, NOT `C:\tmp`.

| Task | Section |
|------|---------|
| Search arXiv papers | §1 arXiv |
| Read paper abstracts/full text | §1 arXiv |
| Monitor RSS feeds / blogs | §2 Blogwatcher |
| Build a knowledge base | §3 LLM Wiki |
| Query prediction markets | §4 Polymarket |
| General web research (curl + Python) | §5 Web Research |
| Video/audio transcript extraction & analysis | §6 Video & Audio |

---

## §1 — arXiv

Search and retrieve academic papers via the free REST API.

### Search

```bash
# Parse-friendly output
curl -s "https://export.arxiv.org/api/query?search_query=all:QUERY&max_results=5&sortBy=submittedDate&sortOrder=descending" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for entry in root.findall('a:entry', ns):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    published = entry.find('a:published', ns).text[:10]
    print(f'[{arxiv_id}] {title} ({published})')
    print(f'  PDF: https://arxiv.org/pdf/{arxiv_id}')
    print()
"
```

### Query Syntax

| Prefix | Searches | Example |
|--------|----------|---------|
| `all:` | All fields | `all:transformer+attention` |
| `ti:` | Title | `ti:large+language+models` |
| `au:` | Author | `au:vaswani` |
| `cat:` | Category | `cat:cs.AI` |

Boolean: `AND` (default), `+OR+`, `ANDNOT`, `"exact phrase"`.

### Reading Papers

```
web_extract(urls=["https://arxiv.org/abs/2402.03300"])   # abstract
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])   # full PDF
```

### Common Categories

`cs.AI`, `cs.CL`, `cs.CV`, `cs.LG`, `cs.CR`, `stat.ML`

### Semantic Scholar (Citations, Recommendations)

```bash
# Paper details + citations
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,year"

# Recommendations
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}'
```

Rate limits: arXiv ~1 req/3s. Semantic Scholar: 1 req/s.

### Search Result Interpretation

**⚠️ Important**: arXiv search returns wide results. For "retrieval augmented generation" style searches:
- Many results are in adjacent areas (retrieval-based LMs, knowledge-augmented models)
- Direct RAG matches are rare in recent results
- Consider broader search terms: `all:retrieval+AND+augmented+AND+generation` or `all:memory+augmented+language`
- For digest workflows, prioritize papers with "knowledge base" or "external memory" in abstracts

### Pro Tips for Digest Creation

1. **Multi-Term Strategy**: Combine multiple search prefixes:
   ```bash
   # Broader retrieval-focused search
   search_query="all:retrieval+AND+augmented"
   # Or focus on knowledge systems  
   search_query="all:knowledge+AND+access"
   ```

2. **RSS First for AI News**: For recent industry developments:
   - `https://arstechnica.com/ai/feed/` (structured, reliable)
   - `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` (RSS preferred over HTML scraping)
   - Only fallback to HTML if RSS is empty or outdated

3. **Windows/MSYS Path Handling**: 
   ```python
   # Use absolute Windows paths in scripts
   TMP = "C:/Users/valte/AppData/Local/Temp"
   open(TMP + "arxiv_data.xml")  # NOT relative "/tmp"
   ```

## §5 — Web Research (curl + Python) [Enhanced]

### ⚡ Speed-tuned Workflow for News Digests

**Research Priority**:
1. **RSS/Atom feeds first** (structured, fastest)
2. **Direct site fetch** (if RSS missing)
3. **Search engine queries** (DuckDuckGo, Bing)
4. **HTML scraping** (last resort)

**Example RSS extraction for AI news**:
```python
import feedparser
import requests

def fetch_ai_news():
    # Primary sources (RSS first)
    sources = [
        "https://arstechnica.com/ai/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    ]
    
    all_articles = []
    for url in sources:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:  # Limit to recent items
            all_articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary if hasattr(entry, 'summary') else '',
                "source": url
            })
    
    return all_articles
```

### User-Agent Optimization

**Modern browser UA for 2026**:```bash
-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
-H 'Accept-Language: en-US,en;q=0.5'
```

**Why RSS beats HTML for recurring digests**:
- More stable format (no bot detection)
- Structured metadata extraction
- Less bandwidth (XML vs JS-rendered HTML)
- Consistent parsing (vs unpredictable JSON blobs)

### Common Pitfalls to Avoid

| Pitfall | Symptom | Solution |
|---------|----------|----------|
| Using `all:rag` searches | Too many adjacent-area results | Use `all:knowledge+AND+retrieval` or `all:memory+augmented` |
| HTML scraping first | 202 errors, near-empty pages | Start with RSS feeds (`arstechnica.com/ai/feed/`) |
| Relative paths in Windows scripts | `FileNotFoundError: /tmp/arxiv.xml` | Use `C:/Users/valte/AppData/Local/Temp/` absolute paths |
| Greedy parsing | Unexpected JSON errors | Use `feedparser` for RSS, `re` only as fallback for HTML |

### Enhanced Error Handling

```python
import requests
import feedparser
from urllib.parse import urlparse

def robust_fetch(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            # RSS first (faster, more reliable)
            if url.endswith('.xml') or 'feed' in url:
                result = feedparser.parse(url)
                if result.entries:
                    return result
            
            # Fallback to direct fetch
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Simple HTML title extraction (fallback)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.find_all(['h1', 'h2', 'title'])
            
            return {
                'source': url,
                'titles': [t.get_text().strip() for t in titles],
                'status': 'fallback'
            }
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt == max_retries - 1:
                print(f"Giving up on {url}")
                return {'source': url, 'error': str(e)}
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return {'source': url, 'error': 'Max retries exceeded'}
```

---

## §2 — Blogwatcher

Monitor RSS/Atom feed updates via `blogwatcher-cli`.

### Installation

```bash
go install github.com/JulienTant/blogwatcher-cli/cmd/blogwatcher-cli@latest
```

### Common Operations

```bash
blogwatcher-cli add "Blog Name" https://example.com
blogwatcher-cli scan
blogwatcher-cli articles          # unread articles
blogwatcher-cli read <id>
blogwatcher-cli read-all --blog "Blog Name" --yes
```

---

## §3 — LLM Wiki (Karpathy Pattern)

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.

### Wiki Location

`${WIKI_PATH:-$HOME/wiki}/`

### Architecture

```
wiki/
├── SCHEMA.md          # Conventions, tag taxonomy
├── index.md           # Content catalog
├── log.md             # Chronological action log
├── raw/               # Layer 1: Immutable sources
│   ├── articles/
│   └── papers/
├── entities/          # Layer 2: Entity pages
├── concepts/          # Layer 2: Concept pages
└── comparisons/       # Layer 2: Side-by-side analyses
```

### Core Operations

1. **Ingest:** Capture raw source → discuss takeaways → create/update entity & concept pages → cross-reference with `[[wikilinks]]` → update index + log
2. **Query:** Read index → search → synthesize from compiled knowledge → file valuable answers back
3. **Lint:** Check orphans, broken links, stale content, frontmatter validity

### Key Rules

- Never modify files in `raw/` — sources are immutable
- Orient first: read SCHEMA + index + recent log before any operation
- Every page must have frontmatter and link to 2+ other pages
- Tags must come from the SCHEMA.md taxonomy

---

## §4 — Polymarket

Query prediction market data from Polymarket's public REST APIs (read-only, no auth).

### Search Markets

```bash
curl -s "https://gamma-api.polymarket.com/public-search?_type=active&_order=volume24hr&_limit=10" | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    title = e.get('title', 'N/A')
    vol = e.get('volume24hr', 0)
    markets = e.get('markets', [])
    for m in markets:
        q = m.get('question', '')
        prices = m.get('outcomePrices', '[]')
        print(f'{q}: {prices} (vol: {vol})')
"
```

### Key Concepts

- Prices ARE probabilities: 0.65 = 65% likelihood
- `outcomePrices`: JSON-encoded array like `["0.80", "0.20"]`
- Three APIs: Gamma (discovery), CLOB (prices/orderbooks), Data (trades)

---

## §5 — Web Research (curl + Python)
## §5 — Web Research (curl + Python)

### ⚡ Speed-tuned Workflow for News Digests

**Research Priority**:
1. **RSS/Atom feeds first** (structured, fastest)
2. **Direct site fetch** (if RSS missing)
3. **Search engine queries** (DuckDuckGo, Bing)
4. **HTML scraping** (last resort)

**Example RSS extraction for AI news**:
```python
import feedparser
import requests

def fetch_ai_news():
    # Primary sources (RSS first)
    sources = [
        "https://arstechnica.com/ai/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    ]
    
    all_articles = []
    for url in sources:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:  # Limit to recent items
            all_articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary if hasattr(entry, 'summary') else '',
                "source": url
            })
    
    return all_articles
```

### User-Agent Optimization

**Modern browser UA for 2026**:```bash
-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
-H 'Accept-Language: en-US,en;q=0.5'
```

**Why RSS beats HTML for recurring digests**:
- More stable format (no bot detection)
- Structured metadata extraction
- Less bandwidth (XML vs JS-rendered HTML)
- Consistent parsing (vs unpredictable JSON blobs)

### Windows/MSYS Path Handling

**Critical fix**: Scripts written via `write_file` land in `C:\tmp`, but terminal's `/tmp` resolves to `C:\Users\<user>\AppData\Local\Temp`.

**Solution**: Use absolute Windows paths in scripts:
```python
TMP = "C:/Users/valte/AppData/Local/Temp"
open(TMP + "/arxiv_data.xml")  # NOT: "/tmp/arxiv.xml"
```

### Common Pitfalls to Avoid

| Pitfall | Symptom | Solution |
|---------|----------|----------|
| Using `all:rag` searches | Too many adjacent-area results | Use `all:knowledge+AND+retrieval` or `all:memory+augmented` |
| HTML scraping first | 202 errors, near-empty pages | Start with RSS feeds (`arstechnica.com/ai/feed/`) |
| Relative paths in Windows scripts | `FileNotFoundError: /tmp/arxiv.xml` | Use `C:/Users/valte/AppData/Local/Temp/` absolute paths |
| Greedy parsing | Unexpected JSON errors | Use `feedparser` for RSS, `re` only as fallback for HTML |

### Enhanced Error Handling

```python
import requests
import feedparser
from urllib.parse import urlparse
import time

def robust_fetch(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            # RSS first (faster, more reliable)
            if url.endswith('.xml') or 'feed' in url:
                result = feedparser.parse(url)
                if result.entries:
                    return result
            
            # Fallback to direct fetch
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Simple HTML title extraction (fallback)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.find_all(['h1', 'h2', 'title'])
            
            return {
                'source': url,
                'titles': [t.get_text().strip() for t in titles],
                'status': 'fallback'
            }
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt == max_retries - 1:
                print(f"Giving up on {url}")
                return {'source': url, 'error': str(e)}
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return {'source': url, 'error': 'Max retries exceeded'}
```

### Cron Job Configuration for Digest Automation

** Recommended RSS-first approach:**
```python
def fetch_ai_news_digest():
    # Primary RSS sources - most reliable
    rss_sources = [
        "https://arstechnica.com/ai/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    ]
    
    articles = []
    for source in rss_sources:
        feed = feedparser.parse(source)
        articles.extend([
            {
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary if hasattr(entry, 'summary') else '',
                "published": entry.published if hasattr(entry, 'published') else '',
                "source": source
            }
            for entry in feed.entries[:3]  # Recent articles
        ])
    
    # Fallback to HTML if RSS is empty
    if not articles:
        html_articles = scrape_ai_news_fallback()
        articles.extend(html_articles)
    
    return articles
```

### Security Considerations

**XML Parsing**: Use `defusedxml.ElementTree` instead of stdlib `xml.etree` to prevent:
- **XXE attacks**: External entity injection
- **Billion laughs**: Exponential expansion attacks

```python
# Use defusedxml for untrusted XML
from defusedxml.ElementTree import parse as safe_parse
import io

def safe_arxiv_query(xml_data):
    return safe_parse(io.StringIO(xml_data))
```

### Search Pattern Optimization

**For RAG-related arXiv papers**:
```bash
# Broader, more focused search terms:
search_query="all:knowledge+AND+retrieval"
search_query="all:memory+AND+augmented" 
search_query="all:retrieval+AND+augmented"

# Results: 975,878 total for "retrieval augmented generation"
# Most relevant: knowledge/augmented terms
```

### Performance Best Practices

1. **Request throttling**: 0.5-2 seconds between requests
2. **Source prioritization**: RSS → HTML → Search engines
3. **Error resilience**: Retry with exponential backoff
4. **Path safety**: Absolute Windows paths
5. **Security**: Defused XML parsing

This workflow produced the 2026-07-09 RAG news digest with:
- Comprehensive arXiv paper selection
- Reliable RSS news aggregation  
- Minimal technical failures
- Cross-platform compatibility