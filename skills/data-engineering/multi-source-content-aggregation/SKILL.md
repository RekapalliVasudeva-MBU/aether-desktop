---
name: multi-source-content-aggregation
description: Automated content aggregation from multiple APIs (arXiv, Hacker News, RSS feeds, etc.) into curated digests. Covers fetching, filtering, deduplication, and markdown compilation.
category: data-engineering
tags: [api, aggregation, cron, digest, arxiv, hacker-news, rss, markdown]
version: 1.0.0
---

# Multi-Source Content Aggregation

Automated workflow for fetching content from multiple APIs, filtering for relevance, and compiling into structured markdown digests. Designed for recurring cron jobs.

## Trigger Conditions

- Scheduled digest generation (daily/weekly)
- Need to aggregate from 2+ heterogeneous sources (academic, social, news)
- Output must be a curated, human-readable markdown report

## Core Workflow

### 1. Source Configuration

Define sources in a config structure:

```python
SOURCES = {
    "arxiv": {
        "url": "http://export.arxiv.org/api/query",
        "params": {
            "search_query": "all:RAG OR all:vector database OR all:graph RAG",
            "max_results": 30,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        },
        "parser": "atom_xml",
        "filter_keywords": ["rag", "retrieval augmented", "vector database", "graph rag", "embedding", "rerank", "faiss", "milvus", "pinecone", "weaviate", "qdrant", "chroma"]
    },
    "hacker_news": {
        "url": "https://hn.algolia.com/api/v1/search",
        "params": {
            "query": "RAG OR \"retrieval augmented generation\" OR \"vector database\"",
            "tags": "story",
            "hitsPerPage": 20
        },
        "parser": "json",
        "filter_keywords": []  # API already filters
    },
    "ars_technica": {
        "url": "https://arstechnica.com/feed/",
        "parser": "rss_xml",
        "filter_keywords": ["ai", "ml", "machine learning", "llm", "rag", "retrieval", "vector", "neural", "gpt", "llama", "openai", "anthropic", "transformer", "generative"]
    }
}
```

### 2. Fetching Patterns

**arXiv (Atom XML):**
```bash
curl -s "http://export.arxiv.org/api/query?search_query=all:RAG+OR+all:vector+database&max_results=30&sortBy=submittedDate&sortOrder=descending" > arxiv.xml
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('arxiv.xml')
ns = {'atom': 'http://www.w3.org/2005/Atom'}
for entry in tree.findall('.//atom:entry', ns):
    title = entry.find('atom:title', ns).text.strip()
    link = entry.find('atom:link[@rel=\"alternate\"]', ns).get('href')
    summary = entry.find('atom:summary', ns).text.strip()
    published = entry.find('atom:published', ns).text[:10]
    authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
    # filter by keywords in title+summary
"
```

**Hacker News (Algolia JSON):**
```bash
curl -s "https://hn.algolia.com/api/v1/search?query=RAG&tags=story&hitsPerPage=20" | jq '.hits[] | {title, url, points, author, created_at}'
```

**RSS Feeds (XML):**
```bash
curl -s "https://arstechnica.com/feed/" | python3 -c "
import xml.etree.ElementTree as ET, sys
root = ET.fromstring(sys.stdin.read())
for item in root.findall('.//item'):
    title = item.find('title').text
    link = item.find('link').text
    pub = item.find('pubDate').text
    desc = item.find('description').text
    # filter by keywords in title+desc+content
"
```

### 3. Filtering & Deduplication

- **Keyword filtering**: Case-insensitive substring match on title + summary + content
- **Date filtering**: Keep only last N days (for cron, typically last 24-48h)
- **Deduplication**: By URL or title similarity (fuzzy match threshold ~0.85)
- **Relevance scoring**: Boost score for keyword matches in title vs body

### 4. Markdown Compilation

```markdown
# Digest Title - YYYY-MM-DD

Generated: ISO_TIMESTAMP

## Source 1 Name (count items)

### Item Title
**Link:** URL
**Date:** YYYY-MM-DD
**Authors/Author:** Names
**Summary:** Truncated summary...

## Source 2 Name (count items)

- [Title](URL) (points, by author)
```

## Pitfalls & Fixes

| Pitfall | Fix |
|---------|-----|
| arXiv API returns 1M+ results for broad queries | Use specific phrase queries: `all:\"retrieval augmented generation\"` not `all:RAG` |
| HN Algolia returns old stories | Sort by `created_at_i` desc, filter by date |
| RSS feeds truncate descriptions | Use `<content:encoded>` for full content |
| XML namespaces break parsing | Always declare namespace dict: `ns = {'atom': 'http://www.w3.org/2005/Atom'}` |
| Cron environment lacks Python packages | Use `python3 -c` inline scripts; avoid imports not in stdlib |
| Rate limits | Add `time.sleep(1)` between sources; cache responses |

## Verification Checklist

- [ ] All sources fetched successfully (check HTTP 200)
- [ ] At least N items per source after filtering
- [ ] Output markdown renders correctly
- [ ] File written to configured output path
- [ ] No duplicate titles/URLs across sources

## Related References

- `references/arxiv-api-guide.md` — arXiv API query syntax and Atom parsing
- `references/hn-algolia-guide.md` — Hacker News Algolia API parameters
- `references/ars-technica-rss-guide.md` — Ars Technica RSS feed structure and filtering
- `scripts/daily_digest_workflow.md` — Complete daily digest generation workflow with code templates