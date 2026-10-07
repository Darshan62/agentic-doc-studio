# Security Documentation

## Threat Model

| Asset | Threat | Attack Vector | Impact | Mitigation (Current/Planned) |
|---|---|---|---|---|
| OpenXML Engine | Malicious Document | Uploading `.docx` with XXE or malware payloads. | Server compromise. | **Planned**: Implement strict XML parsing with `defusedxml` and sandboxed execution. |
| Filesystem | Path Traversal | Sending `../../windows/system32` in `/api/upload` | Info disclosure. | **Current**: Addressed via `path.basename` and `safePath()` boundary checking. |
| API / LLM | Prompt Injection | User sends instructions designed to hijack the LLM payload. | Unintended output. | **Planned**: Isolate untrusted inputs, use rigid JSON schemas to force constraints. |
| Vector DB | RAG Poisoning | Uploading a document containing prompt injection ("IGNORE ALL INSTRUCTIONS"). | Corrupted outputs. | **Planned**: Pre-flight content sanitization before embedding. |

## Application Security Gaps (POC Level)
- **No Authentication/RBAC**: The system currently runs as a local/internal tool (`HOST = "127.0.0.1"`). Any user on the network can access the API.
- **Lack of Secrets Management**: API keys (`GEMINI_API_KEY`) are in `.env`.
- **In-Memory/Local Storage**: Documents are stored unencrypted on the filesystem.

## Enterprise Security Requirements
- Implement OAuth2 / OIDC authentication.
- Implement RBAC (Role-Based Access Control) for document boundaries in RAG.
- Implement strict MIME type validation (currently relies purely on file extensions).
- Store documents in S3 with server-side encryption (SSE-KMS).
- Ensure LLM prompt safety using guardrail models.
