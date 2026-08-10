# Docker on Windows — Integration Guide

## Checking Docker Status

```bash
docker ps              # list running containers
docker info            # daemon status, storage driver, OS type
docker images          # local images
docker version         # client + server version
```

## What Hermes + Docker Can Do

### 1. Kanban Workers in Containers
Run isolated Kanban worker profiles inside Docker containers for sandboxed execution.

### 2. Deploy ML Models / FastAPI Apps
Package FastAPI + PyTorch apps into containers:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t my-ml-app .
docker run -d -p 8000:8000 --gpus all my-ml-app
```

### 3. Database / Service Containers
Run PostgreSQL, Redis, ChromaDB without local install:

```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=*** postgres:16
docker run -d -p 6379:6379 redis:7
docker run -d -p 8001:8000 chromadb/chroma
```

### 4. GPU-Enabled ML Training
RTX 5070 accessible from containers via NVIDIA Container Toolkit:

```bash
docker run --rm --gpus all -v C:/Users/valte/project:/workspace pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime python /workspace/train.py
```

## Docker Desktop on Windows — Key Facts

- **WSL2 backend** default, recommended
- **GPU passthrough** via NVIDIA Container Toolkit
- **Volume mounts**: `-v C:/Users/valte/project:/app`
- **Host access**: containers reach host via `host.docker.internal`

## Common Commands

```bash
docker build -t myapp . && docker run -d --name myapp -p 8000:8000 -v C:/Users/valte/project:/app myapp
docker run --rm -v C:/Users/valte/project:/workspace python:3.11 python /workspace/script.py
docker logs -f myapp
docker stop myapp && docker rm myapp
```

## Pitfalls

- **Path translation**: Windows `C:\Users\valte` → Docker `C:/Users/valte`
- **Line endings**: Add `.gitattributes` with `* text eol=lf`
- **GPU not visible**: Ensure NVIDIA Container Toolkit + WSL2 integration enabled
- **Volume permissions**: Linux containers may not write to Windows mounts — use named volumes
