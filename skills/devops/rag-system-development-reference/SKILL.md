---
name: rag-system-development-reference
title: RAG System Development Reference Documentation
version: 1.0.0
author: Hermes Agent
description: Comprehensive reference documentation and architecture patterns for production-ready Retrieval-Augmented Generation (RAG) systems. Contains reusable templates, code patterns, and implementation guidance.
created: 2025-06-23
last_modified: 2025-06-23
status: active
---

# RAG System Development Reference Documentation

## Overview

This document serves as a complete reference guide for building, maintaining, and scaling Retrieval-Augmented Generation (RAG) systems in production environments. It includes proven architecture patterns, implementation strategies, and operational guidelines derived from successful deployments.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Implementation Patterns](#implementation-patterns)
4. [Error Handling Patterns](#error-handling-patterns)
5. [Testing Strategies](#testing-strategies)
6. [Configuration Patterns](#configuration-patterns)
7. [Monitoring & Debugging](#monitoring--debugging)
8. [Production Deployment](#production-deployment)
9. [Security Considerations](#security-considerations)

---

## System Architecture

### Overview Diagram

```
User Request → Text Processing → Embedding Generation → Vector Search → Context Retrieval → LLM Prompt → Answer Generation
     ↓              ↓              ↓              ↓              ↓              ↓              ↓
Document Ingestion → PDF Processing → Text Cleaning → Semantic Chunker → Vector DB → Query Processing → Ollama Integration
```

### Core Architecture Layers

#### Layer 1: Ingestion Layer
- **Purpose**: Document collection and initial processing
- **Components**: File readers, format converters, document parsers
- **Responsibilities**: PDF extraction, text normalization, format handling

#### Layer 2: Processing Layer
- **Purpose**: Text processing and chunking
- **Components**: Text cleaners, chunkers, embedding generators
- **Responsibilities**: Text normalization, semantic segmentation, vector generation

#### Layer 3: Storage Layer
- **Purpose**: Persistent storage and retrieval
- **Components**: Vector databases, metadata stores, caching systems
- **Responsibilities**: Data persistence, similarity search, indexing

#### Layer 4: Query Layer
- **Purpose**: Request processing and response generation
- **Components**: Query processors, context builders, LLM integrations
- **Responsibilities**: Semantic search, context assembly, answer generation

### Scaling Considerations

#### Horizontal Scaling
- **Load Balancer**: Distribute requests across multiple instances
- **Database Replication**: Sync vector databases across nodes
- **Cache Invalidation**: Maintain consistency across replicas

#### Vertical Scaling
- **Resource Allocation**: Scale CPU, memory, GPU resources
- **Database Optimization**: Optimize query performance and indexing
- **Connection Pooling**: Manage database connections efficiently

## Core Components

### 1. Document Processing Pipeline
```python
# Complete document processing workflow
class DocumentProcessingPipeline:
    def __init__(self, config):
        self.config = config
        self.pdf_processor = PDFProcessor()
        self.text_cleaner = TextCleaner()
        self.chunker = SemanticChunker()
    
    def process_document(self, document_path):
        """Process a single document through the pipeline"""
        # Step 1: PDF extraction
        raw_text = self.pdf_processor.extract_text(document_path)
        
        # Step 2: Text cleaning
        cleaned_text = self.text_cleaner.clean(raw_text)
        
        # Step 3: Semantic chunking
        chunks = self.chunker.chunk(cleaned_text)
        
        return chunks
    
    def process_batch(self, document_paths):
        """Process multiple documents efficiently"""
        results = []
        for path in document_paths:
            chunks = self.process_document(path)
            results.extend(chunks)
        
        return results
```

### 2. Vector Storage Architecture
```python
# High-performance vector storage system
class RAGVectorStore:
    def __init__(self, config):
        self.client = chromadb.PersistentClient(path=config.db_path)
        self.collection_name = config.collection_name
        self.embedding_fn = self._get_embedding_function(config)
        self.collection = self._ensure_collection()
        self.index_config = config.index_config
    
    def _get_embedding_function(self, config):
        """Configure embedding function based on model"""
        embedding_models = {
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "text-embedding-ada-002": "openai/text-embedding-ada-002",
            "gemini-embedding": "google-genai/gemini-embedding"
        }
        
        model_name = embedding_models.get(config.embedding_model, "all-MiniLM-L6-v2")
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
    
    def _ensure_collection(self):
        """Ensure collection exists with proper configuration"""
        return self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={
                "hnsw:space": self.index_config.similarity_metric,
                "hnsw:efConstruction": self.index_config.ef_construction,
                "hnsw:efSearch": self.index_config.ef_search,
                "batch_size": self.index_config.batch_size
            }
        )
    
    def add_documents(self, documents, metadata=None, batch_size=100):
        """Add documents to vector store in batches"""
        documents = self._prepare_documents(documents, metadata)
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self._insert_batch(batch)
    
    def _prepare_documents(self, documents, metadata):
        """Prepare documents for storage"""
        prepared = []
        
        for doc_id, content in enumerate(documents):
            doc_meta = metadata[doc_id] if metadata else {}
            
            prepared.append({
                "id": f"doc_{doc_id}",
                "document": content,
                "metadata": doc_meta,
                "embedding": None  # Generated on demand
            })
        
        return prepared
    
    def _insert_batch(self, batch):
        """Insert a batch of documents"""
        documents = [doc["document"] for doc in batch]
        metadatas = [doc["metadata"] for doc in batch]
        ids = [doc["id"] for doc in batch]
        
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def similarity_search(self, query, n_results=10, filter_dict=None):
        """Perform similarity search"""
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_dict
        )
    
    def hybrid_search(self, query, keyword_weight=0.5, vector_weight=0.5):
        """Perform hybrid keyword + vector search"""
        # This would require additional implementation
        # combining BM25 keywords with vector similarity
        pass
```

### 3. Query Processing Pipeline
```python
# Advanced query processing system
class QueryProcessor:
    def __init__(self, config):
        self.config = config
        self.rag_chain = self._build_rag_chain()
    
    def _build_rag_chain(self):
        """Build the complete RAG processing chain"""
        # This would use LangChain or similar framework
        # for complex question answering pipelines
        
        chain_steps = [
            self._create_prompt_builder(),
            self._create_context_retriever(),
            self._create_llm_executor(),
            self._create_response_formatter()
        ]
        
        return RAGChain(chain_steps)
    
    def _create_prompt_builder(self):
        """Create prompt builder for context assembly"""
        return lambda context, query: f"""
            You are an expert AI assistant specializing in {self.config.domain}.
            
            Use the following context to answer the user's question:
            
            Context: {context}
            
            User Question: {query}
            
            Please provide a comprehensive answer based on the context provided.
            If the context doesn't contain sufficient information to answer the question,
            state "I don't have enough information in my database to answer that."
            
            Answer:
            """
    
    def _create_context_retriever(self):
        """Create context retriever using vector database"""
        return lambda query: self._retrieve_relevant_context(query)
    
    def _create_llm_executor(self):
        """Create LLM executor with streaming support"""
        return lambda prompt: self._call_llm(prompt, stream=True)
    
    def _create_response_formatter(self):
        """Create response formatter"""
        return lambda response: self._format_llm_response(response)
    
    def _retrieve_relevant_context(self, query):
        """Retrieve relevant context for query"""
        results = self.collection.query(
            query_texts=[query],
            n_results=self.config.context_window,
            where=self._get_query_filter(query)
        )
        
        return self._format_context(results)
    
    def _get_query_filter(self, query):
        """Get query-specific filter for context retrieval"""
        # Implement any query-specific filtering
        return {}
    
    def _format_context(self, query_results):
        """Format query results into context string"""
        contexts = []
        
        for i in range(len(query_results['documents'][0])):
            doc_context = f"""
            Chunk {i+1}:
            Source: {query_results['metadatas'][0][i].get('source', 'Unknown')}
            Content: {query_results['documents'][0][i]}
            """
            contexts.append(doc_context)
        
        return "\n".join(contexts)
    
    def _call_llm(self, prompt, stream=False):
        """Call LLM with given prompt"""
        # Implementation depends on LLM provider
        # ollama, openai, anthropic, etc.
        pass
    
    def _format_llm_response(self, response):
        """Format LLM response"""
        return response.strip()
    
    def process_query(self, query):
        """Process a user query through the complete pipeline"""
        # Get relevant context
        context = self._retrieve_relevant_context(query)
        
        # Build prompt
        prompt = self._create_prompt_builder()(context, query)
        
        # Call LLM
        response = self._call_llm(prompt, stream=self.config.stream_response)
        
        # Format response
        formatted_response = self._format_llm_response(response)
        
        return {
            "query": query,
            "context": context,
            "response": formatted_response,
            "sources": self._extract_sources(context)
        }
    
    def _extract_sources(self, context):
        """Extract source information from context"""
        # Parse context to extract source references
        lines = context.split('\n')
        sources = []
        
        for line in lines:
            if line.startswith('Source:'):
                source = line.replace('Source:', '').strip()
                sources.append(source)
        
        return sources
```

## Implementation Patterns

### Pattern 1: Modular Architecture

```python
# Hierarchical module structure for maintainability
project/
├── src/
│   ├── core/                    # Core RAG functionality
│   │   ├── pipeline.py          # Main processing pipeline
│   │   ├── storage.py           # Vector storage management
│   │   └── retrieval.py         # Query processing
│   ├── services/                # Business logic services
│   │   ├── document_processor.py # Document processing
│   │   ├── chunker.py          # Text chunking
│   │   └── embedder.py         # Embedding generation
│   ├── utils/                   # Utility functions
│   │   ├── config.py            # Configuration management
│   │   ├── logging.py          # Logging utilities
│   │   └── monitoring.py        # Monitoring tools
│   └── api/                     # API layer
│       ├── fastapi_app.py      # FastAPI application
│       ├── routes/             # API routes
│       │   ├── documents.py     # Document endpoints
│       │   ├── queries.py      # Query endpoints
│       │   └── health.py       # Health checks
│       └── websockets.py       # WebSocket support
│
├── tests/                      # Test suite
│   ├── unit/                  # Unit tests
│   │   ├── test_pipeline.py   # Pipeline tests
│   │   ├── test_storage.py    # Storage tests
│   │   └── test_services.py   # Service tests
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test fixtures
│
├── scripts/                    # Deployment and maintenance scripts
│   ├── deploy.py             # Deployment script
│   ├── migrate.py            # Database migration
│   ├── backup.py            # Backup utilities
│   └── monitor.py            # Monitoring script
│
├── docs/                      # Documentation
│   ├── api/                  # API documentation
│   ├── architecture/         # Architecture documentation
│   └── guides/               # User guides
│
├── configs/                   # Configuration files
│   ├── development.yaml      # Development config
│   ├── staging.yaml          # Staging config
│   └── production.yaml       # Production config
│
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker orchestration
├── requirements.txt          # Dependencies
└── README.md                 # Project documentation
```

### Pattern 2: Database Migration Strategy

```python
# Database migration framework
class DatabaseMigrator:
    def __init__(self, source_db, target_db):
        self.source = source_db
        self.target = target_db
        self.migrations = []
    
    def add_migration(self, version, description, up_func, down_func):
        """Add a migration"""
        self.migrations.append({
            'version': version,
            'description': description,
            'up': up_func,
            'down': down_load_func
        })
    
    def migrate(self, to_version=None):
        """Run migrations up to specified version"""
        current_version = self._get_current_version()
        
        if to_version is None:
            to_version = max(m['version'] for m in self.migrations)
        
        # Run forward migrations
        for migration in sorted(self.migrations, key=lambda x: x['version']):
            if migration['version'] > current_version:
                if migration['version'] <= to_version:
                    print(f"Applying migration {migration['version']}: {migration['description']}")
                    migration['up']()
                    self._update_version(migration['version'])
    
    def rollback(self, to_version):
        """Rollback migrations to specified version"""
        current_version = self._get_current_version()
        
        for migration in sorted(self.migrations, key=lambda x: x['version'], reverse=True):
            if current_version > to_version and migration['version'] <= current_version:
                print(f"Rolling back migration {migration['version']}")
                migration['down']()
                self._update_version(migration['version'] - 1)
    
    def _get_current_version(self):
        """Get current database version"""
        # Implementation depends on storage mechanism
        pass
    
    def _update_version(self, version):
        """Update database version"""
        # Implementation depends on storage mechanism
        pass
```

### Pattern 3: Configuration Management

```python
# Advanced configuration management
class ConfigurationManager:
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config = {}
        self.environment = self._detect_environment()
        
        if config_file:
            self.load_config()
        else:
            self.load_from_environment()
    
    def _detect_environment(self):
        """Detect current environment"""
        if 'ENVIRONMENT' in os.environ:
            return os.environ['ENVIRONMENT']
        
        # Detect from common environment indicators
        if os.path.exists('/.dockerenv'):
            return 'docker'
        elif os.path.exists('/etc/nginx/nginx.conf'):
            return 'kubernetes'
        else:
            return 'development'
    
    def load_config(self, file_path=None):
        """Load configuration from file"""
        path = file_path or self.config_file
        
        if path.endswith('.yaml') or path.endswith('.yml'):
            import yaml
            with open(path, 'r') as f:
                self.config = yaml.safe_load(f)
        elif path.endswith('.json'):
            import json
            with open(path, 'r') as f:
                self.config = json.load(f)
        elif path.endswith('.env'):
            import python_dotenv
            python_dotenv.load_dotenv(path)
            self.config = self._flatten_env()
    
    def _flatten_env(self):
        """Flatten environment variables"""
        import os
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith('RAG_'):
                config[key[4:]] = self._convert_value(value)
        
        return config
    
    def _convert_value(self, value):
        """Convert environment variable to appropriate type"""
        # Try to convert to boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try to convert to integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return string
        return value
    
    def get(self, key, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if i == 0 and k not in config:
                config[k] = {}
            elif not isinstance(config.get(k), dict):
                config[k] = {}
            
            config = config[k]
        
        config[keys[-1]] = value
    
    def reload(self):
        """Reload configuration from file"""
        if self.config_file:
            self.load_config()
    
    def save(self, file_path=None):
        """Save configuration to file"""
        path = file_path or self.config_file
        
        if not path:
            raise ValueError("No config file specified")
        
        if path.endswith('.yaml') or path.endswith('.yml'):
            import yaml
            with open(path, 'w') as f:
                yaml.dump(self.config, f)
        elif path.endswith('.json'):
            import json
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
```

## Error Handling Patterns

### Pattern 1: Hierarchical Error Handling

```python
class HierarchicalErrorHandler:
    def __init__(self):
        self.error_handlers = []
        self.retry_strategies = {}
    
    def add_handler(self, exception_type, handler_func, priority=1):
        """Add error handler for specific exception type"""
        self.error_handlers.append({
            'exception_type': exception_type,
            'handler': handler_func,
            'priority': priority
        })
        
        # Sort by priority (higher priority first)
        self.error_handlers.sort(key=lambda x: x['priority'], reverse=True)
    
    def handle(self, exception, context=None):
        """Handle exception with registered handlers"""
        for handler_info in self.error_handlers:
            if isinstance(exception, handler_info['exception_type']):
                try:
                    return handler_info['handler'](exception, context)
                except Exception as handler_error:
                    print(f"Error handler failed: {handler_error}")
                    continue
        
        # No handler found, re-raise the original exception
        raise
    
    def add_retry_strategy(self, exception_type, max_retries=3, delay=1.0):
        """Add retry strategy for specific exception type"""
        self.retry_strategies[exception_type] = {
            'max_retries': max_retries,
            'delay': delay,
            'backoff_factor': 2.0
        }
    
    def execute_with_retry(self, func, exception_type, *args, **kwargs):
        """Execute function with automatic retry on specified exception"""
        if exception_type not in self.retry_strategies:
            return func(*args, **kwargs)
        
        strategy = self.retry_strategies[exception_type]
        max_retries = strategy['max_retries']
        delay = strategy['delay']
        backoff_factor = strategy['backoff_factor']
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                last_exception = e
                
                if attempt < max_retries:
                    wait_time = delay * (backoff_factor ** attempt)
                    print(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time:.2f}s")
                    time.sleep(wait_time)
                else:
                    print(f"Max retries ({max_retries}) exhausted for {exception_type}")
        
        raise last_exception
```

### Pattern 2: Circuit Breaker

```python
import time
import threading
from functools import wraps

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
        self.lock = threading.Lock()
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == 'OPEN':
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = 'HALF_OPEN'
                        print("Circuit breaker moving to HALF_OPEN state")
                    else:
                        raise CircuitBreakerError("Circuit breaker is OPEN")
                
                if self.state == 'HALF_OPEN':
                    try:
                        result = func(*args, **kwargs)
                        self._on_success()
                        return result
                    except self.expected_exception as e:
                        self._on_failure()
                        raise
                
                # CLOSED state
                return func(*args, **kwargs)
        
        return wrapper
    
    def _on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            print(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def reset(self):
        with self.lock:
            self.failure_count = 0
            self.state = 'CLOSED'

class CircuitBreakerError(Exception):
    pass
```

### Pattern 3: Graceful Degradation

```python
class GracefulDegradation:
    def __init__(self):
        self.quality_levels = {
            'high': {'min_chunks': 5, 'max_response_time': 1.0},
            'medium': {'min_chunks': 3, 'max_response_time': 5.0},
            'low': {'min_chunks': 1, 'max_response_time': 30.0}
        }
    
    def assess_system_state(self, memory_usage, gpu_available, response_time):
        """Assess current system state and return appropriate quality level"""
        if not gpu_available:
            return 'low'
        
        if memory_usage > 0.9:
            return 'low'
        
        if response_time > 10.0:
            return 'medium'
        
        return 'high'
    
    def degrade_request(self, query, quality_level='medium'):
        """Process request with specified quality level"""
        requirements = self.quality_levels[quality_level]
        
        # Modify processing based on quality level
        return self._process_query(query, requirements)
    
    def _process_query(self, query, requirements):
        """Process query with specific requirements"""
        # Retrieve context (simplified)
        context = self._retrieve_context(query, min_chunks=requirements['min_chunks'])
        
        # Generate response (simplified)
        response = self._generate_response(query, context, max_time=requirements['max_response_time'])
        
        return {
            'query': query,
            'context': context,
            'response': response,
            'quality_level': requirements['quality'],
            'metadata': {
                'min_chunks_satisfied': len(context) >= requirements['min_chunks'],
                'response_time_under_limit': self._estimate_response_time() <= requirements['max_response_time']
            }
        }
```

## Testing Strategies

### Pattern 1: Contract Testing

```yaml
# contract_tests.yml - Pact-style contract definitions
services:
  rag-system:
    endpoint: /api/queries
    methods:
      GET /api/queries:
        request:
          query_parameters:
            q: string
            n: integer
        response:
          status: 200
          headers:
            content-type: application/json
          body:
            type: object
            properties:
              query:
                type: string
              response:
                type: string
              sources:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: string
                    source:
                      type: string
```

```python
# contract_test_client.py
import requests
import json

def test_rag_api_contract():
    """Test RAG API against contract"""
    base_url = "http://localhost:8000/api"
    
    # Load contract
    with open('contract_tests.yml', 'r') as f:
        contract = yaml.safe_load(f)
    
    # Test query endpoint
    test_endpoint = contract['services']['rag-system']['methods']['GET /api/queries']
    
    # Prepare test request
    request_template = test_endpoint['request']
    response_template = test_endpoint['response']
    
    # Test with sample data
    test_request = {
        'q': 'What is the architecture of RAG systems?',
        'n': 3
    }
    
    response = requests.get(f"{base_url}/queries", params=test_request)
    
    # Validate response against contract
    assert response.status_code == response_template['status']
    
    response_data = response.json()
    
    # Validate response structure
    assert 'query' in response_data
    assert 'response' in response_data
    assert 'sources' in response_data
    
    print("✅ Contract test passed")
```

### Pattern 2: Property-Based Testing

```python
from hypothesis import given, settings, example

class TestRAGProperties:
    @given(text=st.text(min_size=1, max_size=1000))
    @settings(max_examples=10, deadline=1000.0)
    def test_chunk_property(self, text):
        """Property test: Chunks should not contain overlapping content"""
        chunker = SimpleChunker(max_tokens=512)
        chunks = chunker.chunk_text(text)
        
        # Property 1: No overlapping content
        for i in range(len(chunks) - 1):
            assert not text.find(chunks[i], i+1)  # chunks[i] should not appear again
        
        # Property 2: All original content preserved
        reconstructed = ''.join(chunks)
        assert text in reconstructed or text.replace(' ', '') in reconstructed
        
        # Property 3: No chunk exceeds maximum tokens
        for chunk in chunks:
            tokens = self.tokenizer.encode(chunk)
            assert len(tokens) <= 512
    
    @given(query=st.text(min_size=1, max_size=200))
    def test_search_consistency(self, query):
        """Property test: Search should be deterministic"""
        # Perform search twice
        results1 = self.vector_store.similarity_search(query, n_results=5)
        results2 = self.vector_store.similarity_search(query, n_results=5)
        
        # Results should be identical (ignoring scores)
        for i in range(len(results1['documents'][0])):
            assert results1['documents'][0][i] == results2['documents'][0][i]
            assert results1['metadatas'][0][i] == results2['metadatas'][0][i]
    
    @example(text="Hello world!")
    @example(text="This is a longer text with multiple sentences. Testing the chunker property can be complex.")
    def test_edge_cases(self, text):
        """Test edge cases"""
        chunker = SimpleChunker(max_tokens=512)
        chunks = chunker.chunk_text(text)
        
        # Should never return empty chunks for non-empty input
        if text:
            assert len(chunks) > 0
```

### Pattern 3: Chaos Testing

```python
# chaos_test.py - Simulate various failure scenarios
class ChaosTestSuite:
    def __init__(self, rag_system):
        self.rag_system = rag_system
        self.original_config = config.copy()
    
    def test_with_network_failure(self):
        """Test RAG system with network failure"""
        # Simulate network failure
        import requests
        original_get = requests.get
        
        def failing_get(*args, **kwargs):
            raise ConnectionError("Network unreachable")
        
        requests.get = failing_get
        
        try:
            # Test that system handles gracefully
            result = self.rag_system.process_query("test query")
            assert 'error' in result
        finally:
            requests.get = original_get
    
    def test_with_memory_pressure(self):
        """Test RAG system under memory pressure"""
        import psutil
        import threading
        
        def consume_memory():
            """Consume memory in background thread"""
            data = []
            while True:
                data.append([0] * 1000000)  # Allocate memory
                time.sleep(0.1)
        
        # Start memory consumption
        memory_thread = threading.Thread(target=consume_memory)
        memory_thread.daemon = True
        memory_thread.start()
        
        try:
            # Give memory consumption time to take effect
            time.sleep(2)
            
            # Test that system still works
            result = self.rag_system.process_query("memory test")
            assert 'response' in result
        finally:
            # Cleanup
            del data
    
    def test_with_gpu_failure(self):
        """Test RAG system with GPU failure"""
        import torch
        
        # Temporarily disable CUDA
        original_cuda = torch.cuda.is_available
        torch.cuda.is_available = lambda: False
        
        try:
            # Test that system falls back to CPU
            result = self.rag_system.process_query("gpu failure test")
            assert 'response' in result
        finally:
            torch.cuda.is_available = original_cuda
    
    def run_all_tests(self):
        """Run all chaos tests"""
        self.test_with_network_failure()
        self.test_with_memory_pressure()
        self.test_with_gpu_failure()
        print("✅ All chaos tests passed")
```

## Configuration Patterns

### Pattern 1: Feature Flags

```yaml
# config/feature_flags.yml
feature_flags:
  # Core RAG functionality
  rag_core_enabled: true
  vector_search_enabled: true
  llm_integration_enabled: true
  
  # Performance features
  streaming_enabled: false
  caching_enabled: true
  indexing_enabled: true
  
  # Advanced features
  batch_processing_enabled: true
  multi_modal_enabled: false
  hybrid_search_enabled: false
  
  # Monitoring features
  metrics_enabled: true
  logging_enabled: true
  alerting_enabled: false
  
  # Scalability features
  horizontal_scaling_enabled: true
  load_balancing_enabled: true
  auto_scaling_enabled: false
```

```python
# config/feature_manager.py
class FeatureManager:
    def __init__(self, config_file='config/feature_flags.yml'):
        self.config = self._load_config(config_file)
        self.features = self._parse_feature_flags(self.config)
    
    def _load_config(self, config_file):
        """Load configuration from file"""
        if config_file.endswith('.yml') or config_file.endswith('.yaml'):
            import yaml
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _parse_feature_flags(self, config):
        """Parse feature flags from configuration"""
        features = {}
        
        if 'feature_flags' in config:
            for feature_name, enabled in config['feature_flags'].items():
                features[feature_name] = {
                    'enabled': enabled,
                    'dependencies': self._get_feature_dependencies(feature_name),
                    'conflicts': self._get_feature_conflicts(feature_name)
                }
        
        return features
    
    def _get_feature_dependencies(self, feature_name):
        """Get features that a given feature depends on"""
        dependencies = {
            'rag_core_enabled': [],
            'vector_search_enabled': ['rag_core_enabled'],
            'llm_integration_enabled': ['rag_core_enabled', 'vector_search_enabled'],
            'streaming_enabled': ['llm_integration_enabled'],
            'caching_enabled': ['rag_core_enabled'],
            'indexing_enabled': ['vector_search_enabled'],
            'batch_processing_enabled': ['rag_core_enabled'],
            'multi_modal_enabled': ['llm_integration_enabled'],
            'hybrid_search_enabled': ['vector_search_enabled'],
            'metrics_enabled': ['rag_core_enabled'],
            'logging_enabled': ['rag_core_enabled'],
            'alerting_enabled': ['metrics_enabled'],
            'horizontal_scaling_enabled': ['rag_core_enabled'],
            'load_balancing_enabled': ['rag_core_enabled'],
            'auto_scaling_enabled': ['horizontal_scaling_enabled']
        }
        
        return dependencies.get(feature_name, [])
    
    def _get_feature_conflicts(self, feature_name):
        """Get features that conflict with a given feature"""
        conflicts = {
            'streaming_enabled': ['low_quality_mode_enabled'],
            'indexing_enabled': ['low_quality_mode_enabled'],
            'caching_enabled': ['low_quality_mode_enabled'],
            'batch_processing_enabled': ['real_time_enabled'],
            'multi_modal_enabled': ['text_only_enabled'],
            'hybrid_search_enabled': ['vector_search_enabled_only'],
            'alerting_enabled': ['silent_mode_enabled']
        }
        
        return conflicts.get(feature_name, [])
    
    def is_feature_enabled(self, feature_name):
        """Check if a feature is enabled"""
        if feature_name not in self.features:
            return False
        
        feature_info = self.features[feature_name]
        
        # Check dependencies
        for dependency in feature_info['dependencies']:
            if not self.is_feature_enabled(dependency):
                return False
        
        # Check conflicts
        for conflict in feature_info['conflicts']:
            if self.is_feature_enabled(conflict):
                return False
        
        return feature_info['enabled']
    
    def enable_feature(self, feature_name, validate_dependencies=True):
        """Enable a feature"""
        if feature_name not in self.features:
            raise ValueError(f"Feature '{feature_name}' not found")
        
        if validate_dependencies:
            # Check dependencies before enabling
            for dependency in self.features[feature_name]['dependencies']:
                if not self.is_feature_enabled(dependency):
                    raise ValueError(f"Cannot enable '{feature_name}' - dependency '{dependency}' is disabled")
        
        self.features[feature_name]['enabled'] = True
        
        # Enable dependent features
        for dep in self.features[feature_name]['dependencies']:
            if dep in self.features:
                self.features[dep]['enabled'] = True
    
    def disable_feature(self, feature_name):
        """Disable a feature"""
        if feature_name not in self.features:
            raise ValueError(f"Feature '{feature_name}' not found")
        
        self.features[feature_name]['enabled'] = False
        
        # Remove dependent features
        for feature in self.features:
            if feature in self.features[feature_name]['dependencies']:
                self.features[feature]['enabled'] = False
```

## Monitoring & Debugging

### Pattern 1: Distributed Tracing

```python
# tracing.py - OpenTelemetry-based distributed tracing
import opentelemetry as otel
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.instrumentation.system_functions import deprecation
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportResultHandler
import time

class TracingConfig:
    def __init__(self, service_name="rag-system", endpoint=None):
        self.service_name = service_name
        self.endpoint = endpoint
        self.tracer = None
        self.meter = None
    
    def setup(self):
        """Setup OpenTelemetry instrumentation"""
        # Create tracer provider
        tracer_provider = TracerProvider(
            resource=Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0"
            })
        )
        
        # Add span processors
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=self.endpoint)
        )
        tracer_provider.add_span_processor(span_processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Create meter provider
        meter_provider = MeterProvider()
        metric_exporter = PrometheusMetricExporter(endpoint=self.endpoint)
        meter_provider.add_metric_reader(
            PeriodicExportResultHandler(metric_exporter)
        )
        
        # Set as global meter provider
        metrics.set_meter_provider(meter_provider)
        
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
    
    def start_span(self, span_name, attributes=None):
        """Start a new span"""
        if self.tracer:
            span = self.tracer.start_span(span_name)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            return span
        return None
    
    def log_metric(self, metric_name, value, attributes=None):
        """Log a metric"""
        if self.meter:
            instrumentation_scope = self.meter.get_instrumentation_scope(__name__)
            metric = instrumentation_scope.counter(metric_name)
            metric.add(value, attributes or {})
```

### Pattern 2: Performance Monitoring

```python
# monitoring.py - Comprehensive performance monitoring
import psutil
import time
from datetime import datetime
from typing import Dict, List, Any

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'memory': [],
            'cpu': [],
            'gpu': [],
            'response_time': [],
            'throughput': []
        }
        self.start_time = time.time()
        self.monitoring = False
    
    def start_monitoring(self, interval=1.0):
        """Start monitoring system metrics"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._collect_metrics, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _collect_metrics(self, interval):
        """Collect metrics in background thread"""
        while self.monitoring:
            metrics = self._collect_current_metrics()
            
            with self.metrics_lock:
                for metric_name, value in metrics.items():
                    if metric_name in self.metrics:
                        self.metrics[metric_name].append({
                            'timestamp': time.time(),
                            'value': value,
                            'process_id': os.getpid()
                        })
            
            # Keep only last hour of metrics
            self._cleanup_old_metrics()
            
            time.sleep(interval)
    
    def _collect_current_metrics(self):
        """Collect current system metrics"""
        metrics = {}
        
        # CPU usage
        metrics['cpu'] = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        metrics['memory'] = memory.percent
        
        # GPU usage (if available)
        try:
            import torch
            if torch.cuda.is_available():
                gpu_metrics = self._get_gpu_metrics()
                metrics.update(gpu_metrics)
        except ImportError:
            pass
        
        # Process-specific metrics
        process = psutil.Process()
        metrics['process_cpu'] = process.cpu_percent()
        metrics['process_memory'] = process.memory_percent()
        
        return metrics
    
    def _get_gpu_metrics(self):
        """Get GPU metrics"""
        import torch
        
        metrics = {}
        
        for i in range(torch.cuda.device_count()):
            metrics[f'gpu_{i}_utilization'] = torch.cuda.utilization(i)
            metrics[f'gpu_{i}_memory_used'] = torch.cuda.memory_allocated(i) / 1024**3  # GB
            metrics[f'gpu_{i}_memory_total'] = torch.cuda.get_device_properties(i).total_memory / 1024**3  # GB
        
        return metrics
    
    def _cleanup_old_metrics(self):
        """Remove old metrics (older than 1 hour)"""
        current_time = time.time()
        cutoff_time = current_time - 3600  # 1 hour ago
        
        for metric_name in self.metrics:
            self.metrics[metric_name] = [
                m for m in self.metrics[metric_name]
                if m['timestamp'] > cutoff_time
            ]
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5.0)
    
    def get_metrics_summary(self, time_window=300):
        """Get metrics summary for time window"""
        cutoff_time = time.time() - time_window
        
        summary = {}
        
        for metric_name in self.metrics:
            recent_metrics = [
                m for m in self.metrics[metric_name]
                if m['timestamp'] > cutoff_time
            ]
            
            if recent_metrics:
                values = [m['value'] for m in recent_metrics]
                summary[metric_name] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'current': values[-1]
                }
        
        return summary
    
    def generate_report(self):
        """Generate performance report"""
        summary = self.get_metrics_summary()
        
        report = f"Performance Report\n"
        report += f"Generated at: {datetime.now()}\n"
        report += f"Total monitoring time: {time.time() - self.start_time:.1f}s\n\n"
        
        for metric_name, data in summary.items():
            report += f"{metric_name.title()}:\n"
            report += f"  Average: {data['average']:.2f}\n"
            report += f"  Min: {data['min']:.2f}\n"
            report += f"  Max: {data['max']:.2f}\n"
            report += f"  Current: {data['current']:.2f}\n"
            report += "\n"
        
        return report
```

### Pattern 3: Alerting System

```python
# alerting.py - Intelligent alerting system
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Dict, List, Any

class AlertingSystem:
    def __init__(self, config):
        self.config = config
        self.alert_queue = []
        self.notification_channels = self._setup_notification_channels()
    
    def _setup_notification_channels(self):
        """Setup notification channels based on configuration"""
        channels = {}
        
        if self.config.get('email', {}).get('enabled', False):
            channels['email'] = EmailNotifier(
                smtp_server=self.config['email']['smtp_server'],
                smtp_port=self.config['email']['smtp_port'],
                username=self.config['email']['username'],
                password=self.config['email']['password'],
                from_address=self.config['email']['from_address'],
                to_addresses=self.config['email']['to_addresses']
            )
        
        if self.config.get('slack', {}).get('enabled', False):
            channels['slack'] = SlackNotifier(
                webhook_url=self.config['slack']['webhook_url']
            )
        
        if self.config.get('teams', {}).get('enabled', False):
            channels['teams'] = TeamsNotifier(
                webhook_url=self.config['teams']['webhook_url']
            )
        
        if self.config.get('pagerduty', {}).get('enabled', False):
            channels['pagerduty'] = PagerDutyNotifier(
                api_key=self.config['pagerduty']['api_key'],
                integration_key=self.config['pagerduty']['integration_key']
            )
        
        return channels
    
    def send_alert(self, alert_type, severity, message, context=None):
        """Send alert through configured channels"""
        alert = {
            'type': alert_type,
            'severity': severity,
            'message': message,
            'context': context or {},
            'timestamp': datetime.now(),
            'id': self._generate_alert_id()
        }
        
        # Add to alert queue
        self.alert_queue.append(alert)
        
        # Send through all enabled channels
        for channel_name, channel in self.notification_channels.items():
            try:
                channel.send(alert)
            except Exception as e:
                print(f"Failed to send alert through {channel_name}: {e}")
        
        # Log alert
        self._log_alert(alert)
    
    def _generate_alert_id(self):
        """Generate unique alert ID"""
        return f"alert-{int(time.time())}-{hash(str(datetime.now()))}"
    
    def _log_alert(self, alert):
        """Log alert to file"""
        log_entry = f"{alert['timestamp'].isoformat()} [{alert['severity']}] {alert['type']}: {alert['message']}\n"
        
        with open('alerts.log', 'a') as f:
            f.write(log_entry)
    
    def process_alerts(self):
        """Process queued alerts"""
        while self.alert_queue:
            alert = self.alert_queue.pop(0)
            
            # Check if alert should be escalated
            if self._should_escalate(alert):
                self._escalate_alert(alert)
            
            # Add to processed alerts file
            self._write_processed_alert(alert)
    
    def _should_escalate(self, alert):
        """Determine if alert should be escalated"""
        # Check if alert is older than threshold
        age = (datetime.now() - alert['timestamp']).total_seconds()
        if age > self.config.get('alert_threshold_seconds', 300):
            return True
        
        # Check if same type of alert occurred recently
        similar_alerts = [
            a for a in self.alert_queue
            if a['type'] == alert['type'] and 
               abs((a['timestamp'] - alert['timestamp']).total_seconds()) < 300
        ]
        
        if len(similar_alerts) >= self.config.get('similar_alert_threshold', 3):
            return True
        
        return False
    
    def _escalate_alert(self, alert):
        """Escalate alert to higher severity or different channel"""
        # Create escalated alert
        escalated_alert = alert.copy()
        escalated_alert['severity'] = 'CRITICAL'
        escalated_alert['escalated'] = True
        
        # Send to critical channels only
        critical_channels = ['email', 'slack']  # Example critical channels
        
        for channel_name in critical_channels:
            if channel_name in self.notification_channels:
                try:
                    self.notification_channels[channel_name].send(escalated_alert)
                except Exception as e:
                    print(f"Failed to send escalated alert: {e}")
    
    def _write_processed_alert(self, alert):
        """Write processed alert to file"""
        import json
        
        with open('processed_alerts.json', 'a') as f:
            f.write(json.dumps(alert) + '\n')
```

## Production Deployment

### Pattern 1: Docker Compose

```yaml
# docker-compose.yml - Production deployment
version: '3.8'

services:
  rag-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RAG_ENVIRONMENT=production
      - RAG_LOG_LEVEL=INFO
      - RAG_WORKERS=4
      - RAG_QUEUE_SIZE=100
    volumes:
      - ./data:/app/data:ro
      - ./logs:/app/logs
      - ./rag_vector_db:/app/rag_vector_db
      - ./configs:/app/configs:ro
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    networks:
      - rag-network
    depends_on:
      - redis
      - ollama
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - rag-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    networks:
      - rag-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus-data:/prometheus
    restart: unless-stopped
    networks:
      - rag-network
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana:/etc/grafana/provisioning.d
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
    networks:
      - rag-network

networks:
  rag-network:
    driver: bridge

volumes:
  redis-data:
  ollama-data:
  prometheus-data:
  grafana-data:
```

### Pattern 2: Kubernetes Deployment

```yaml
# k8s-deployment.yaml - Kubernetes configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  labels:
    app: rag-api
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
        version: v1.0.0
    spec:
      containers:
      - name: rag-api
        image: your-registry/rag-api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: RAG_ENVIRONMENT
          value: "production"
        - name: RAG_LOG_LEVEL
          value: "INFO"
        - name: RAG_WORKERS
          value: "4"
        - name: RAG_QUEUE_SIZE
          value: "100"
        resources:
          requests:
            cpu: "500m"
            memory: "1G"
          limits:
            cpu: "2"
            memory: "4G"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
          readOnly: true
        - name: logs-volume
          mountPath: /app/logs
        - name: config-volume
          mountPath: /app/configs
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: data-pvc
      - name: logs-volume
        emptyDir:
          medium: Memory
      - name: config-volume
        configMap:
          name: rag-config
---
apiVersion: v1
kind: Service
metadata:
  name: rag-api-service
  labels:
    app: rag-api
spec:
  selector:
    app: rag-api
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
  - ReadOnlyMany
  storageClassName: standard
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
data:
  LOG_LEVEL: "INFO"
  RAG_WORKERS: "4"
  RAG_QUEUE_SIZE: "100"
  OLLAMA_MODEL: "richardyoung/qwythos-9b-abliterated:Q4_K_M"
```

### Pattern 3: Monitoring Stack

```yaml
# monitoring-stack.yaml - Complete monitoring infrastructure
apiVersion: v1
kind: ConfigMap
metadata:
  name: monitoring-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
      - job_name: 'rag-api'
        static_configs:
          - targets: ['rag-api-service:8000']
        metrics_path: '/metrics'
        scrape_interval: 30s
    
      - job_name: 'node-exporter'
        static_configs:
          - targets: ['node-exporter:9100']
  
  grafana-dashboard.json: |
    {
      "dashboard": {
        "id": 1,
        "title": "RAG System Monitoring",
        "panels": [
          {
            "title": "CPU Usage",
            "type": "graph",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
            "targets": [
              {
                "expr": "rate(container_cpu_usage_total{image=\"\"}[5m])",
                "legendFormat": "{{instance}}"
              }
            ]
          },
          {
            "title": "Memory Usage",
            "type": "graph", 
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
            "targets": [
              {
                "expr": "container_memory_usage_bytes{image=\"\"}/1024/1024/1024",
                "legendFormat": "{{instance}}"
              }
            ]
          },
          {
            "title": "GPU Utilization",
            "type": "graph",
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
            "targets": [
              {
                "expr": "gpu_utilization",
                "legendFormat": "GPU {gpu_id}"
              }
            ]
          }
        ]
      }
    }
    }
```

## Security Implementation

### Pattern 1: Authentication Middleware

```python
# auth_middleware.py - Authentication and authorization
from functools import wraps
import jwt
from typing import Dict, Any, Callable

class AuthMiddleware:
    def __init__(self, config):
        self.config = config
        self.public_keys = self._load_public_keys()
        self.required_roles = config.get('required_roles', {})
    
    def _load_public_keys(self):
        """Load JWT public keys"""
        keys = {}
        
        if 'jwt_keys_url' in self.config:
            import requests
            response = requests.get(self.config['jwt_keys_url'])
            if response.status_code == 200:
                key_data = response.json()
                for key_id, key_info in key_data.items():
                    if 'n' in key_info and 'e' in key_info:
                        keys[key_id] = self._create_public_key(key_info)
        
        return keys
    
    def _create_public_key(self, key_info):
        """Create RSA public key from JWT key information"""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        # Simplified key generation - implement actual JWT key loading
        return None
    
    def authenticate_request(self, request_headers):
        """Authenticate request using JWT token"""
        auth_header = request_headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, "Missing or invalid Authorization header"
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            payload = jwt.decode(
                token,
                self.public_keys,
                algorithms=['RS256'],
                options={'verify_aud': False}
            )
            
            return payload, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            return None, f"Authentication failed: {str(e)}"
    
    def require_role(self, role):
        """Decorator to require specific role for endpoint"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Authenticate request
                payload, error = self.authenticate_request(request_headers)
                if error:
                    return {'error': error, 'status': 401}, 401
                
                # Check role
                user_roles = payload.get('roles', [])
                if role not in user_roles:
                    return {'error': 'Insufficient permissions', 'status': 403}, 403
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def rate_limit(self, max_requests=100, time_window=3600):
        """Rate limiting decorator"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Implementation depends on storage backend
                # Redis, database, etc.
                pass
            return wrapper
        return decorator
    
    def api_key_auth(self, api_key_header='X-API-Key'):
        """API key authentication"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                api_key = request_headers.get(api_key_header)
                if not api_key:
                    return {'error': 'API key required', 'status': 401}, 401
                
                # Validate API key
                if not self._validate_api_key(api_key):
                    return {'error': 'Invalid API key', 'status': 401}, 401
                \n                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _validate_api_key(self, api_key):
        """Validate API key against storage"""
        # Implement API key validation logic
        pass
```

### Pattern 2: Data Encryption

```python
# encryption.py - Data encryption and decryption
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class DataEncryption:
    def __init__(self, master_key, salt=None):
        self.master_key = master_key
        self.salt = salt or self._generate_salt()
        self.key = self._derive_key()
    
    def _generate_salt(self):
        """Generate random salt"""
        import os
        return os.urandom(16)
    
    def _derive_key(self):
        """Derive encryption key from master key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
    
    def encrypt_data(self, data):
        """Encrypt data"""
        f = Fernet(self.key)
        encrypted_data = f.encrypt(data.encode() if isinstance(data, str) else data)
        return encrypted_data
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data"""
        f = Fernet(self.key)
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode() if isinstance(decrypted_data, bytes) else decrypted_data
    
    def encrypt_file(self, file_path, output_path=None):
        """Encrypt file"""
        if output_path is None:
            output_path = file_path + '.enc'
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = self.encrypt_data(data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        return output_path
    
    def decrypt_file(self, encrypted_file_path, output_path=None):
        """Decrypt file"""
        if output_path is None:
            output_path = encrypted_file_path.replace('.enc', '')
        
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.decrypt_data(encrypted_data)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return output_path
```

## Testing Implementation

### Pattern 1: Automated Testing Framework

```yaml
# test-framework.yml - Automated testing configuration
test_suites:
  unit:
    name: "Unit Tests"
    path: "tests/unit"
    pattern: "test_*.py"
    timeout: 300
    retry: 2
    
  integration:
    name: "Integration Tests"
    path: "tests/integration"
    pattern: "test_*.py"
    timeout: 600
    retry: 1
    
  chaos:
    name: "Chaos Tests"
    path: "tests/chaos"
    pattern: "test_*.py"
    timeout: 1200
    retry: 0
    
  performance:
    name: "Performance Tests"
    path: "tests/performance"
    pattern: "test_*.py"
    timeout: 1800
    retry: 1

test_matrix:
  python_versions: ["3.8", "3.9", "3.10", "3.11"]
  operating_systems: ["linux", "macos", "windows"]
  database_configs: [
    {"name": "sqlite", "version": "3.33"},
    {"name": "postgresql", "version": "13"},
    {"name": "mysql", "version": "8"}
  ]
  gpu_configurations: [
    {"cuda_version": "11.0", "gpu_model": "rtx_3080"},
    {"cuda_version": "11.1", "gpu_model": "rtx_4090"},
    {"cuda_version": null, "gpu_model": "cpu_only"}
  ]
```

```python
# test_runner.py - Automated test runner
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging

class TestRunner:
    def __init__(self, config_file='test-framework.yml'):
        self.config = self._load_config(config_file)
        self.test_results = {}
        self.logger = self._setup_logging()
    
    def _load_config(self, config_file):
        """Load test configuration"""
        import yaml
        if Path(config_file).exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _setup_logging(self):
        """Setup logging for test runner"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('test_runner.log')
            ]
        )
        return logging.getLogger(__name__)
    
    async def run_all_tests(self):
        """Run all test suites"""
        for suite_name, suite_config in self.config.get('test_suites', {}).items():
            self.logger.info(f"Running {suite_name} tests...")
            await self.run_test_suite(suite_name, suite_config)
        
        # Generate test report
        self._generate_test_report()
    
    async def run_test_suite(self, suite_name, suite_config):
        """Run a specific test suite"""
        suite_path = Path(suite_config['path'])
        test_pattern = suite_config['pattern']
        timeout = suite_config.get('timeout', 300)
        retry = suite_config.get('retry', 1)
        
        # Collect test files
        test_files = list(suite_path.glob(test_pattern))
        
        if not test_files:
            self.logger.warning(f"No test files found for {suite_name}")
            return
        
        # Run tests in suite
        for test_file in test_files:
            await self.run_single_test(test_file, suite_name, timeout, retry)
    
    async def run_single_test(self, test_file, suite_name, timeout, retry):
        """Run a single test with retries"""
        for attempt in range(retry + 1):
            try:
                self.logger.info(f"Running {test_file.name} (attempt {attempt + 1}/{retry + 1})")
                
                # Run test
                result = await self._run_test(test_file, timeout)
                
                # Record result
                self._record_test_result(test_file, suite_name, result)
                
                if result['passed']:
                    self.logger.info(f"✅ {test_file.name} passed")
                else:
                    self.logger.error(f"❌ {test_file.name} failed: {result['error']}")
                
                return
                
            except asyncio.TimeoutError:
                self.logger.error(f"⏰ {test_file.name} timed out")
                if attempt == retry:
                    self._record_test_result(test_file, suite_name, {
                        'passed': False,
                        'error': f"Test timed out after {timeout} seconds"
                    })
                    break
            except Exception as e:
                self.logger.error(f"❌ {test_file.name} failed: {str(e)}")
                if attempt == retry:
                    self._record_test_result(test_file, suite_name, {
                        'passed': False,
                        'error': str(e)
                    })
                    break
    
    async def _run_test(self, test_file, timeout):
        """Execute a single test"""
        # This would run the actual test using pytest or similar
        # Implementation depends on test framework being used
        pass
    
    def _record_test_result(self, test_file, suite_name, result):
        """Record test result"""
        if suite_name not in self.test_results:
            self.test_results[suite_name] = []
        
        self.test_results[suite_name].append({
            'file': test_file.name,
            'path': str(test_file),
            'result': result,
            'timestamp': datetime.now()
        })
    
    def _generate_test_report(self):
        """Generate comprehensive test report"""
        report = {
            'summary': self._generate_summary(),
            'detailed_results': self.test_results,
            'recommendations': self._generate_recommendations()
        }
        
        # Save report
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        self._print_summary(report)
    
    def _generate_summary(self):
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for suite_results in self.test_results.values():
            for test_result in suite_results:
                total_tests += 1
                if test_result['result']['passed']:
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'timestamp': datetime.now()
        }
    
    def _generate_recommendations(self):
        """Generate test improvement recommendations"""
        recommendations = []
        
        # Find failing test suites
        failing_suites = [
            suite for suite, results in self.test_results.items()
            if any(not test['result']['passed'] for test in results)
        ]
        
        if failing_suites:
            recommendations.append(
                f"Fix failing test suites: {', '.join(failing_suites)}"
            )
        
        # Check test coverage
        total_tests = sum(len(results) for results in self.test_results.values())
        if total_tests < 100:
            recommendations.append(
                "Increase test coverage by adding more unit tests"
            )
        
        return recommendations
    
    def _print_summary(self, report):
        """Print test summary"""
        summary = report['summary']
        
        print("\n" + "="*60)
        print("TEST RUN SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print("="*60)
        
        if report['recommendations']:
            print("\nRECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"• {rec}")
```

This reference documentation provides comprehensive guidance for building production-ready RAG systems, covering architecture patterns, implementation strategies, testing approaches, deployment configurations, and operational considerations.

The goal is to serve as a practical reference rather than an exhaustive specification, allowing developers to adapt these patterns to their specific requirements while maintaining best practices and reliability standards.