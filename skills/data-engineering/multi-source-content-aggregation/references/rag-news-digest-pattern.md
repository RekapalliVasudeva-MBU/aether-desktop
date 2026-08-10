# RAG News Digest Pattern

Concrete example of the multi-source-content-aggregation skill for daily RAG/vector database news.

## Cron Job Configuration

```bash
hermes cronjob create \
  --name "Daily RAG News Digest" \
  --schedule "0 8 * * *" \
  --prompt "Generate the daily RAG news digest by fetching latest arXiv papers on RAG/vector databases/graph RAG, Hacker News stories on RAG, and Ars Technica AI/ML articles. Save to C:/Users/valte/RAG-lecture/RAG_News_Digest_YYYY-MM-DD.md" \
  --script "C:/Users/valte/RAG-lecture/generate_rag_digest.py"
```

Or as a Python inline script (used in this session):

```python
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
output_file = f'RAG-lecture/RAG_News_Digest_{today}.md'

# 1. arXiv - specific phrase queries to avoid 1M+ results
arxiv_url = 'http://export.arxiv.org/api/query'
params = {
    'search_query': 'all:"retrieval augmented generation" OR all:"RAG" OR all:"vector database" OR all:"graph RAG"',
    'start': 0,
    'max_results': 20,
    'sortBy': 'submittedDate',
    'sortOrder': 'descending'
}
arxiv_resp = requests.get(arxiv_url, params=params)

# Parse Atom XML with namespace
root = ET.fromstring(arxiv_resp.text)
ns = {'atom': 'http://www.w3.org/2005/Atom'}
papers = []
for entry in root.findall('atom:entry', ns):
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
    summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')[:300]
    link = entry.find('atom:id', ns).text
    published = entry.find('atom:published', ns).text
    authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
    papers.append({'title': title, 'summary': summary, 'link': link, 'published': published, 'authors': authors})

# 2. Hacker News - Algolia API
hn_url = 'https://hn.algolia.com/api/v1/search'
hn_params = {'query': 'RAG OR "retrieval augmented generation" OR "vector database"', 'tags': 'story', 'hitsPerPage': 15}
hn_resp = requests.get(hn_url, params=hn_params)
hn_data = hn_resp.json()

# 3. Ars Technica RSS
ars_url = 'https://feeds.arstechnica.com/arstechnica/technology-lab'
ars_resp = requests.get(ars_url)
ars_root = ET.fromstring(ars_resp.content)
ars_items = []
for item in ars_root.findall('.//item')[:15]:
    title = item.find('title').text if item.find('title') is not None else ''
    link = item.find('link').text if item.find('link') is not None else ''
    desc = item.find('description').text if item.find('description') is not None else ''
    pub = item.find('pubDate').text if item.find('pubDate') is not None else ''
    if any(kw in title.lower() for kw in ['rag', 'retrieval', 'vector', 'embedding', 'llm', 'ai', 'machine learning']):
        ars_items.append({'title': title, 'link': link, 'desc': desc[:200], 'pub': pub})

# 4. Write markdown digest
with open(output_file, 'w') as f:
    f.write(f'# RAG News Digest - {today}\n\n')
    f.write(f'Generated: {datetime.now().isoformat()}\n\n')
    
    f.write('## arXiv Latest Papers (last 20)\n\n')
    for p in papers:
        f.write(f'### {p["title"]}\n')
        f.write(f'**Authors:** {", ".join(p["authors"])}  \n')
        f.write(f'**Published:** {p["published"][:10]}  \n')
        f.write(f'**Link:** {p["link"]}  \n')
        f.write(f'**Abstract:** {p["summary"]}...  \n\n')
    
    f.write('## Hacker News (RAG/Vector DB related)\n\n')
    for hit in hn_data.get('hits', [])[:15]:
        title = hit.get('title', '')
        url = hit.get('url', '')
        points = hit.get('points', 0)
        author = hit.get('author', '')
        if url:
            f.write(f'- [{title}]({url}) ({points} points, by {author})\n')
    
    f.write('\n## Ars Technica (AI/ML/RAG related)\n\n')
    for item in ars_items[:10]:
        f.write(f'- [{item["title"]}]({item["link"]}) ({item["pub"]})\n')
        f.write(f'  {item["desc"]}...\n\n')

print(f'Written to {output_file}')
```

## Key Patterns Learned

1. **arXiv query syntax**: Use `all:"exact phrase"` for specific terms, not broad `all:RAG` which returns millions
2. **HN Algolia**: Filter by `tags=story` and sort by date implicitly
3. **RSS filtering**: Check title + description for keywords since RSS doesn't support query params
4. **Namespace handling**: Always declare `ns = {'atom': 'http://www.w3.org/2005/Atom'}` for arXiv
5. **Cron compatibility**: Inline Python script with only stdlib + requests (avoid import issues in cron env)

## Output Structure

```
RAG-lecture/
  RAG_News_Digest_2026-07-26.md
  RAG_News_Digest_2026-07-27.md
  ...
```

Each file contains:
- arXiv papers (20 latest, filtered by RAG keywords)
- Hacker News stories (15, with points/author)
- Ars Technica articles (10, AI/ML filtered)

## Verification

```bash
# Check latest digest
cat RAG-lecture/RAG_News_Digest_$(date +%F).md | head -30

# List all digests
ls -la RAG-lecture/RAG_News_Digest_*.md
```