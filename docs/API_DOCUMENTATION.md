# API Documentation

The REST API is implemented in Express/TypeScript (`server.ts`).

## Endpoints

| Method | Endpoint | Purpose | Request | Response |
|---|---|---|---|---|
| GET | `/api/status` | System health & DB stats | None | `{status, chunks, docs}` |
| POST | `/api/orchestrate` | Main generation endpoint | `{prompt, doc_template, ppt_template, focus_docs}` | JSON with generation status & steps |
| POST | `/api/upload` | Upload & ingest file | `{filename, base64Content}` | `{status, filename, path, ingest}` |
| POST | `/api/conversational-edit`| Legacy edit endpoint | `{instruction}` | `{status, diff, artifacts}` |
| POST | `/api/workspace/open` | Open file in workspace | `{path}` | `{status, state}` |
| POST | `/api/workspace/chat` | Send edit intent | `{message, selection, current_slide}` | `{status, state}` |
| POST | `/api/workspace/undo` | Revert to previous version| None | `{status, state}` |
| GET | `/api/download/:name` | Download generated file | None | Binary file |

## Example Requests

**Generation Request**
```json
POST /api/orchestrate
{
  "prompt": "Create an AI adoption proposal",
  "doc_template": "templates_and_samples/Company_Proposal.docx",
  "ppt_template": "templates_and_samples/Company_Template.pptx"
}
```

**Conversational Editing**
```json
POST /api/workspace/chat
{
  "message": "Make this text blue",
  "selection": { "type": "paragraph", "text": "Existing text..." }
}
```

## Security & Error Handling
Currently, the API has **no authentication**. It relies on `path.basename` and custom `safePath` logic to prevent directory traversal, but this is insufficient for enterprise use.
- **Errors**: Propagated from the Python bridge child process as JSON `{"error": "message"}`. Status codes 400 for bad input, 500 for backend crashes, 413 for payload too large.
