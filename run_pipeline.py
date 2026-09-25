"""
Python bridge called by the Express server:  python run_pipeline.py <command> '<json payload>'
Always prints one JSON object. On failure it prints {"error": ...} and exits with code 1.
"""
import json
import os
import sys

from agents.supervisor import SupervisorAgent
from agents.workspace_agent import run_workspace
from core.gemini_client import GeminiError, check_api_key
from scripts.package_project import package_project


def get_status(supervisor: SupervisorAgent) -> dict:
    return {
        "status": "ready",
        "kb_chunks_indexed": supervisor.vector_store.count_chunks(),
        "kb_documents": supervisor.vector_store.list_indexed_docs(),
        "versions_count": len(supervisor.version_manager.get_history()),
        "versions": supervisor.version_manager.get_history(),
        "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY")),
        "gemini_key_status": check_api_key(),
    }


def run(command: str, payload: dict) -> dict:
    if command == "workspace":
        # The editor workspace doesn't need the knowledge base, so skip building the supervisor
        return run_workspace(payload)
    supervisor = SupervisorAgent("knowledge_store.db")
    if command == "orchestrate":
        return supervisor.process_request(payload["prompt"], payload["doc_template"], payload["ppt_template"],
                                          payload.get("focus_docs") or [])
    if command == "edit":
        return supervisor.handle_conversational_edit(payload["instruction"])
    if command == "convert":
        return supervisor.handle_conversion(payload.get("direction", "docx_to_pptx"))
    if command == "ingest":
        return supervisor.ingest_file(payload["path"])
    if command == "search":
        return supervisor.search(payload["query"])
    if command == "get_status":
        return get_status(supervisor)
    if command == "package_zip":
        return {"status": "success", "zip_path": package_project()}
    raise ValueError(f"Unknown command: {command}")


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing command argument"}))
        sys.exit(1)

    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        print(json.dumps(run(sys.argv[1], payload)))
    except (GeminiError, ValueError, KeyError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
