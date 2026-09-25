"""
End-to-end tests of the chat editing loop on real DOCX/PPTX files (built-in parser, no network).
Each test runs in its own temp folder with fresh demo files, and checks the saved file itself.
Run:  python -m unittest tests.test_editor_workspace
"""
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock

from agents.workspace_agent import run_workspace
from core.docx_model import DocxDocument, paragraph_text
from core.ooxml_package import OoxmlPackage
from core.pptx_model import PptxDocument, shape_text, text_of
from templates_and_samples.create_demo_files import create_demo_files

DOCX = "templates_and_samples/demo/Acme_Proposal_Demo.docx"
PPTX = "templates_and_samples/demo/Acme_Pitch_Deck_Demo.pptx"
NEW_LOGO = "templates_and_samples/uploads/nova_logo.png"


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        env = mock.patch.dict(os.environ, {"EDIT_PARSER": "rules", "GEMINI_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        create_demo_files()
        os.makedirs("templates_and_samples/uploads")
        shutil.copy("templates_and_samples/demo/nova_logo.png", NEW_LOGO)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def chat(self, message: str, **extra) -> dict:
        return run_workspace({"op": "chat", "message": message, **extra})

    def working_path(self) -> str:
        state = run_workspace({"op": "state"})["state"]
        folder = next(p for p in os.listdir("output/workspace") if os.path.isdir(os.path.join("output/workspace", p)))
        return os.path.join("output/workspace", folder, state["active"]["name"])

    def working_file(self) -> OoxmlPackage:
        return OoxmlPackage.from_file(self.working_path())

    def last_reply(self, result: dict) -> str:
        return result["state"]["messages"][-1]["text"]


class DocxWorkflowTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(run_workspace({"op": "open", "path": DOCX})["status"], "ok")

    def title_props(self) -> dict:
        doc = DocxDocument(self.working_file())
        title = doc.title()
        return doc.styles.run_props(title.p, next(title.p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")))

    def test_title_font_bold_size_and_colour(self):
        for message in ("Change the document title font to Arial and make it bold.", "Change the title font size to 24.",
                        "Change the title color to blue."):
            self.assertEqual(self.chat(message)["status"], "done", message)
        props = self.title_props()
        self.assertEqual((props["font"], props["bold"], props["size"], props["color"]), ("Arial", True, 24.0, "0070C0"))
        state = run_workspace({"op": "state"})["state"]
        self.assertEqual(state["active"]["version"], "v1.3")

    def test_remove_paragraph_about_topic(self):
        result = self.chat("Remove the paragraph about enterprise architecture.")
        self.assertEqual(result["status"], "done")
        texts = [paragraph_text(r.p) for r in DocxDocument(self.working_file()).content_paragraphs()]
        self.assertFalse(any("enterprise architecture" in t for t in texts))
        self.assertTrue(any(t.startswith("The platform combines") for t in texts))

    def test_insert_paragraph_after_executive_summary(self):
        self.chat("Add this paragraph after the executive summary:\nOur platform helps enterprises automate document workflows.")
        texts = [paragraph_text(r.p) for r in DocxDocument(self.working_file()).content_paragraphs()]
        index = texts.index("Our platform helps enterprises automate document workflows.")
        self.assertTrue(texts[index - 1].startswith("Acme proposes"))
        self.assertEqual(texts[index + 1], "Solution Overview")

    def test_replace_and_resize_logo(self):
        missing = self.chat("Replace the company logo with the uploaded image.")
        self.assertEqual(missing["status"], "error")  # nothing uploaded yet
        run_workspace({"op": "upload", "path": NEW_LOGO})
        self.assertEqual(self.chat("Replace the company logo with the uploaded image.")["status"], "done")
        self.assertEqual(self.chat("Make the company logo 80% of its current size.")["status"], "done")
        pkg = self.working_file()
        image = DocxDocument(pkg).images()[0]
        with open(NEW_LOGO, "rb") as f:
            self.assertEqual(pkg.read(image.media_part), f.read())
        self.assertEqual(image.cx, round(int(1.6 * 914400) * 0.8))

    def test_undo_and_redo_restore_file_contents(self):
        self.chat("Change the title color to blue.")
        self.assertEqual(self.title_props()["color"], "0070C0")
        run_workspace({"op": "undo"})
        self.assertEqual(self.title_props()["color"], "1B365D")
        run_workspace({"op": "redo"})
        self.assertEqual(self.title_props()["color"], "0070C0")

    def test_missing_target_leaves_document_unchanged(self):
        before = self.working_file().to_bytes()
        result = self.chat("Remove the paragraph about quantum teleportation.")
        self.assertEqual(result["status"], "error")
        self.assertIn("couldn't", self.last_reply(result))
        self.assertEqual(self.working_file().to_bytes(), before)
        self.assertEqual(result["state"]["active"]["version"], "v1.0")

    def test_ambiguous_request_asks_and_numbered_answer_applies(self):
        result = self.chat("Remove the paragraph about platform")
        self.assertEqual(result["status"], "clarify")
        self.assertGreater(len(result["state"]["messages"][-1]["options"]), 1)
        self.assertEqual(self.chat("1")["status"], "done")

    def test_selection_is_used_for_this(self):
        pid = next(r.pid for r in DocxDocument(self.working_file()).content_paragraphs()
                   if paragraph_text(r.p).startswith("Teams keep"))
        self.chat("Delete this paragraph", selection={"kind": "paragraph", "pid": pid})
        texts = [paragraph_text(r.p) for r in DocxDocument(self.working_file()).content_paragraphs()]
        self.assertFalse(any(t.startswith("Teams keep") for t in texts))


class PptxWorkflowTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(run_workspace({"op": "open", "path": PPTX})["status"], "ok")

    def test_title_font_and_size_on_slide_one(self):
        self.assertEqual(self.chat("Change the title on slide 1 to Arial, 32 points.")["status"], "done")
        doc = PptxDocument(self.working_file())
        rpr = next(doc.title_shape(1).el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"))
        latin = rpr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}latin")
        self.assertEqual((rpr.get("sz"), latin.get("typeface")), ("3200", "Arial"))

    def test_remove_third_bullet_from_slide_two(self):
        self.chat("Remove the third bullet from slide 2.")
        bullets = [text_of(p) for _, p in PptxDocument(self.working_file()).bullets(2)]
        self.assertEqual(len(bullets), 3)
        self.assertNotIn("Manual edits introduce brand and compliance errors", bullets)

    def test_resize_logo_on_slide_one_only(self):
        self.chat("Resize the logo on slide 1 to 80%.")
        doc = PptxDocument(self.working_file())
        self.assertEqual(doc.pictures(1)[0].cx, round(int(1.8 * 914400) * 0.8))
        self.assertEqual(doc.pictures(2)[0].cx, int(0.9 * 914400))

    def test_add_bullet_delete_slide_and_replace_logo(self):
        self.chat("Add a bullet to slide 3: Live preview of every change")
        self.assertIn("Live preview of every change", [text_of(p) for _, p in PptxDocument(self.working_file()).bullets(3)])
        self.chat("Remove slide 5.")
        doc = PptxDocument(self.working_file())
        self.assertEqual([shape_text(doc.title_shape(n).el) for n in range(1, 5)][-1], "Business Impact")
        run_workspace({"op": "upload", "path": NEW_LOGO})
        self.chat("Change the presentation logo.")
        pkg = self.working_file()
        doc = PptxDocument(pkg)
        with open(NEW_LOGO, "rb") as f:
            new = f.read()
        self.assertTrue(all(pkg.read(doc.picture_media(p)[1]) == new for p in doc.pictures()))


class SafetyTests(WorkspaceTestCase):
    def test_chat_without_document_and_empty_message(self):
        self.assertEqual(run_workspace({"op": "chat", "message": "Make the title bold"})["status"], "error")
        run_workspace({"op": "open", "path": DOCX})
        self.assertEqual(run_workspace({"op": "chat", "message": "   "})["status"], "error")

    def test_paths_outside_allowed_folders_are_rejected(self):
        for path in ("../../etc/passwd.docx", "tests/test_editor_workspace.py", "output/workspace/state.json"):
            result = run_workspace({"op": "open", "path": path})
            self.assertEqual(result["status"], "error", path)

    def test_corrupted_file_gives_a_clear_error(self):
        with open("templates_and_samples/uploads/broken.docx", "wb") as f:
            f.write(b"this is not a zip file")
        result = run_workspace({"op": "open", "path": "templates_and_samples/uploads/broken.docx"})
        self.assertEqual(result["status"], "error")
        self.assertIn("corrupted", result["error"])

    def test_downloaded_file_is_a_valid_package(self):
        run_workspace({"op": "open", "path": PPTX})
        self.chat("Remove slide 5.")
        with zipfile.ZipFile(self.working_path()) as zf:
            self.assertIsNone(zf.testzip())
            self.assertNotIn("ppt/slides/slide5.xml", zf.namelist())


if __name__ == "__main__":
    unittest.main()
