# AetherMind cloud image — self-contained RAG site, OpenRouter powered.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# web_ui/, rag_vector_db/, cloud_server.py are copied in by build_deploy.py
COPY . .

ENV OPENROUTER_MODEL=openrouter/free
EXPOSE 8000
CMD ["sh", "-c", "python cloud_server.py"]
