# Windows Localhost HTTP Server Workarounds

## Problem
`python -m http.server` started via Hermes `terminal()` on Windows exits immediately or returns empty responses.

## Solutions

### Python wrapper (most reliable)
Create `serve.py`:
```python
import http.server,os,threading,time
PORT,DIR=8081,os.path.dirname(os.path.abspath(__file__))
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=DIR,**kw)
threading.Thread(target=lambda:http.server.HTTPServer(("127.0.0.1",PORT),H).serve_forever(),daemon=True).start();time.sleep(999)
```
Start: `cmd /c "start /MIN pythonw C:\path\serve.py"`

### file:// protocol (no server needed)
`browser_navigate(url="file:///C:/Users/valte/project/index.html")` — works for single HTML files.

### Verify
`curl -s http://127.0.0.1:8081/index.html | head -3`
