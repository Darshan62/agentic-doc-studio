# Current vs Production Architecture

This document explicitly separates what is actually implemented today in the POC versus what is required for an enterprise production deployment.

## CURRENT PROJECT (What works today)
- **Local LLM via Ollama**: The system successfully runs entirely locally using `qwen3:4b` and `qwen3-vl:8b`. 
- **OpenXML Generation**: Native, deterministic Python generation of `.docx` and `.pptx` (no MS Office binaries required).
- **Conversational Editing**: Works via rigid JSON intent mapping and targeted XML updates.
- **OCR/Vision**: Extracts text from images and PDFs using vision models.
- **Versioning**: Takes file snapshots per instruction for simple undo/redo.

## PARTIAL (Works but with severe limitations)
- **RAG Pipeline**: Implemented locally using SQLite. **Limitation**: Uses a custom N-gram MD5 hashing algorithm instead of dense semantic embeddings, leading to poor semantic matching.
- **Web Research**: Implemented via Gemini Grounding. **Limitation**: Only works if Gemini is the active provider. With Ollama, web search is skipped.
- **Orchestration**: A Supervisor agent exists. **Limitation**: It is a static, hardcoded sequential pipeline rather than a dynamic LLM-driven graph planner.
- **API**: Functional Express backend. **Limitation**: Spawns Python CLI via `child_process.spawn` for every request, introducing massive cold-start latency and preventing concurrent scaling.

## MOCK/STUB (Simulated)
- None. The system avoids mocks (aside from the Python `unittest` suite which heavily mocks the LLM).

## PLANNED (Future Implementation)
- Claim-level citation mapping (tracking exact sentence boundaries).
- Hybrid RAG search (BM25 + Semantic).
- Multi-modal LLM routing via LiteLLM.

## PRODUCTION ARCHITECTURE (Enterprise Recommendation)
To move this POC to enterprise production, the following architecture is required:

| Component | Current POC | Production Recommendation |
|---|---|---|
| **Backend Framework** | Node.js + `child_process.spawn` | **FastAPI** (Persistent Python Microservice) |
| **Vector Database** | Local SQLite (Hashing) | **Pinecone** or **pgvector** |
| **Embeddings** | Custom MD5 N-gram | **OpenAI `text-embedding-3-small`** |
| **Authentication** | None | **OAuth2 / OIDC** with JWT |
| **Object Storage** | Local File System (`output/`) | **AWS S3** / Azure Blob Storage |
| **Async Tasks** | Synchronous HTTP Wait | **Celery + Redis** |
| **Orchestration** | Static Sequential Pipeline | **LangGraph** (Dynamic DAG) |
| **Observability** | CLI `print()` logs | **OpenTelemetry** + Datadog / Grafana |
