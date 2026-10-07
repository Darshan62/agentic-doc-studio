# System Architecture

## High-Level Architecture

```mermaid
flowchart TD
    User([User]) -->|HTTP/REST| Frontend[Vite + React Frontend]
    Frontend -->|POST /api/orchestrate| API[Express API Layer / server.ts]
    
    API -->|spawn python| PythonBridge[run_pipeline.py]
    PythonBridge --> Supervisor[Supervisor / Orchestrator]
    
    subgraph Multi-Agent System
        Supervisor --> DocAnalysis[Document Analyzer]
        Supervisor --> PptAnalysis[PPT Analyzer]
        Supervisor --> WebSearch[Web Researcher]
        Supervisor --> RAG[RAG Retrieval Agent]
        Supervisor --> Writer[Content Writer Agent]
        Supervisor --> DocGen[Document Generation Agent]
        Supervisor --> PptGen[PPT Generation Agent]
        Supervisor --> Validator[Validation Agent]
    end
    
    subgraph Core Engines
        DocGen --> DocxEngine[Native OpenXML DOCX Engine]
        PptGen --> PptxEngine[Native OpenXML PPTX Engine]
    end
    
    subgraph Storage
        RAG --> SQLite[(SQLite Vector Store)]
        DocxEngine --> FS[(Local File System)]
        PptxEngine --> FS
    end
    
    FS --> Preview[Workspace Preview & Download]
    Preview --> User
```

## Conversational Editing Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Server (TS)
    participant Editor (Python)
    participant LLM
    participant OpenXML

    User->>Frontend: Selects paragraph + "Make this blue"
    Frontend->>Server: POST /api/workspace/chat {message, selection}
    Server->>Editor: Spawn python workspace_edit.py
    Editor->>LLM: Prompt with selection context
    LLM-->>Editor: JSON {action: "update_style", target: {...}, changes: {color: "0000FF"}}
    Editor->>OpenXML: Apply exact deterministic change
    OpenXML-->>Editor: Save v1.1.docx
    Editor-->>Server: Return updated state.json
    Server-->>Frontend: Success (updates preview)
    Frontend-->>User: Visual update
```

## Storage Architecture
- **Vector Store**: Currently local SQLite (`knowledge_store.db`).
- **File System**: `templates_and_samples/uploads` for ingest, `output/` for generated files, `output/workspace/` for live editing versions.
- **State**: Ephemeral session state stored in `output/session.json`.

## Production Recommendation
For enterprise production, the architecture must evolve:
1. **API Layer**: Migrate Python bridge from `child_process.spawn` to a dedicated FastAPI microservice to avoid cold-start overhead.
2. **Storage**: Replace local SQLite with Pinecone/pgvector. Replace local filesystem with AWS S3 / Azure Blob Storage.
3. **Queueing**: Add Celery or Redis for long-running generation tasks to prevent HTTP timeouts.
