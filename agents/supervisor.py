"""
Supervisor / Orchestrator Agent
Runs the agents in order and keeps the session (content, templates, sources) in output/session.json.
Every API call starts a new Python process, so anything needed later must be saved to disk.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from agents.content_writer import ContentWriterAgent
from agents.converter import BidirectionalConverterAgent
from agents.doc_generator import DocumentGenerationAgent
from agents.document_analyzer import DocumentAnalysisAgent
from agents.ingestion_agent import IngestionAgent
from agents.ppt_analyzer import PptAnalysisAgent
from agents.ppt_generator import PptGenerationAgent
from agents.rag_agent import EnterpriseRagAgent
from agents.validator import ValidationAgent
from agents.web_researcher import WebResearchAgent
from core.citation_tracker import CitationTracker
from core.models import DocumentStyle, PresentationStyle
from core.vector_store import EnterpriseVectorStore
from core.version_manager import VersionManager

SESSION_FILE = "output/session.json"
DOCX_OUT = "output/Company_Proposal_Generated.docx"
PPTX_OUT = "output/Company_Presentation_Generated.pptx"
SAMPLE_KB_DIR = "templates_and_samples/knowledge_base"


class SupervisorAgent:
    def __init__(self, db_path: str = "knowledge_store.db"):
        self.name = "Supervisor Agent"
        self.vector_store = EnterpriseVectorStore(db_path)
        self.version_manager = VersionManager()
        self.doc_analyzer = DocumentAnalysisAgent()
        self.ppt_analyzer = PptAnalysisAgent()
        self.web_researcher = WebResearchAgent()
        self.rag_agent = EnterpriseRagAgent(self.vector_store)
        self.writer = ContentWriterAgent()
        self.doc_generator = DocumentGenerationAgent()
        self.ppt_generator = PptGenerationAgent()
        self.validator = ValidationAgent()
        self.converter = BidirectionalConverterAgent()
        self.ingestion = IngestionAgent(self.vector_store)
        self.steps: List[Dict[str, Any]] = []
        self.seed_knowledge_base()

    def seed_knowledge_base(self) -> None:
        """On a fresh install the database is empty, so index the bundled sample documents."""
        if self.vector_store.count_chunks() > 0 or not os.path.isdir(SAMPLE_KB_DIR):
            return
        for filename in sorted(os.listdir(SAMPLE_KB_DIR)):
            self.ingestion.ingest(os.path.join(SAMPLE_KB_DIR, filename))

    def log_step(self, agent: str, action: str, detail: str, artifacts: Optional[List[str]] = None) -> None:
        self.steps.append({"step_num": len(self.steps) + 1, "agent": agent, "action": action,
                           "detail": detail, "status": "completed", "artifacts": artifacts or [],
                           "timestamp": time.time()})

    # ---------- session ----------
    def load_session(self) -> Dict[str, Any]:
        if not os.path.exists(SESSION_FILE):
            raise ValueError("Nothing generated yet. Run a generation first.")
        with open(SESSION_FILE, encoding="utf-8") as f:
            return json.load(f)

    def save_session(self, session: Dict[str, Any]) -> None:
        os.makedirs("output", exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

    def load_styles(self, doc_template: str, ppt_template: str) -> Tuple[DocumentStyle, PresentationStyle]:
        doc_style = self.doc_analyzer.analyze(doc_template)["style_object"]
        ppt_style = self.ppt_analyzer.analyze(ppt_template)["style_object"]
        return doc_style, ppt_style

    def build_files(self, content: Dict[str, Any], citations: List[Dict[str, Any]],
                    doc_style: DocumentStyle, ppt_style: PresentationStyle) -> None:
        os.makedirs("output", exist_ok=True)
        self.doc_generator.generate(content["document"], doc_style, citations, DOCX_OUT)
        self.ppt_generator.generate(content["deck"], ppt_style, citations, PPTX_OUT)

    # ---------- main pipeline ----------
    def process_request(self, prompt: str, doc_template: str, ppt_template: str) -> Dict[str, Any]:
        citation_tracker = CitationTracker()

        doc_style, ppt_style = self.load_styles(doc_template, ppt_template)
        self.log_step(self.doc_analyzer.name, "Analyze templates",
                      f"Word: {doc_style.primary_font}, #{doc_style.primary_color}. "
                      f"PowerPoint: {ppt_style.primary_font}, #{ppt_style.primary_color}.")

        web_results = self.web_researcher.research(prompt, citation_tracker)
        sources = [r for r in web_results if r.id]
        self.log_step(self.web_researcher.name, "Google Search via Gemini",
                      f"Found {len(sources)} web sources: " + ", ".join(r.title for r in sources))

        rag_chunks = self.rag_agent.retrieve(prompt, citation_tracker)
        docs_used = sorted({c.source_doc for c in rag_chunks})
        self.log_step(self.rag_agent.name, "Search knowledge base",
                      f"Retrieved {len(rag_chunks)} chunks from: " + ", ".join(docs_used))

        content = self.writer.write(prompt, doc_style.tone, web_results, rag_chunks)
        self.log_step(self.writer.name, "Write content with Gemini",
                      f"{len(content['document']['sections'])} document sections, {len(content['deck']['slides'])} slides.")

        citations = citation_tracker.get_citations_list()
        self.build_files(content, citations, doc_style, ppt_style)
        self.log_step(self.doc_generator.name, "Build DOCX and PPTX", "Rendered the content with the template styles.",
                      artifacts=[DOCX_OUT, PPTX_OUT])

        validation = self.validate(content, citations, doc_style, ppt_style)

        self.version_manager.reset()
        self.version_manager.snapshot(prompt, DOCX_OUT, PPTX_OUT, author=self.name,
                                      changes=["Generated the proposal and slide deck."])
        self.save_session({"prompt": prompt, "doc_template": doc_template, "ppt_template": ppt_template,
                           "content": content, "citations": citations})

        return {"status": "success", "prompt": prompt, "generated_docx": DOCX_OUT, "generated_pptx": PPTX_OUT,
                "content": content, "validation": validation, "citations_count": len(citations),
                "citations": citations, "execution_steps": self.steps}

    def validate(self, content: Dict[str, Any], citations: List[Dict[str, Any]],
                 doc_style: DocumentStyle, ppt_style: PresentationStyle) -> Dict[str, Any]:
        expected_slides = len(content["deck"]["slides"]) + 2  # + title slide + sources slide
        validation = {
            "docx": self.validator.validate_docx(DOCX_OUT, doc_style.primary_color),
            "pptx": self.validator.validate_pptx(PPTX_OUT, expected_slides, ppt_style.primary_color),
            "traceability": self.validator.audit_citations(content, citations),
        }
        self.log_step(self.validator.name, "Validate files",
                      f"DOCX {validation['docx']['status']}, PPTX {validation['pptx']['status']}, "
                      f"{validation['traceability']['sources_cited_in_text']} of {len(citations)} sources cited.")
        return validation

    # ---------- follow-up actions ----------
    def handle_conversational_edit(self, instruction: str) -> Dict[str, Any]:
        session = self.load_session()
        content, changes = self.writer.revise(session["content"], instruction)

        doc_style, ppt_style = self.load_styles(session["doc_template"], session["ppt_template"])
        self.build_files(content, session["citations"], doc_style, ppt_style)
        record = self.version_manager.snapshot(instruction, DOCX_OUT, PPTX_OUT,
                                               author="Conversational Edit", changes=changes)
        self.save_session({**session, "content": content})

        return {"status": "success", "instruction": instruction, "version": record["version"],
                "diff_summary": changes, "content": content,
                "artifacts": {"docx": DOCX_OUT, "pptx": PPTX_OUT}}

    def handle_conversion(self, direction: str) -> Dict[str, Any]:
        session = self.load_session()
        if direction == "docx_to_pptx":
            out_file = self.converter.docx_to_pptx(session["content"], session["citations"])
        else:
            out_file = self.converter.pptx_to_docx(session["content"], session["citations"])
        return {"status": "success", "direction": direction, "artifact": out_file}

    def ingest_file(self, path: str) -> Dict[str, Any]:
        return {"status": "success", **self.ingestion.ingest(path)}

    def search(self, query: str) -> Dict[str, Any]:
        chunks = self.vector_store.search(query, top_k=5)
        return {"status": "success", "results": [
            {"title": c.title, "doc": c.source_doc, "similarity": c.similarity_score, "text": c.content}
            for c in chunks]}
