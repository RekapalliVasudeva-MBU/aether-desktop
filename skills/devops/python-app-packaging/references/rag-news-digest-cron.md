# Daily RAG News Digest Cron Job

## Setup
Created cron job `c7ddb27b585e` - "Daily RAG News Digest"
- Schedule: `0 8 * * *` (daily at 8 AM)
- Runs as: `no_agent=True` script (script only, no LLM tokens)
- Output: Saves to `C:\Users\valte\RAG-lecture\RAG_News_Digest_YYYY-MM-DD.md`

## Sources Queried
1. **arXiv** - Latest papers on RAG, vector databases, graph RAG (20 papers, sorted by submission date)
2. **Hacker News** - Algolia search for RAG/vector DB stories (15 results)
3. **Ars Technica** - Technology Lab RSS feed, filtered for AI/ML/RAG keywords

## Script
```python
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
output_file = f'RAG-lecture/RAG_News_Digest_{today}.md'

# arXiv search
arxiv_url = 'http://export.arxiv.org/api/query'
params = {
    'search_query': 'all:"retrieval augmented generation" OR all:"RAG" OR all:"vector database" OR all:"graph RAG"',
    'start': 0,
    'max_results': 20,
    'sortBy': 'submittedDate',
    'sortOrder': 'descending'
}
arxiv_resp = requests.get(arxiv_url, params=params)

# Parse arXiv XML
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

# Hacker News
hn_url = 'https://hn.algolia.com/api/v1/search'
hn_params = {'query': 'RAG OR "retrieval augmented generation" OR "vector database"', 'tags': 'story', 'hitsPerPage': 15}
hn_resp = requests.get(hn_url, params=hn_params)
hn_data = hn_resp.json()

# Ars Technica RSS
ars_url = 'https://feeds.arstechnica.com/arstechnica/technology-lab'
ars_resp = requests.get(ars_url)
ars_root = ET.fromstring(ars_resp.content)
ars_items = []
for item in ars_root.findall('.//item')[:15]:
    title = item.find('title').text if item.find('title') is not None else ''
    link = item.find('link').text if item.find('link') is not None else ''
    desc = item.find('description').text if item.find('description') is not None else ''
    pub = item.find('pubDate').text if item.find('pubDate') is not None else ''
    if any(kw in title.lower() for kw in ['rag', 'retrieval', 'vector', 'embedding', 'llm', 'ai']):
        ars_items.append({'title': title, 'link': link, 'desc': desc[:200], 'pub': pub})

# Write digest
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

## Today's Digest (2026-07-26)
- File: `C:\Users\valte\RAG-lecture\RAG_News_Digest_2026-07-26.md` (16 KB)
- Contains 20 arXiv papers (July 20-26) including GRADRAG, CRAG-MM-Diagnostics, Vector Search As Nearest Neighbor Matching, Testing RAG Systems with Chunk Coverage
- Hacker News: AnythingLLM (368 pts), Devv.ai (185 pts), memvid (61 pts)
- Ars Technica: Energy IPOs surge, Hackers using AI tools for botnets

## Verification
```bash
# Manual test run
cronjob action=run job_id=c7ddb27b585e
# Result: execution_success=true, last_status=ok
```