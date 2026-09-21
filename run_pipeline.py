"""
Python Bridge CLI for the Multi-Agent System
Called by Express server endpoints to execute orchestration, edits, conversions, and diagnostics.
Outputs strictly valid JSON to stdout.
"""
import sys
import json
import os
from agents.supervisor import SupervisorAgent
from scripts.package_project import package_project

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing command argument"}))
        sys.exit(1)

    cmd = sys.argv[1]
    supervisor = SupervisorAgent("knowledge_store.db")

    if cmd == "orchestrate":
        # Read payload from stdin or argv
        payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else json.load(sys.stdin)
        prompt = payload.get("prompt", "Research the latest Generative AI trends and create a proposal and 12-slide presentation")
        doc_tpl = payload.get("doc_template", "templates_and_samples/Company_Proposal.docx")
        ppt_tpl = payload.get("ppt_template", "templates_and_samples/Company_Template.pptx")
        
        res = supervisor.process_request(prompt, doc_tpl, ppt_tpl)
        print(json.dumps(res, indent=2))

    elif cmd == "edit":
        payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else json.load(sys.stdin)
        instruction = payload.get("instruction", "Add an executive summary.")
        res = supervisor.handle_conversational_edit(instruction)
        print(json.dumps(res, indent=2))

    elif cmd == "convert":
        payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else json.load(sys.stdin)
        direction = payload.get("direction", "docx_to_pptx")
        res = supervisor.handle_conversion(direction)
        print(json.dumps(res, indent=2))

    elif cmd == "package_zip":
        zip_path = package_project()
        print(json.dumps({"status": "success", "zip_path": zip_path, "download_url": "/downloads/multi_agent_doc_ppt_system.zip"}))

    elif cmd == "get_status":
        history = supervisor.version_manager.get_history()
        count = supervisor.vector_store.count_chunks()
        indexed_docs = supervisor.vector_store.list_indexed_docs()
        print(json.dumps({
            "status": "ready",
            "kb_chunks_indexed": count,
            "kb_documents": indexed_docs,
            "versions_count": len(history),
            "versions": history,
            "sample_files": {
                "docx_template": "templates_and_samples/Company_Proposal.docx",
                "pptx_template": "templates_and_samples/Company_Template.pptx",
                "ocr_brief": "templates_and_samples/Scanned_Architecture_Brief.png"
            },
            "active_artifacts": {
                "docx": "output/Company_Proposal_Generated.docx" if os.path.exists("output/Company_Proposal_Generated.docx") else None,
                "pptx": "output/Company_Presentation_Generated.pptx" if os.path.exists("output/Company_Presentation_Generated.pptx") else None,
                "zip": "public/downloads/multi_agent_doc_ppt_system.zip" if os.path.exists("public/downloads/multi_agent_doc_ppt_system.zip") else None
            }
        }, indent=2))

    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))

if __name__ == "__main__":
    main()
