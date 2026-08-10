# AI News Processor for AI/ML Engineering

**Author**: Hermes Agent  
**Date**: 2026-07-07  
**Purpose**: Terminal-based AI news aggregation from multiple sources with filtering for AI/ML engineering relevance

## Overview

When you need to collect the latest AI news without browser tools (as per Hermes constraints), use this pattern: combine curl for source fetching + Python for parsing + relevance filtering + ranking.

## Files This Workflow Produces

For this conversation, the workflow created:
- `ai_news_processor.py` - Main script (located in project workspace)
- `arstechnica.html`, `hn.html`, `verge.html` - Cached source HTML files

## Key Techniques Demonstrated

### 1. Multi-Source Intelligence Gathering
- **Ars Technica AI**: Custom HTML extraction with direct article parsing
- **Hacker News**: BeautifulSoup parsing of submissions with metadata
- **The Verge AI**: Section-specific article extraction

### 2. AI Relevance Filtering
```python
def is_ai_relevant(text):
    ai_keywords = [
        'ai', 'artificial intelligence', 'llm', 'language model',
        'gpt', 'chatgpt', 'claude', 'gemini', 'copilot',
        'openai', 'anthropic', 'rag', 'machine learning',
        'deep learning', 'neural network', 'transformer',
        'embedding', 'prompt', 'agent'
    ]
    return any(keyword in text.lower() for keyword in ai_keywords)
```

### 3. Intelligence Scoring & Ranking System
```python
def get_importance_score(headline):
    score = 0
    title_lower = headline['title'].lower()
    
    # Model releases + major companies = high priority
    if any(term in title_lower for term in ['gpt', 'openai', 'claude', 'gemini', 'copilot']):
        score += 10
    if any(term in title_lower for term in ['anthropic', 'google', 'microsoft']):
        score += 8
    
    # Technical content from papers/repos
    if 'arxiv' in headline['url'] or 'github' in headline['url']:
        score += 5
    
    # Engineering-focused content
    if headline['source'] == 'Hacker News' and ('rag' in title_lower or 'embedding' in title_lower):
        score += 7
        
    return score
```

### 4. Production-Ready Output Format
- Clean numbered list presentation
- 1-2 line summaries for quick scanning
- "Why it matters for AI/ML engineer" insights
- Source URLs for drill-down

## Best Practices Captured

- **Always cache source HTML** for reproducibility
- **User-Agent matters** – some sites return minimal content with generic tool strings
- **Rate limiting** – don't hit endpoints repeatedly (though this is just demo data)
- **Multiple parsing fallbacks** – different sites need different selectors
- **Intelligence first, raw data second** – relevance filtering beats volume

## Use Cases

- Daily briefing compilation for AI teams
- Feature tracking for AI/ML engineers
- Competitor monitoring in AI space
- Research brief preparation
- Technical trend analysis

**Note**: RSS feed patterns can change over time - monitor and update feed URLs regularly. For production use, set up cron jobs to run this daily with new source files.