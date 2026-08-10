# YouTube Transcript Extraction — Quick Reference

## Install

```bash
python3 -m pip install youtube-transcript-api
```

## Fetch Transcript (Correct API for v1.x)

```python
from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
t = api.fetch('VIDEO_ID')

for line in t:
    seconds = int(line.start)
    print(f"[{seconds//60}:{seconds%60:02d}] {line.text}")
```

## Pitfall: Wrong Method Names

These do **NOT** exist in the current version:
- ❌ `YouTubeTranscriptApi.get_transcript('VIDEO_ID')`
- ❌ `YouTubeTranscriptApi.fetch('VIDEO_ID')` (class method — needs instance)

Correct pattern:
- ✅ `api = YouTubeTranscriptApi()` then `api.fetch('VIDEO_ID')`

## Fetch by Timestamp Range

```python
from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
t = api.fetch('VIDEO_ID')

# Only lines after 12 minutes
for line in t:
    if line.start >= 720:
        print(f"[{int(line.start)//60}:{int(line.start)%60:02d}] {line.text}")
```

## Fallback: timedtext API (no package needed)

```bash
curl -sL "https://www.youtube.com/api/timedtext?v=VIDEO_ID&lang=en&fmt=json3" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for e in data.get('events', []):
    for seg in e.get('segs', []):
        text = seg.get('utf8', '').strip()
        if text:
            print(f\"[{e.get('tStartMs',0)//1000}s] {text}\")
"
```

## Get Video Metadata (no API key)

```bash
curl -sL "https://www.youtube.com/watch?v=VIDEO_ID" | python3 -c "
import sys, re
html = sys.stdin.read()
title = re.search(r'\"title\":\"([^\"]+)\"', html)
length = re.search(r'\"lengthSeconds\":\"(\d+)\"', html)
if title: print('Title:', title.group(1))
if length: print('Duration:', int(length.group(1))//60, 'min', int(length.group(1))%60, 'sec')
"
```
