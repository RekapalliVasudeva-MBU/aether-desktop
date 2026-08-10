---
name: python-dev-companion
description: Python development best practices, code review checklist, and project conventions. Use when writing, reviewing, or refactoring Python code (FastAPI, PyTorch, sklearn, data science). Enforces code quality, security, and maintainability standards.
---

BE DIRECT: focus on getting results done, not on explaining process.

## When to Activate

- Writing new Python code or refactoring existing code
- Reviewing pull requests or code changes
- Building FastAPI endpoints or PyTorch models
- Setting up a new Python project
- Before marking any coding task complete

## Code Quality Checklist (Confidence-Gated)

### Pre-Report Gate for Every Finding
Before flagging ANY issue, answer ALL four — if any answer is "no", DROP it:
1. Can I cite the exact file and line? (No vague "somewhere in auth")
2. Can I describe the concrete failure mode? (Input → state → bad outcome)
3. Have I read surrounding context? (Callers, imports, tests)
4. Is the severity defensible? (Missing docs ≠ HIGH. Single `any` in test ≠ CRITICAL.)

### Review Order: CRITICAL → HIGH → MEDIUM → LOW

**CRITICAL** (must fix, include snippet + line + failure scenario):
- Hardcoded secrets, API keys, passwords
- SQL injection, command injection, eval() on user input
- Authentication bypass, missing auth on protected routes
- Privilege escalation paths

**HIGH** (should fix):
- Missing error handling on I/O and external calls
- Mutable default arguments (`def f(x=[])`)
- Bare `except:` or `except Exception:` without logging
- Incorrect path traversal / file access
- Missing input validation on API endpoints

**MEDIUM** (nice to fix):
- Missing type hints on public functions
- Functions > 50 lines that could be split
- Missing docstrings on public APIs
- Code duplication across files
- Using `type(x) == list` instead of `isinstance(x, list)`

**LOW** (suggestion only):
- Variable naming improvements
- Import ordering
- Minor style inconsistencies

## Language-Specific Patterns

### Python Core
- **EAFP over LBYL**: Try/except preferred over if-checks for dict access, file ops
- **Explicit is better than implicit**: No hidden side effects in imports
- **Use `is`/`is not` for None**, not `==`
- **Use `isinstance()` for type checks**, not `type()`
- **f-strings** for formatting, `pathlib.Path` for paths
- **Generators** for large data — never load everything into memory
- **`__slots__`** for data classes with many instances

### Type Hints (Python 3.9+)
```python
# Built-in generics — no typing import needed
def process(items: list[str]) -> dict[str, int]: ...

# Optional
from typing import Optional
def find(user_id: str) -> User | None: ...
```

### Error Hierarchy
```python
class AppError(Exception): pass
class ValidationError(AppError): pass
class NotFoundError(AppError): pass
```

### FastAPI Patterns
- `main.py` → app construction, middleware, router registration
- `schemas/` → Pydantic request/response models
- `dependencies.py` → DB, auth, pagination
- `services/` or `crud/` → business logic
- Use `create_app()` factory for testability
- Always declare `response_model` on routes
- Never return raw ORM objects in responses
- Use async for I/O-bound endpoints
- Override dependencies in tests, don't open production resources

### PyTorch Patterns
- **Device-agnostic**: `device = torch.device("cuda" if torch.cuda.is_available() else "cpu")`
- **Reproducibility**: Set all seeds (torch, numpy, random) + `cudnn.deterministic = True`
- **Shape annotations**: Comment tensor shapes in forward pass
- **Clean nn.Module**: Clear `__init__`/`forward`, no magic
- Use `DataLoader` with `num_workers` for data pipeline
- Save checkpoints: model state + optimizer state + epoch

## Security Scan Patterns

### OWASP Top 10 Quick Check
1. **Injection** — User input in queries? Use ORM/parameterized queries
2. **Broken Auth** — Passwords hashed (bcrypt/argon2)? JWT validated?
3. **Sensitive Data** — HTTPS? Secrets in env vars? PII encrypted?
4. **Broken Access** — Auth checked on every route? CORS configured?
5. **XSS** — Output escaped? CSP set?
6. **Misconfiguration** — Debug off in prod? Security headers set?
7. **Known Vulns** — `pip-audit` clean? Dependencies updated?

### Secrets Detection
Scan for these patterns in code:
- `api_key = "sk-..."` (hardcoded)
- `password = "..."` (hardcoded)
- `token = "..."` (hardcoded)
- `.env` files in repo (check `.gitignore`)

### Commands
```bash
# Security
bandit -r .
pip-audit

# Linting + Formatting
ruff check .
black .
isort .

# Type checking
mypy .

# Testing
pytest --cov=. --cov-report=term-missing
```

## Project Layout (pyproject.toml)
```toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.9"

[project.optional-dependencies]
dev = ["pytest>=7.4", "black>=23.0", "ruff>=0.1.0", "mypy>=1.5.0"]

[tool.black]
line-length = 88
target-version = ['py39']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.9"
disallow_untyped_defs = true
warn_return_any = true
```

## Anti-Patterns (Flag Immediately)

```python
# Mutable default arguments
def f(x=[]): ...           # BUG: shared list

# Bare except
try: ... except: ...       # Hides all errors

# Wrong None check
if x == None: ...          # Use `is None`

# Wrong type check
if type(x) == list: ...    # Use isinstance(x, list)

# Silent failure
try: ... except: pass      # Never do this

# Hardcoded secrets
API_KEY = "sk-..."         # Use os.environ or .env

# from module import *
from os import *           # Explicit imports only
```

## Vector Search / RAG Tools

### turbovec (Recommended for RAG)
- **Install:** `pip install turbovec` (also on PyPI as `turbovec[langchain]`)
- **What:** Rust-based vector index using Google's TurboQuant (ICLR 2026). 16x less RAM than float32, faster than FAISS.
- **API:**
  ```python
  from turbovec import TurboQuantIndex
  index = TurboQuantIndex(dim=1536, bit_width=4)
  index.add(vectors)  # np.float32 array, shape (n, dim)
  scores, indices = index.search(query, k=10)  # query shape (1, dim)
  index.write("index.tv")  # persist to disk
  loaded = TurboQuantIndex.load("index.tv")
  ```
- **IdMapIndex** (custom uint64 IDs):
  ```python
  from turbovec import IdMapIndex
  idx = IdMapIndex(dim=1536, bit_width=4)
  idx.add_with_ids(vectors, np.arange(n, dtype=np.uint64))
  scores, ids = idx.search(query, k=10)
  ```
- **Filtered search:** Pass `allowlist=np.array([...], dtype=np.uint64)` to `search()` for hybrid retrieval
- **Windows note:** Use `C:/Users/valte/` paths, not `/tmp/` for persistence
- **When to use:** Building RAG systems, especially memory-constrained or latency-sensitive deployments
- **Alternatives:** FAISS (heavier), ChromaDB (managed service), simple grep (surprisingly effective for small corpora per arXiv:2605.15184)

## Behavior Rules (ECC-Inspired)

Apply these to all coding work:
- Run tests before marking task complete
- Never create files outside the project directory
- Ask before deleting any file
- Explain reasoning before writing code
- If unsure, ask — don't guess
- Only report issues you're >80% confident are real problems
