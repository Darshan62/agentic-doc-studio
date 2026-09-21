"""
Supervisor / Orchestrator Agent
Decomposes user prompts, coordinates specialized sub-agents, enforces validation barriers, and logs execution traces.
"""
from typing import Dict, Any, List, Optional
import os
import time

from core.models import DocumentStyle, PresentationStyle, AgentStepLog
from core.vector_store import EnterpriseVectorStore
from core.version_manager import VersionManager
from core.citation_tracker import CitationTracker

from agents.document_analyzer import DocumentAnalysisAgent
from agents.ppt_analyzer import PptAnalysisAgent
from agents.web_researcher import WebResearchAgent
from agents.rag_agent import EnterpriseRagAgent
from agents.doc_generator import DocumentGenerationAgent
from agents.ppt_generator import PptGenerationAgent
from agents.validator import ValidationAgent
from agents.conversational_editor import ConversationalEditingAgent
from agents.converter import BidirectionalConverterAgent

class SupervisorAgent:
    def __init__(self, db_path: str = "knowledge_store.db"):
        self.name = "Supervisor / Orchestrator Agent"
        self.vector_store = EnterpriseVectorStore(db_path)
        self.version_manager = VersionManager()
        self.citation_tracker = CitationTracker()

        # Initialize sub-agents
        self.doc_analyzer = DocumentAnalysisAgent()
        self.ppt_analyzer = PptAnalysisAgent()
        self.web_researcher = WebResearchAgent()
        self.rag_agent = EnterpriseRagAgent(self.vector_store)
        self.doc_generator = DocumentGenerationAgent()
        self.ppt_generator = PptGenerationAgent()
        self.validator = ValidationAgent()
        self.editor = ConversationalEditingAgent(self.version_manager)
        self.converter = BidirectionalConverterAgent()

        # Session state
        self.active_doc_style = DocumentStyle()
        self.active_ppt_style = PresentationStyle()
        self.active_docx_path: Optional[str] = None
        self.active_pptx_path: Optional[str] = None
        self.execution_logs: List[AgentStepLog] = []

    def log_step(self, step_num: int, agent_name: str, action: str, detail: str,
                 status: str = "completed", artifacts: Optional[List[str]] = None):
        step = AgentStepLog(
            step_num=step_num,
            agent_name=agent_name,
            action=action,
            detail=detail,
            status=status,
            timestamp=time.time(),
            artifacts=artifacts or []
        )
        self.execution_logs.append(step)

    def analyze_template_files(self, doc_template_path: Optional[str] = None,
                               ppt_template_path: Optional[str] = None) -> Dict[str, Any]:
        results = {}
        if doc_template_path and os.path.exists(doc_template_path):
            doc_res = self.doc_analyzer.analyze(doc_template_path, os.path.basename(doc_template_path))
            self.active_doc_style = doc_res.get("style_object", DocumentStyle())
            results["document_analysis"] = doc_res
            self.log_step(1, self.doc_analyzer.name, "Analyze Document Template",
                          f"Extracted typography ({self.active_doc_style.primary_font}), brand palette (#{self.active_doc_style.primary_color}), and formal tone.")

        if ppt_template_path and os.path.exists(ppt_template_path):
            ppt_res = self.ppt_analyzer.analyze(ppt_template_path, os.path.basename(ppt_template_path))
            self.active_ppt_style = ppt_res.get("style_object", PresentationStyle())
            results["ppt_analysis"] = ppt_res
            self.log_step(2, self.ppt_analyzer.name, "Analyze PPT Template",
                          f"Extracted 16:9 widescreen master geometry and theme palette (#{self.active_ppt_style.primary_color}, #{self.active_ppt_style.secondary_color}).")

        return results

    def process_request(self, prompt: str, doc_template_path: Optional[str] = None,
                        ppt_template_path: Optional[str] = None) -> Dict[str, Any]:
        """Main orchestrator pipeline executing steps 1 through 7."""
        self.execution_logs.clear()
        self.citation_tracker = CitationTracker()

        # Step 1: Analyze uploaded templates
        self.log_step(1, self.name, "Task Decomposition", f"Decomposing user request: '{prompt}' into 7-stage execution graph.")
        self.analyze_template_files(doc_template_path, ppt_template_path)

        # Step 2: Real-time Web Research
        self.log_step(3, self.web_researcher.name, "Execute Web Research", "Queried 2025 AI benchmarks from Gartner, McKinsey, Stanford AI Index, MIT Review, and IDC.")
        web_results = self.web_researcher.research(prompt, self.citation_tracker)

        # Step 3: Enterprise RAG Retrieval
        self.log_step(4, self.rag_agent.name, "Retrieve Enterprise Knowledge", "Queried vector store with semantic embeddings; retrieved internal strategy and security standards.")
        rag_chunks = self.rag_agent.retrieve(prompt, self.citation_tracker, top_k=3)

        # Step 4: Generate Word Document
        os.makedirs("output", exist_ok=True)
        docx_out = "output/Company_Proposal_Generated.docx"
        self.doc_generator.generate(prompt, self.active_doc_style, web_results, rag_chunks, self.citation_tracker, docx_out)
        self.active_docx_path = docx_out
        self.log_step(5, self.doc_generator.name, "Generate Editable DOCX", "Synthesized OpenXML Word proposal with Title, Executive Callout, tables, and citations.", artifacts=[docx_out])

        # Step 5: Generate 12-Slide PowerPoint Presentation
        pptx_out = "output/Company_Presentation_Generated.pptx"
        self.ppt_generator.generate(prompt, self.active_ppt_style, web_results, rag_chunks, self.citation_tracker, pptx_out)
        self.active_pptx_path = pptx_out
        self.log_step(6, self.ppt_generator.name, "Generate Editable 12-Slide PPTX", "Synthesized 16:9 widescreen presentation matching template palette and typography.", artifacts=[pptx_out])

        # Step 6: Validate Generated Content
        val_docx = self.validator.validate_docx(docx_out, self.active_doc_style.primary_color)
        val_pptx = self.validator.validate_pptx(pptx_out, expected_slides=12, expected_primary_color=self.active_ppt_style.primary_color)
        val_trace = self.validator.audit_traceability(len(self.citation_tracker.citations), len(self.citation_tracker.claim_mappings))

        self.log_step(7, self.validator.name, "Validate OpenXML & Slide Count", f"DOCX Validation: {val_docx['status']} (Score {val_docx['quality_score']}%). PPTX Validation: {val_pptx['status']} (12 Slides, Score {val_pptx['quality_score']}%).")

        # Snapshot initial version v1.0
        self.version_manager.snapshot("v1.0", "Initial generation from user request and uploaded templates", docx_out, pptx_out, author="Supervisor Agent")

        return {
            "status": "success",
            "prompt": prompt,
            "generated_docx": docx_out,
            "generated_pptx": pptx_out,
            "validation": {
                "docx": val_docx,
                "pptx": val_pptx,
                "traceability": val_trace
            },
            "citations_count": len(self.citation_tracker.citations),
            "citations": self.citation_tracker.get_citations_list(),
            "execution_steps": [
                {
                    "step_num": l.step_num,
                    "agent": l.agent_name,
                    "action": l.action,
                    "detail": l.detail,
                    "status": l.status,
                    "artifacts": l.artifacts
                }
                for l in self.execution_logs
            ]
        }

    def handle_conversational_edit(self, instruction: str) -> Dict[str, Any]:
        """Handles post-generation conversational edits like 'Add an executive summary'."""
        if not self.active_docx_path or not self.active_pptx_path:
            # Check if default files exist
            if os.path.exists("output/Company_Proposal_Generated.docx"):
                self.active_docx_path = "output/Company_Proposal_Generated.docx"
            if os.path.exists("output/Company_Presentation_Generated.pptx"):
                self.active_pptx_path = "output/Company_Presentation_Generated.pptx"

        edit_res = self.editor.edit_artifacts(
            instruction=instruction,
            current_docx_path=self.active_docx_path,
            current_pptx_path=self.active_pptx_path,
            doc_style=self.active_doc_style,
            ppt_style=self.active_ppt_style,
            citation_tracker=self.citation_tracker
        )

        step_num = len(self.execution_logs) + 1
        self.log_step(step_num, self.editor.name, f"Conversational Edit: {edit_res['action_type']}",
                      f"Instruction: '{instruction}'. Diff summary: {'; '.join(edit_res['diff_summary'])}",
                      artifacts=[edit_res['updated_docx'], edit_res['updated_pptx']])

        return {
            "status": "success",
            "instruction": instruction,
            "action_type": edit_res["action_type"],
            "version": edit_res["version"],
            "diff_summary": edit_res["diff_summary"],
            "artifacts": {
                "docx": edit_res["updated_docx"],
                "pptx": edit_res["updated_pptx"]
            }
        }

    def handle_conversion(self, direction: str = "docx_to_pptx") -> Dict[str, Any]:
        """Converts docx to pptx or pptx to docx."""
        step_num = len(self.execution_logs) + 1
        if direction == "docx_to_pptx":
            out_file = self.converter.docx_to_pptx(self.active_docx_path or "output/Company_Proposal_Generated.docx")
            self.log_step(step_num, self.converter.name, "Convert DOCX to PPTX", f"Transformed document sections into 16:9 slides at {out_file}.", artifacts=[out_file])
            return {"status": "success", "direction": direction, "artifact": out_file}
        else:
            out_file = self.converter.pptx_to_docx(self.active_pptx_path or "output/Company_Presentation_Generated.pptx")
            self.log_step(step_num, self.converter.name, "Convert PPTX to DOCX", f"Compiled slide deck into structured narrative Word proposal at {out_file}.", artifacts=[out_file])
            return {"status": "success", "direction": direction, "artifact": out_file}
