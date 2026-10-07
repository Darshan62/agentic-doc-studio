# RAG Documentation (Retrieval-Augmented Generation)

## Pipeline Implementation
The current Enterprise RAG implementation is built into `core/vector_store.py`.

1. **Ingestion**: Documents (`.txt`, `.pdf`, `.docx`) are uploaded and parsed.
2. **Chunking**: Sliding-window chunking (350 characters, 60 char overlap).
3. **Embedding**: Uses a local, deterministic N-gram MD5 hashing algorithm (`compute_dense_embedding`) to map text to a 128-dimensional dense vector. This avoids requiring a heavy local embedding model.
4. **Storage**: Vectors and metadata are stored in local SQLite (`knowledge_store.db`).
5. **Retrieval**: Standard cosine similarity search across the entire SQLite table, extracting top-K chunks.
6. **Grounding**: Chunks are injected into the LLM system prompt.
7. **Traceability**: The LLM adds `[RAG-X]` inline citations.

## Limitations
- The hashing-based embedding is a simplified heuristic and lacks deep semantic understanding compared to transformer-based embeddings (like `text-embedding-3-small` or `BGE`).
- SQLite table scans do not scale to millions of vectors.

## Production Recommendation
For an enterprise environment, the architecture must change to:
- **Embedding Model**: Use standard LLM embeddings (e.g. OpenAI, Cohere) or a dedicated local model (e.g. `nomic-embed-text`).
- **Vector DB**: Pinecone, pgvector (PostgreSQL), Weaviate, or Qdrant.
- **Advanced RAG**: Implement Hybrid Search (BM25 + Semantic), Reranking (e.g., Cohere Rerank), and Metadata Filtering.
