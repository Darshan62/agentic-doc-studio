"""
Tests for the multi-agent pipeline. Gemini is mocked, and every test runs in its own temp folder.
Run:  python -m unittest tests.test_multi_agent_system
"""
import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

from agents.document_analyzer import brand_colors
from agents.ingestion_agent import IngestionAgent
from agents.supervisor import SupervisorAgent
from core.gemini_client import GeminiError, ask_gemini, ask_gemini_json
from core.ocr_vision import read_image_text
from core.ooxml_docx import DocxBuilder, DocxReader
from core.ooxml_pptx import PptxBuilder, PptxReader
from core.vector_store import EnterpriseVectorStore
from scripts.package_project import package_project

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_TEMPLATE = os.path.join(REPO, "templates_and_samples", "Company_Proposal.docx")
PPT_TEMPLATE = os.path.join(REPO, "templates_and_samples", "Company_Template.pptx")
FILLER = " ".join(["solar adoption keeps growing across regions"] * 8)


def make_content(title: str = "Solar Energy Proposal") -> dict:
    layouts = [
        {"layout": "bullets", "title": "Summary", "summary": "Why now [Web-1]", "points": ["Costs fell [RAG-1]"]},
        {"layout": "two_column", "title": "Compare", "left_title": "A", "left_points": ["a"],
         "right_title": "B", "right_points": ["b"]},
        {"layout": "three_pillar", "title": "Pillars", "subtitle": "s",
         "pillars": [{"title": "P1", "desc": "d", "metric": "10%"}]},
        {"layout": "metrics", "title": "Numbers", "metrics": [{"value": "5x", "label": "Growth", "desc": "d"}]},
        {"layout": "table", "title": "Table", "headers": ["H1", "H2"], "rows": [["1", "2"]]},
    ]
    return {
        "document": {
            "title": title, "subtitle": "Plan", "executive_summary": "Solar is cheaper [Web-1].",
            "sections": [{"heading": f"Section {i}", "paragraphs": [FILLER], "bullets": ["Point [RAG-1]"],
                          "table": None} for i in range(1, 5)],
        },
        "deck": {"title": title, "subtitle": "Plan", "slides": layouts * 2},  # 10 content slides
    }


def fake_web_search(prompt, **kwargs):
    return "Solar prices fell 90% since 2010.", [{"title": "IEA Solar Report", "url": "https://iea.org/solar"}]


def write_minimal_pdf(path: str, text: str) -> None:
    """Writes a tiny one-page PDF with an uncompressed text stream."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_at)
    with open(path, "wb") as f:
        f.write(out)


class TempFolderTest(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.store = EnterpriseVectorStore("test.db")
        self.store.index_document("solar_notes.txt", "Solar notes", "Solar panel costs fell sharply.\n" * 3)

    def tearDown(self):
        self.store.conn.close()
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestFileBuilders(TempFolderTest):
    def test_docx_round_trip_ranks_colors_by_frequency(self):
        builder = DocxBuilder("T", "Georgia", "Arial", "1B365D", "00A3E0")
        builder.add_title_block("TEST PROPOSAL", "Sub")
        builder.add_heading_1("1. Section")
        builder.save("sample.docx")

        with zipfile.ZipFile("sample.docx") as zf:
            self.assertIn("word/document.xml", zf.namelist())
        structure = DocxReader("sample.docx").extract_structure()
        self.assertIn("TEST PROPOSAL", structure["title"])
        self.assertEqual(structure["detected_colors"][0], "1B365D")

    def test_greys_are_not_brand_colors(self):
        self.assertEqual(brand_colors(["222222", "ffffff", "1b365d", "000000"]), ["1B365D"])

    def test_pptx_has_twelve_slides(self):
        builder = PptxBuilder("Deck", "0F2D59", "2563EB", "10B981")
        builder.add_title_slide("Title", "Sub")
        for i in range(11):
            builder.add_three_pillar_slide(f"Slide {i}", "s", [{"title": "p", "desc": "d", "metric": "1"}])
        builder.save("deck.pptx")
        self.assertEqual(PptxReader("deck.pptx").extract_structure()["slide_count"], 12)


class TestPackaging(TempFolderTest):
    def test_zip_leaves_out_secrets_outputs_and_uploads(self):
        for path in (".env", ".env.example", "app.py", "output/result.docx", "templates_and_samples/uploads/cv.pdf"):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write("x")

        with zipfile.ZipFile(package_project("public/downloads/project.zip")) as zf:
            names = sorted(n.replace("\\", "/") for n in zf.namelist())
        self.assertEqual(names, [".env.example", "app.py"])


class TestIngestion(TempFolderTest):
    def test_pdf_upload_becomes_searchable(self):
        write_minimal_pdf("paper.pdf", "Quantum batteries store energy differently")
        result = IngestionAgent(self.store).ingest("paper.pdf")

        self.assertEqual(result["chunks_indexed"], 1)
        top = self.store.search("quantum batteries", top_k=1)[0]
        self.assertEqual(top.source_doc, "paper.pdf")

    def test_reupload_replaces_old_chunks(self):
        agent = IngestionAgent(self.store)
        with open("notes.txt", "w") as f:
            f.write("first version\n" * 50)
        agent.ingest("notes.txt")
        with open("notes.txt", "w") as f:
            f.write("second version")
        agent.ingest("notes.txt")
        chunks = [c for c in self.store.search("version", top_k=50) if c.source_doc == "notes.txt"]
        self.assertEqual([c.content for c in chunks], ["second version"])

    def test_unsupported_file_type_is_rejected(self):
        with open("script.exe", "w") as f:
            f.write("x")
        with self.assertRaises(ValueError):
            IngestionAgent(self.store).ingest("script.exe")


@mock.patch("agents.web_researcher.ask_gemini", side_effect=fake_web_search)
class TestPipeline(TempFolderTest):
    def run_generation(self, supervisor: SupervisorAgent) -> dict:
        with mock.patch("agents.content_writer.ask_gemini_json", return_value=make_content()):
            return supervisor.process_request("Proposal on solar energy", DOC_TEMPLATE, PPT_TEMPLATE)

    def test_generation_builds_valid_files_with_citations(self, _search):
        result = self.run_generation(SupervisorAgent("test.db"))

        self.assertEqual(result["validation"]["docx"]["status"], "PASSED")
        self.assertEqual(result["validation"]["pptx"]["status"], "PASSED")
        self.assertEqual(result["validation"]["pptx"]["checks"]["actual_slides"], 12)
        ids = [c["id"] for c in result["citations"]]
        self.assertIn("[Web-1]", ids)
        self.assertIn("[RAG-1]", ids)
        self.assertEqual(result["validation"]["traceability"]["status"], "PASSED")

    def test_edit_works_from_a_fresh_process(self, _search):
        self.run_generation(SupervisorAgent("test.db"))

        # A new SupervisorAgent mimics the next API call (new Python process)
        revised = {"content": make_content("Revised Title"), "changes": ["Renamed the title"]}
        with mock.patch("agents.content_writer.ask_gemini_json", return_value=revised):
            result = SupervisorAgent("test.db").handle_conversational_edit("Rename the title")

        self.assertEqual(result["version"], "v1.1")
        self.assertEqual(result["diff_summary"], ["Renamed the title"])
        self.assertIn("Revised Title", DocxReader(result["artifacts"]["docx"]).extract_structure()["title"])
        self.assertEqual(len(SupervisorAgent("test.db").version_manager.get_history()), 2)

    def test_conversion_in_both_directions(self, _search):
        self.run_generation(SupervisorAgent("test.db"))
        supervisor = SupervisorAgent("test.db")

        pptx = supervisor.handle_conversion("docx_to_pptx")["artifact"]
        docx = supervisor.handle_conversion("pptx_to_docx")["artifact"]
        self.assertEqual(PptxReader(pptx).extract_structure()["slide_count"], 4 + 2)
        self.assertGreater(DocxReader(docx).extract_structure()["word_count"], 0)

    def test_edit_before_generation_gives_clear_error(self, _search):
        with self.assertRaises(ValueError):
            SupervisorAgent("test.db").handle_conversational_edit("Add a summary")


def fake_http_response(body: dict) -> mock.MagicMock:
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(json.dumps(body).encode())
    return response


@mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
class TestGeminiClient(unittest.TestCase):
    def test_missing_api_key_raises(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaises(GeminiError):
                ask_gemini("hello")

    def test_returns_text_and_web_sources(self):
        body = {"candidates": [{
            "content": {"parts": [{"text": "Answer"}]},
            "groundingMetadata": {"groundingChunks": [{"web": {"title": "IEA", "uri": "https://iea.org"}}]},
        }]}
        with mock.patch("urllib.request.urlopen", return_value=fake_http_response(body)) as urlopen:
            text, sources = ask_gemini("q", use_web_search=True)

        self.assertEqual(text, "Answer")
        self.assertEqual(sources, [{"title": "IEA", "url": "https://iea.org"}])
        sent = json.loads(urlopen.call_args[0][0].data)
        self.assertEqual(sent["tools"], [{"google_search": {}}])

    def test_invalid_json_answer_raises(self):
        body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
        with mock.patch("urllib.request.urlopen", return_value=fake_http_response(body)):
            with self.assertRaises(GeminiError):
                ask_gemini_json("q")

    def test_http_error_becomes_gemini_error(self):
        error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)  # type: ignore[arg-type]
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(GeminiError, "HTTP 401"):
                ask_gemini("q")

    def test_image_text_is_read_with_gemini(self):
        with open(os.path.join(REPO, "templates_and_samples", "Scanned_Architecture_Brief.png"), "rb") as f:
            png = f.read()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png)
        with mock.patch("core.ocr_vision.ask_gemini", return_value=("Diagram text", [])) as ask:
            self.assertEqual(read_image_text(tmp.name), "Diagram text")
        self.assertEqual(ask.call_args.kwargs["image_mime"], "image/png")
        os.remove(tmp.name)


if __name__ == "__main__":
    unittest.main()
