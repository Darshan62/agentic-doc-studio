"""
End-to-End Test Suite for Enterprise Multi-Agent AI System
Validates OpenXML integrity, agent orchestration, RAG retrieval, 12-slide presentation generation, and conversational editing.
"""
import unittest
import os
import zipfile

from core.models import DocumentStyle, PresentationStyle
from core.ooxml_docx import DocxBuilder, DocxReader
from core.ooxml_pptx import PptxBuilder, PptxReader
from core.vector_store import EnterpriseVectorStore
from core.citation_tracker import CitationTracker
from core.version_manager import VersionManager

from agents.supervisor import SupervisorAgent
from agents.validator import ValidationAgent
from agents.converter import BidirectionalConverterAgent

class TestMultiAgentSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs("output", exist_ok=True)
        os.makedirs("versions", exist_ok=True)

    def test_01_docx_builder_reader(self):
        """Test DocxBuilder creates valid OpenXML package and DocxReader parses it."""
        path = "output/test_sample.docx"
        builder = DocxBuilder("Test Title", "Georgia", "Arial", "1B365D", "00A3E0")
        builder.add_title_block("TEST PROPOSAL", "Testing Docx Builder")
        builder.add_heading_1("1. Section One")
        builder.add_paragraph("This is a test paragraph with Georgian typography.")
        builder.add_callout("Test Callout", "Executive callout test content.")
        builder.add_table(["Col A", "Col B"], [["Row 1A", "Row 1B"], ["Row 2A", "Row 2B"]])
        builder.save(path)

        self.assertTrue(os.path.exists(path))
        # Verify valid zip
        with zipfile.ZipFile(path) as zf:
            self.assertIn("word/document.xml", zf.namelist())
            self.assertIn("[Content_Types].xml", zf.namelist())

        # Test reader
        reader = DocxReader(path)
        struct = reader.extract_structure()
        self.assertIn("TEST PROPOSAL", struct.get("title", ""))
        self.assertGreaterEqual(struct.get("headings_count", 0), 1)
        self.assertIn("1B365D", struct.get("detected_colors", []))

    def test_02_pptx_builder_reader(self):
        """Test PptxBuilder creates valid 16:9 presentation with 12 slides."""
        path = "output/test_12_slides.pptx"
        builder = PptxBuilder("Test 12 Slides", "0F2D59", "2563EB", "10B981")
        
        # 12 distinct slides
        builder.add_title_slide("Title", "Subtitle")
        builder.add_executive_summary_slide("Exec", "Summary", ["H1", "H2", "H3"])
        for i in range(3, 13):
            builder.add_three_pillar_slide(f"Slide {i}", f"Sub {i}", [{"title": f"Pillar {i}", "desc": "Desc", "metric": "100%"}])

        builder.save(path)
        self.assertTrue(os.path.exists(path))

        # Check zip contents
        with zipfile.ZipFile(path) as zf:
            self.assertIn("ppt/presentation.xml", zf.namelist())
            self.assertIn("ppt/slides/slide1.xml", zf.namelist())
            self.assertIn("ppt/slides/slide12.xml", zf.namelist())

        reader = PptxReader(path)
        struct = reader.extract_structure()
        self.assertEqual(struct.get("slide_count"), 12)
        self.assertEqual(len(struct.get("titles", [])), 12)

    def test_03_vector_store_rag(self):
        """Test dense vector indexing and cosine similarity retrieval."""
        vs = EnterpriseVectorStore("knowledge_store.db")
        chunks = vs.search("multi-agent architecture and autonomous task execution", top_k=3)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertGreaterEqual(chunks[0].similarity_score, 0.20)
        self.assertIsNotNone(chunks[0].content)

    def test_04_supervisor_full_pipeline(self):
        """Test Supervisor orchestrating full workflow to generate proposal DOCX and 12-slide PPTX."""
        supervisor = SupervisorAgent("knowledge_store.db")
        result = supervisor.process_request(
            prompt="Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.",
            doc_template_path="templates_and_samples/Company_Proposal.docx",
            ppt_template_path="templates_and_samples/Company_Template.pptx"
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(result["generated_docx"]))
        self.assertTrue(os.path.exists(result["generated_pptx"]))

        # Check validation scorecard
        val = result["validation"]
        self.assertEqual(val["docx"]["status"], "PASSED")
        self.assertEqual(val["pptx"]["status"], "PASSED")
        self.assertEqual(val["pptx"]["checks"]["actual_slides"], 12)
        self.assertEqual(val["pptx"]["checks"]["exact_slide_count_met"], True)
        self.assertGreaterEqual(result["citations_count"], 4)
        self.assertGreaterEqual(len(result["execution_steps"]), 6)

    def test_05_conversational_editing_and_versioning(self):
        """Test conversational revisions and version management."""
        supervisor = SupervisorAgent("knowledge_store.db")
        # Initialize files first
        supervisor.process_request(
            prompt="Initial proposal generation",
            doc_template_path="templates_and_samples/Company_Proposal.docx",
            ppt_template_path="templates_and_samples/Company_Template.pptx"
        )

        # Test prompt 1: "Add an executive summary."
        res1 = supervisor.handle_conversational_edit("Add an executive summary.")
        self.assertEqual(res1["status"], "success")
        self.assertIn("executive summary", res1["diff_summary"][0].lower())

        # Test prompt 2: "Make the presentation more concise."
        res2 = supervisor.handle_conversational_edit("Make the presentation more concise.")
        self.assertEqual(res2["status"], "success")

        # Test prompt 3: "Add a competitive analysis section."
        res3 = supervisor.handle_conversational_edit("Add a competitive analysis section.")
        self.assertEqual(res3["status"], "success")

        # Verify version history has captured snapshots
        history = supervisor.version_manager.get_history()
        self.assertGreaterEqual(len(history), 3)

    def test_06_bidirectional_converter(self):
        """Test converting DOCX to PPTX and PPTX to DOCX."""
        converter = BidirectionalConverterAgent()
        pptx_out = converter.docx_to_pptx("output/Company_Proposal_Generated.docx", "output/test_converted.pptx")
        self.assertTrue(os.path.exists(pptx_out))

        docx_out = converter.pptx_to_docx("output/Company_Presentation_Generated.pptx", "output/test_converted.docx")
        self.assertTrue(os.path.exists(docx_out))

if __name__ == "__main__":
    unittest.main()
