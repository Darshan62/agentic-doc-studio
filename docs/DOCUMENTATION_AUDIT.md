# STRICT DOCUMENTATION AUDIT

| Claim | Evidence File | Evidence Function/Class | Status | Correction Required |
|---|---|---|---|---|
| **Current LLM Provider is Gemini** | `core/llm_client.py` | `provider_name()` / `DEFAULT_PROVIDER` | OUTDATED | The default provider is Ollama (`qwen3:4b`), not Gemini. Gemini is supported but requires manual configuration. |
| **Web Research performs live search** | `agents/web_researcher.py` | `research()` | PARTIALLY VERIFIED | Live web search ONLY works if Gemini is configured. With the default Ollama, it is explicitly mocked/skipped. |
| **Multi-Agent Architecture (10+ agents)** | `agents/supervisor.py` | `SupervisorAgent.__init__` | VERIFIED | None (Already corrected to 10+). Active generation uses ~8 agents sequentially. |
| **Conversational Editing / Structured JSON** | `core/edit_schema.py` | `validate_command()` | VERIFIED | None. The schema strictly enforces OpenXML capabilities. |
| **Deterministic OpenXML Modification** | `core/docx_editor.py` | `DocxEditor.apply()` | VERIFIED | None. It uses `xml.etree.ElementTree` to edit native XML tags. |
| **Enterprise RAG** | `core/vector_store.py` | `compute_dense_embedding()` | PARTIALLY VERIFIED | It is local SQLite RAG using custom n-gram MD5 hashing, not a true semantic transformer embedding. "Enterprise" is a stretch for the current implementation. |
| **OCR / Vision** | `core/ocr_vision.py` | `read_image_text()` | VERIFIED | None. Uses `qwen3-vl:8b` via Ollama or Gemini vision. |
| **Citations** | `core/citation_tracker.py` | `CitationTracker` | VERIFIED | None. It maps source-level citations to `[Web-1]` and `[RAG-1]`. |
| **Versioning / Undo** | `core/version_manager.py` | `VersionManager.snapshot()` | VERIFIED | None. It copies exact file states into `versions/` directory. |
| **Security (No Auth/RBAC)** | `server.ts` | `app.post("/api/*")` | VERIFIED | None. Confirmed zero authentication and basic `safePath()` boundary checking. |

## Execution Flow Verified
1. **User Request** → React Frontend
2. **API Endpoint** → `server.ts` routes to `/api/workspace/chat` or `/api/orchestrate`.
3. **Python Bridge** → `spawn("python", ["run_pipeline.py", ...])`.
4. **Supervisor/Workspace** → Python executes pipeline.
5. **LLM** → `core/llm_client.py` sends prompt to Ollama (default).
6. **Structured JSON** → LLM returns JSON command.
7. **Validation** → `core/edit_schema.py` validates structure.
8. **Deterministic Editor** → `core/docx_editor.py` edits `xml.etree`.
9. **Modification** → File is saved to disk by `OoxmlPackage.to_bytes()`.
10. **Frontend** → JSON state returned via STDOUT to Node, Node responds to React.

## Audit Summary
- **Verified**: 7
- **Partially Verified**: 2
- **Outdated**: 1
- **Not Verified**: 0
- **Major Corrections Made**: Corrected LLM default to Ollama, clarified Web Research limitations, clarified RAG hashing limitation.
