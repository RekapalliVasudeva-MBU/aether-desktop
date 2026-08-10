# arXiv API Guide

## Base URL
`http://export.arxiv.org/api/query`

## Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `search_query` | Search query using arXiv syntax | `all:"retrieval augmented generation"` |
| `start` | Starting index (0-based) | `0` |
| `max_results` | Max results to return (max 2000) | `30` |
| `sortBy` | Sort field: `relevance`, `lastUpdatedDate`, `submittedDate` | `submittedDate` |
| `sortOrder` | Sort direction: `ascending`, `descending` | `descending` |

## Search Query Syntax

| Field | Prefix | Example |
|-------|--------|---------|
| All fields | `all:` | `all:RAG` |
| Title | `ti:` | `ti:"vector database"` |
| Abstract | `abs:` | `abs:retrieval` |
| Authors | `au:` | `au:Smith` |
| Category | `cat:` | `cat:cs.CL` |
| Date range | `submittedDate:[YEARMMDD TO YEARMMDD]` | `submittedDate:[20240101 TO 20241231]` |

**Boolean operators:** `AND`, `OR`, `NOT` (must be uppercase)
**Phrase search:** Use quotes `"retrieval augmented generation"`
**Grouping:** Use parentheses `(A OR B) AND C`

## Example Queries

```bash
# RAG-related papers (specific phrases)
all:"retrieval augmented generation" OR all:"vector database" OR all:"graph RAG" OR all:"dense retrieval" OR all:rerank

# Broader ML/AI
all:RAG OR all:"retrieval-augmented generation" OR all:"vector store" OR all:faiss OR all:milvus OR all:pinecone
```

## Response Format (Atom XML)

```xml
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2607.12345v1</id>
    <title>Paper Title</title>
    <summary>Abstract text...</summary>
    <published>2026-07-23T17:59:58Z</published>
    <updated>2026-07-23T17:59:58Z</updated>
    <link href="https://arxiv.org/abs/2607.12345v1" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2607.12345v1" rel="related" type="application/pdf" title="pdf"/>
    <author><name>Author Name</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
```

## Python Parsing Template

```python
import xml.etree.ElementTree as ET

ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}

tree = ET.parse('response.xml')
root = tree.getroot()

for entry in root.findall('.//atom:entry', ns):
    paper_id = entry.find('atom:id', ns).text
    title = entry.find('atom:title', ns).text.strip()
    summary = entry.find('atom:summary', ns).text.strip()
    published = entry.find('atom:published', ns).text[:10]  # YYYY-MM-DD
    link = entry.find('atom:link[@rel="alternate"]', ns).get('href')
    pdf_link = entry.find('atom:link[@rel="related"]', ns).get('href')
    authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
    primary_cat = entry.find('arxiv:primary_category', ns).get('term')
```