# Hacker News Algolia API Guide

## Base URL
`https://hn.algolia.com/api/v1/search`

## Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `query` | Search query (supports Algolia syntax) | `RAG OR "retrieval augmented generation"` |
| `tags` | Filter by tag: `story`, `comment`, `show_hn`, `ask_hn`, `poll` | `story` |
| `hitsPerPage` | Results per page (max 1000) | `20` |
| `page` | Page number (0-indexed) | `0` |
| `numericFilters` | Filter by numeric attributes | `points>10`, `created_at_i>1704067200` |
| `facetFilters` | Filter by facet values | `(author:user1)` |
| `attributesToRetrieve` | Fields to return | `title,url,points,author,created_at_i` |
| `attributesToHighlight` | Fields to highlight | `title,story_text` |

## Algolia Query Syntax

| Syntax | Meaning |
|--------|---------|
| `term1 term2` | AND (both terms) |
| `term1 OR term2` | OR (either term) |
| `"exact phrase"` | Exact phrase match |
| `-term` | Exclude term |
| `prefix*` | Prefix match |

## Response Format (JSON)

```json
{
  "hits": [
    {
      "objectID": "42299349",
      "title": "I looked at 1000s of RAG queries...",
      "url": "https://example.com",
      "author": "npip99",
      "points": 6,
      "num_comments": 3,
      "created_at": "2024-12-02T19:12:31Z",
      "created_at_i": 1733166751,
      "story_text": "Full story text...",
      "_highlightResult": {
        "title": { "value": "I looked at 1000s of <em>RAG</em> queries...", "matchedWords": ["rag"] }
      }
    }
  ],
  "nbHits": 150,
  "page": 0,
  "hitsPerPage": 20,
  "processingTimeMS": 5
}
```

## Common Filters for Recency

```bash
# Last 24 hours (Unix timestamp)
created_at_i>$(date -d '1 day ago' +%s)

# Last 7 days
created_at_i>$(date -d '7 days ago' +%s)

# Minimum points
points>5
```

## curl Examples

```bash
# Basic RAG search
curl -s "https://hn.algolia.com/api/v1/search?query=RAG%20OR%20%22retrieval%20augmented%20generation%22%20OR%20%22vector%20database%22&tags=story&hitsPerPage=20"

# Recent high-score RAG stories
curl -s "https://hn.algolia.com/api/v1/search?query=RAG&tags=story&hitsPerPage=20&numericFilters=created_at_i>1704067200,points>10"
```

## Python Processing

```python
import requests, json
from datetime import datetime, timedelta

url = "https://hn.algolia.com/api/v1/search"
params = {
    "query": "RAG OR \"retrieval augmented generation\" OR \"vector database\"",
    "tags": "story",
    "hitsPerPage": 20
}
resp = requests.get(url, params=params, timeout=30)
data = resp.json()

for hit in data.get("hits", []):
    if hit.get("url"):  # Only stories with links
        title = hit["title"]
        url = hit["url"]
        points = hit["points"]
        author = hit["author"]
        created = datetime.fromtimestamp(hit["created_at_i"]).strftime("%Y-%m-%d")
        print(f"- [{title}]({url}) ({points} points, by {author})")
```