# Ars Technica RSS Feed Guide

## Feed URLs

| Feed | URL |
|------|-----|
| Main (all) | `https://arstechnica.com/feed/` |
| AI/ML section | `https://arstechnica.com/ai/feed/` |
| Science | `https://arstechnica.com/science/feed/` |
| Tech Policy | `https://arstechnica.com/tech-policy/feed/` |
| Gadgets | `https://arstechnica.com/gadgets/feed/` |

## RSS Structure (XML)

```xml
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Ars Technica</title>
    <link>https://arstechnica.com</link>
    <description>Serving the Technologist since 1998</description>
    <lastBuildDate>Sat, 25 Jul 2026 20:52:30 +0000</lastBuildDate>
    <item>
      <title>Article Title</title>
      <link>https://arstechnica.com/ai/2026/07/article-slug/</link>
      <comments>https://arstechnica.com/ai/2026/07/article-slug/#comments</comments>
      <dc:creator>Author Name</dc:creator>
      <pubDate>Sat, 25 Jul 2026 20:52:30 +0000</pubDate>
      <category>AI</category>
      <guid isPermaLink="true">https://arstechnica.com/ai/2026/07/article-slug/</guid>
      <description><![CDATA[Short description/excerpt]]></description>
      <content:encoded><![CDATA[Full HTML content]]></content:encoded>
    </item>
  </channel>
</rss>
```

## Key Fields

| Field | XPath | Description |
|-------|-------|-------------|
| Title | `item/title` | Article headline |
| URL | `item/link` | Permalink |
| Author | `item/dc:creator` | Author name (in DC namespace) |
| PubDate | `item/pubDate` | RFC 2822 date format |
| Categories | `item/category` | Multiple tags (section, topics) |
| Description | `item/description` | Short teaser (CDATA) |
| Full Content | `item/content:encoded` | Full article HTML (CDATA) |
| Comments Count | `item/slash:comments` | Number of comments |

## Namespaces Required

```python
ns = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'slash': 'http://purl.org/rss/1.0/modules/slash/',
    'media': 'http://search.yahoo.com/mrss/'
}
```

## Python Parsing Template

```python
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# SECURITY: Use defusedxml to prevent XXE/billion-laughs attacks
# pip install defusedxml
from defusedxml.ElementTree import fromstring, parse

ns = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'slash': 'http://purl.org/rss/1.0/modules/slash/',
    'media': 'http://search.yahoo.com/mrss/'
}

def fetch_ars_feed(feed_url, timeout=30):
    """Fetch and parse Ars Technica RSS feed."""
    resp = requests.get(feed_url, timeout=timeout)
    resp.raise_for_status()
    # Use defusedxml for safe parsing
    root = fromstring(resp.content)
    return root

def parse_ars_items(root, keywords=None, max_items=20):
    """Parse items from RSS feed root element."""
    items = []
    for item in root.findall('.//item')[:max_items]:
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else ''
        pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
        
        # Parse RFC 2822 date
        pub_date = None
        if pub_date_str:
            try:
                pub_date = parsedate_to_datetime(pub_date_str)
            except Exception:
                pass
        
        # Author (dc:creator)
        creator = item.find('dc:creator', ns)
        author = creator.text if creator is not None else ''
        
        # Categories
        categories = [cat.text for cat in item.findall('category')]
        
        # Description (teaser)
        desc_elem = item.find('description')
        description = desc_elem.text if desc_elem is not None else ''
        
        # Full content
        content_elem = item.find('content:encoded', ns)
        full_content = content_elem.text if content_elem is not None else ''
        
        # Combined text for filtering
        full_text = f"{title} {description} {full_content}".lower()
        
        # Filter for AI/ML/RAG topics
        if keywords and not any(kw in full_text for kw in keywords):
            continue
        
        items.append({
            'title': title,
            'link': link,
            'pub_date': pub_date,
            'pub_date_str': pub_date_str,
            'author': author,
            'categories': categories,
            'description': description[:300],
            'full_content': full_content
        })
    
    return items

# AI/ML/RAG keywords
AI_KEYWORDS = [
    'ai', 'ml', 'machine learning', 'llm', 'large language model',
    'rag', 'retrieval augmented generation', 'retrieval-augmented',
    'vector database', 'vector store', 'embedding', 'embeddings',
    'gpt', 'llama', 'claude', 'openai', 'anthropic', 'mistral',
    'transformer', 'attention', 'fine-tuning', 'rlhf',
    'generative', 'diffusion', 'stable diffusion',
    'semantic search', 'similarity search', 'nearest neighbor',
    'pinecone', 'weaviate', 'milvus', 'qdrant', 'chroma', 'faiss',
    'langchain', 'llamaindex', 'haystack',
    'chatbot', 'agent', 'copilot', 'assistant',
    'artificial intelligence'
]

# Fetch from AI section + main feed
def fetch_ars_technica_articles(max_items=15):
    """Fetch AI-relevant articles from Ars Technica."""
    all_items = []
    seen_links = set()
    
    for feed_url in ['https://arstechnica.com/ai/feed/', 'https://arstechnica.com/feed/']:
        try:
            root = fetch_ars_feed(feed_url)
            items = parse_ars_items(root, keywords=AI_KEYWORDS, max_items=max_items)
            for item in items:
                if item['link'] not in seen_links:
                    seen_links.add(item['link'])
                    all_items.append(item)
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
    
    # Sort by pub_date (newest first)
    all_items.sort(key=lambda x: x['pub_date'] or '', reverse=True)
    return all_items[:max_items]
```

## Date Parsing

```python
from email.utils import parsedate_to_datetime

# RSS pubDate format: "Sat, 25 Jul 2026 20:52:30 +0000"
dt = parsedate_to_datetime("Sat, 25 Jul 2026 20:52:30 +0000")
# Returns timezone-aware datetime
iso_date = dt.isoformat()
date_str = dt.strftime("%Y-%m-%d")
```

## Filtering Tips

1. **Use the AI section feed** (`/ai/feed/`) as primary source - higher signal-to-noise
2. **Cross-check main feed** for AI articles that might be categorized differently
3. **Filter by content:encoded** - contains full article text, better for keyword matching
4. **Deduplicate by link** - same article may appear in multiple feeds
5. **Limit to last 24-48 hours** by parsing pubDate and comparing to now

## Rate Limiting & Etiquette

- Feed updates hourly (`<sy:updatePeriod>hourly</sy:updatePeriod>`)
- Poll no more than once per hour
- Use conditional requests with `If-Modified-Since` / `ETag` headers
- Cache responses for at least 1 hour

```python
import requests

headers = {}
if last_modified:
    headers['If-Modified-Since'] = last_modified
if etag:
    headers['If-None-Match'] = etag

response = requests.get('https://arstechnica.com/feed/', headers=headers)
if response.status_code == 304:
    # Not modified, use cached
    pass
```

## Common Issues

| Issue | Solution |
|-------|----------|
| CDATA in description/content | Use `.text` directly - ElementTree handles CDATA |
| HTML in content:encoded | Strip tags with `re.sub(r'<[^>]+>', '', content)` or use `html2text` |
| Namespaces missing | Always declare `ns` dict and pass to `find/findall` |
| Date format variations | Use `email.utils.parsedate_to_datetime` for RFC 2822 |
| Feed truncation | Some feeds limit to 10-20 items; use paginated archives if needed |
| XXE/Billion-laughs attacks | **Use `defusedxml.ElementTree` instead of stdlib** |