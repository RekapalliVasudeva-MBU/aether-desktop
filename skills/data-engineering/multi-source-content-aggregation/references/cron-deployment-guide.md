# Cron Job Deployment Guide

## Overview
This guide covers deploying the multi-source digest generator as a scheduled cron job on Windows (via Task Scheduler) or Linux/macOS (via cron).

## Windows Task Scheduler (Recommended for this user)

### Create a Basic Task
1. Open **Task Scheduler** (`taskschd.msc`)
2. Click **Create Basic Task...**
3. Name: `RAG Daily News Digest`
4. Trigger: **Daily** at 06:00 AM (or preferred time)
5. Action: **Start a Program**

### Program/Script
```
C:\Users\valte\AppData\Local\Programs\Python\Python311\python.exe
```
Or if using uv:
```
C:\Users\valte\.cargo\bin\uv.exe
```

### Arguments (for direct Python)
```
C:\Users\valte\AppData\Local\hermes\scripts\generate_rag_digest.py
```

### Arguments (for uv run)
```
run --directory C:\Users\valte\AppData\Local\hermes python scripts/generate_rag_digest.py
```

### Start In (Optional)
```
C:\Users\valte\AppData\Local\hermes
```

### Settings
- ✅ Run only if network available
- ✅ Run task as soon as possible after scheduled start is missed
- ☐ Stop task if runs longer than: 30 minutes
- ✅ If running, do not start new instance

## Alternative: Hermes Cron (Built-in)

Hermes has a built-in cron system. Add to `~/.hermes/cron/rag-digest.yaml`:

```yaml
name: "rag-daily-digest"
schedule: "0 6 * * *"  # Daily at 6 AM UTC
timezone: "America/Los_Angeles"
command: "python scripts/generate_rag_digest.py"
working_dir: "C:/Users/valte/AppData/Local/hermes"
notify_on_failure: true
notify_on_success: false
env:
  PYTHONPATH: "C:/Users/valte/AppData/Local/hermes"
```

Then register:
```bash
hermes cron add rag-daily-digest.yaml
hermes cron enable rag-daily-digest
```

## Linux/macOS Cron

```bash
# Edit crontab
crontab -e

# Add line (daily at 6 AM)
0 6 * * * /usr/bin/python3 /path/to/hermes/scripts/generate_rag_digest.py >> /var/log/rag-digest.log 2>&1

# Or with uv
0 6 * * * cd /path/to/hermes && /home/user/.cargo/bin/uv run python scripts/generate_rag_digest.py >> /var/log/rag-digest.log 2>&1
```

## Script Template (generate_rag_digest.py)

```python
#!/usr/bin/env python3
"""
Daily RAG News Digest Generator
Run via cron/Task Scheduler to fetch and compile daily digest.
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the digest generator
from scripts.digest_generator import generate_daily_digest

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(os.environ.get("RAG_DIGEST_OUTPUT", "C:/Users/valte/RAG-lecture"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"RAG_News_Digest_{today}.md"
    
    print(f"[{datetime.now().isoformat()}] Generating digest for {today}")
    print(f"Output: {output_file}")
    
    try:
        generate_daily_digest(output_file)
        print(f"[{datetime.now().isoformat()}] Success: {output_file}")
        return 0
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Core Digest Generator (digest_generator.py)

```python
"""
Core digest generation logic - importable and testable.
"""
import requests
from defusedxml.ElementTree import fromstring
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---
SOURCES = {
    "arxiv": {
        "url": "http://export.arxiv.org/api/query",
        "params": {
            "search_query": 'all:"retrieval augmented generation" OR all:RAG OR all:"vector database" OR all:"graph RAG" OR all:"dense retrieval" OR all:reranking OR all:faiss OR all:milvus OR all:weaviate OR all:pinecone OR all:qdrant OR all:chromadb',
            "start": 0,
            "max_results": 30,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        },
        "days_back": 3,
        "min_items": 10
    },
    "hacker_news": {
        "url": "https://hn.algolia.com/api/v1/search",
        "params": {
            "query": "RAG OR \"retrieval augmented generation\" OR \"vector database\"",
            "tags": "story",
            "hitsPerPage": 20
        },
        "days_back": 7,
        "min_items": 5
    },
    "ars_technica": {
        "feeds": ["https://arstechnica.com/ai/feed/", "https://arstechnica.com/feed/"],
        "keywords": ["ai", "ml", "machine learning", "llm", "rag", "retrieval", "vector", "neural", "gpt", "llama", "openai", "anthropic", "transformer", "generative", "embedding", "semantic search"],
        "max_items": 15,
        "days_back": 2,
        "min_items": 3
    }
}

OUTPUT_TEMPLATE = """# RAG News Digest - {date}

Generated: {generated}

## arXiv Latest Papers ({arxiv_count})

{arxiv_items}

## Hacker News (RAG/Vector DB related) ({hn_count})

{hn_items}

## Ars Technica (AI/ML/RAG related) ({ars_count})

{ars_items}
"""

# --- Fetchers ---

def fetch_arxiv():
    cfg = SOURCES["arxiv"]
    resp = requests.get(cfg["url"], params=cfg["params"], timeout=30)
    resp.raise_for_status()
    
    root = fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    papers = []
    cutoff = datetime.now() - timedelta(days=cfg["days_back"])
    
    for entry in root.findall(".//atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        link = entry.find("atom:link[@rel='alternate']", ns).get("href")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        published_str = entry.find("atom:published", ns).text
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        
        if published < cutoff:
            continue
            
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        
        # Secondary filter for RAG relevance
        text = (title + " " + summary).lower()
        rag_keywords = ["rag", "retrieval augmented", "retrieval-augmented", "vector database", "vector store",
                       "graph rag", "dense retrieval", "rerank", "faiss", "milvus", "pinecone", "weaviate",
                       "qdrant", "chroma", "lancedb", "embedding", "semantic search"]
        if not any(kw in text for kw in rag_keywords):
            continue
        
        papers.append({
            "title": title,
            "link": link,
            "summary": summary[:500],
            "published": published.strftime("%Y-%m-%d"),
            "authors": ", ".join(authors[:3])
        })
    
    return papers[:20]

def fetch_hacker_news():
    cfg = SOURCES["hacker_news"]
    resp = requests.get(cfg["url"], params=cfg["params"], timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    stories = []
    cutoff = datetime.now() - timedelta(days=cfg["days_back"])
    
    for hit in data.get("hits", []):
        if not hit.get("url"):
            continue
        created = datetime.fromtimestamp(hit["created_at_i"])
        if created < cutoff:
            continue
        stories.append({
            "title": hit["title"],
            "url": hit["url"],
            "points": hit["points"],
            "author": hit["author"],
            "date": created.strftime("%Y-%m-%d")
        })
    
    return stories[:15]

def fetch_ars_technica():
    cfg = SOURCES["ars_technica"]
    ns = {
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'slash': 'http://purl.org/rss/1.0/modules/slash/'
    }
    keywords = [k.lower() for k in cfg["keywords"]]
    cutoff = datetime.now() - timedelta(days=cfg["days_back"])
    seen = set()
    all_items = []
    
    for feed_url in cfg["feeds"]:
        try:
            resp = requests.get(feed_url, timeout=30)
            resp.raise_for_status()
            root = fromstring(resp.content)
            
            for item in root.findall(".//item")[:cfg["max_items"]]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                if link in seen:
                    continue
                
                pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
                pub_date = None
                if pub_date_str:
                    try:
                        pub_date = parsedate_to_datetime(pub_date_str)
                        if pub_date.tzinfo is not None:
                            pub_date = pub_date.replace(tzinfo=None)
                    except Exception:
                        pass
                
                if pub_date and pub_date < cutoff:
                    continue
                
                desc = item.find("description").text if item.find("description") is not None else ""
                content_elem = item.find("content:encoded", ns)
                content = content_elem.text if content_elem is not None else ""
                
                full_text = f"{title} {desc} {content}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue
                
                seen.add(link)
                all_items.append({
                    "title": title,
                    "link": link,
                    "pub_date": pub_date.strftime("%Y-%m-%d") if pub_date else pub_date_str,
                    "description": desc[:300]
                })
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
    
    all_items.sort(key=lambda x: x["pub_date"] or "", reverse=True)
    return all_items[:10]

# --- Formatters ---

def format_arxiv(papers):
    if not papers:
        return "*No relevant papers found in the last 3 days.*\n"
    lines = []
    for p in papers:
        lines.append(f"### {p['title']}")
        lines.append(f"**Authors:** {p['authors']}  ")
        lines.append(f"**Published:** {p['published']}  ")
        lines.append(f"**Link:** {p['link']}  ")
        lines.append(f"**Abstract:** {p['summary']}...  ")
        lines.append("")
    return "\n".join(lines)

def format_hn(stories):
    if not stories:
        return "*No relevant stories found in the last 7 days.*\n"
    lines = []
    for s in stories:
        lines.append(f"- [{s['title']}]({s['url']}) ({s['points']} points, by {s['author']})")
    return "\n".join(lines) + "\n"

def format_ars(items):
    if not items:
        return "*No relevant articles found in the last 2 days.*\n"
    lines = []
    for item in items:
        lines.append(f"- [{item['title']}]({item['link']}) ({item['pub_date']})")
        lines.append(f"  {item['description']}...")
        lines.append("")
    return "\n".join(lines)

# --- Main Generator ---

def generate_daily_digest(output_path: Path):
    """Generate the daily digest and write to output_path."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    generated = datetime.now().isoformat()
    
    print("Fetching arXiv...")
    arxiv_papers = fetch_arxiv()
    
    print("Fetching Hacker News...")
    hn_stories = fetch_hacker_news()
    
    print("Fetching Ars Technica...")
    ars_items = fetch_ars_technica()
    
    content = OUTPUT_TEMPLATE.format(
        date=date_str,
        generated=generated,
        arxiv_count=len(arxiv_papers),
        arxiv_items=format_arxiv(arxiv_papers),
        hn_count=len(hn_stories),
        hn_items=format_hn(hn_stories),
        ars_count=len(ars_items),
        ars_items=format_ars(ars_items)
    )
    
    output_path.write_text(content, encoding="utf-8")
    print(f"Written to {output_path}")
    return content

if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("RAG_News_Digest.md")
    generate_daily_digest(out)
```

## Monitoring & Alerting

### Health Check Endpoint
```python
# Add to generate_rag_digest.py
def health_check():
    """Verify all sources are reachable."""
    checks = {}
    for name, cfg in SOURCES.items():
        try:
            if name == "arxiv":
                resp = requests.get(cfg["url"], params=cfg["params"], timeout=10)
            elif name == "hacker_news":
                resp = requests.get(cfg["url"], params=cfg["params"], timeout=10)
            elif name == "ars_technica":
                resp = requests.get(cfg["feeds"][0], timeout=10)
            checks[name] = resp.status_code == 200
        except Exception as e:
            checks[name] = False
    return all(checks.values()), checks
```

### Failure Notification (Windows)
```powershell
# In Task Scheduler action, use a wrapper script that sends email on failure
# Or use Hermes built-in notification:
# hermes cron add --notify-on-failure --email user@example.com
```

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Task doesn't run | Check "Run whether user is logged on or not" + "Run with highest privileges" |
| Python not found | Use full path to python.exe or uv.exe |
| Network errors | Add retry logic with exponential backoff |
| Permission denied on output | Ensure output directory writable by task user |
| Timezone issues | Set explicit timezone in cron config or use UTC consistently |
| Feed returns 304 | Handle Not Modified - use cached data |

## Dependencies

```toml
# pyproject.toml or requirements.txt
requests>=2.31.0
defusedxml>=0.7.1
python-dateutil>=2.8.2
```