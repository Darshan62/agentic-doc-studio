"""
Direct tests of the DOCX/PPTX editors (no chat layer): every supported operation is applied
in memory, saved, re-read, and checked on the XML.
Run:  python -m unittest tests.test_edit_operations
"""
import os
import shutil
import tempfile
import unittest

from core.docx_editor import DocxEditor
from core.docx_model import W, DocxDocument, paragraph_text
from core.edit_schema import ClarificationNeeded, EditError, validate_command
from core.ooxml_package import OoxmlPackage, PackageError, image_info
from core.pptx_editor import PptxEditor
from core.pptx_model import A, PptxDocument, shape_text, text_of
from templates_and_samples.create_demo_files import acme_logo, build_docx, build_pptx, nova_logo


def texts(pkg: OoxmlPackage):
    return [paragraph_text(r.p) for r in DocxDocument(pkg).content_paragraphs()]


class DocxOperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        path = os.path.join(self.tmp, "demo.docx")
        build_docx(acme_logo(), path)
        self.pkg = OoxmlPackage.from_file(path)

    def apply(self, raw: dict):
        outcome = DocxEditor(self.pkg).apply(validate_command(raw, "docx"), nova_logo())
        self.pkg = OoxmlPackage(self.pkg.to_bytes())  # round-trip: the saved bytes must parse again
        return outcome

    def test_update_text_replace_delete_and_insert_text(self):
        self.apply({"action": "update_text", "target": {"type": "title"}, "text": "Acme Document Cloud"})
        self.apply({"action": "replace_text", "target_text": "USD 240,000", "replacement_text": "USD 250,000"})
        self.apply({"action": "delete_text", "target_text": "up to 60% faster, "})
        self.apply({"action": "insert_text", "target": {"type": "subtitle"}, "text": "(Draft)"})
        all_text = texts(self.pkg)
        self.assertEqual(all_text[0], "Acme Document Cloud")
        self.assertTrue(any("USD 250,000" in t for t in all_text))
        self.assertFalse(any("60% faster" in t for t in all_text))
        self.assertTrue(all_text[1].endswith("(Draft)"))

    def test_style_headings_phrase_and_alignment(self):
        self.apply({"action": "update_style", "target": {"type": "headings"}, "changes": {"color": "red", "italic": True}})
        self.apply({"action": "update_style", "target": {"type": "text", "text": "zero-trust"}, "changes": {"underline": True}})
        self.apply({"action": "update_style", "target": {"type": "body"}, "changes": {"align": "justify"}})
        doc = DocxDocument(self.pkg)
        heading = next(r for r in doc.content_paragraphs() if doc.role(r) == "heading")
        props = doc.styles.run_props(heading.p, next(heading.p.iter(W + "r")))
        self.assertEqual((props["color"], props["italic"]), ("C00000", True))
        underlined = [r for r in doc.body.iter(W + "r") if r.find(f"{W}rPr/{W}u") is not None]
        self.assertEqual("".join(t.text or "" for r in underlined for t in r.iter(W + "t")), "zero-trust")
        body = next(r for r in doc.content_paragraphs() if doc.role(r) == "body")
        self.assertEqual(doc.styles.alignment(body.p), "justify")

    def test_insert_at_end_and_before_heading(self):
        self.apply({"action": "insert_paragraph", "text": "Closing remark.", "position": {"where": "end"}})
        self.apply({"action": "insert_paragraph", "text": "Before next steps.",
                    "position": {"where": "before", "anchor": {"type": "heading", "text": "Next Steps"}}})
        all_text = texts(self.pkg)
        self.assertEqual(all_text[-1], "Closing remark.")
        self.assertEqual(all_text[all_text.index("Next Steps") - 1], "Before next steps.")

    def test_errors_and_clarifications(self):
        with self.assertRaises(EditError):
            self.apply({"action": "update_style", "target": {"type": "paragraph", "index": 999}, "changes": {"bold": True}})
        with self.assertRaises(EditError):
            self.apply({"action": "replace_text", "target_text": "no such words", "replacement_text": "x"})
        with self.assertRaises(ClarificationNeeded):
            self.apply({"action": "delete_paragraph", "target": {"type": "paragraph", "text": "platform"}})
        with self.assertRaises(EditError):
            self.apply({"action": "resize_image", "target": {"type": "logo"}, "scale": 0.05})

    def test_logo_resize_is_capped_at_page_width_and_replace_keeps_aspect(self):
        self.apply({"action": "resize_image", "target": {"type": "logo"}, "scale": 10})
        image = DocxDocument(self.pkg).images()[0]
        self.assertEqual(image.cx, 6.5 * 914400)
        self.apply({"action": "replace_image", "target": {"type": "image", "index": 1}, "image_source": "last_upload"})
        image = DocxDocument(self.pkg).images()[0]
        _, width, height = image_info(nova_logo())
        self.assertAlmostEqual(image.cy / image.cx, height / width, places=3)

    def test_corrupted_package_is_rejected(self):
        with self.assertRaises(PackageError):
            OoxmlPackage(b"not a zip")


class PptxOperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        path = os.path.join(self.tmp, "demo.pptx")
        build_pptx(acme_logo(), path)
        self.pkg = OoxmlPackage.from_file(path)

    def apply(self, raw: dict, slide: int = 1):
        outcome = PptxEditor(self.pkg, slide).apply(validate_command(raw, "pptx"), nova_logo())
        self.pkg = OoxmlPackage(self.pkg.to_bytes())
        return outcome

    def test_update_text_replace_and_style_bullets(self):
        self.apply({"action": "update_text", "target": {"type": "title", "slide": 3}, "text": "Our Platform"})
        self.apply({"action": "replace_text", "target_text": "Q3 2025", "replacement_text": "Q4 2025"})
        self.apply({"action": "update_style", "target": {"type": "bullet", "slide": 2},
                    "changes": {"color": "green", "bold": True, "underline": True, "align": "center"}})
        doc = PptxDocument(self.pkg)
        self.assertEqual(shape_text(doc.title_shape(3).el), "Our Platform")
        self.assertIn("Q4 2025", "".join(t.text or "" for t in self.pkg.xml(doc.slide_part(1)).iter(A + "t")))
        for _, p in doc.bullets(2):
            rpr = p.find(f"{A}r/{A}rPr")
            self.assertEqual((rpr.get("b"), rpr.get("u"), rpr.find(f"{A}solidFill/{A}srgbClr").get("val")), ("1", "sng", "00B050"))
            self.assertEqual(p.find(A + "pPr").get("algn"), "ctr")

    def test_style_whole_document_and_current_slide_default(self):
        self.apply({"action": "update_style", "target": {"type": "document"}, "changes": {"font_family": "Georgia"}})
        outcome = self.apply({"action": "update_style", "target": {"type": "title"}, "changes": {"italic": True}}, slide=4)
        self.assertEqual(outcome.slides, [4])
        latin = {r.get("typeface") for n in range(1, 6)
                 for r in self.pkg.xml(PptxDocument(self.pkg).slide_part(n)).iter(A + "latin")}
        self.assertEqual(latin, {"Georgia"})

    def test_add_bullet_after_first_and_delete_by_text(self):
        self.apply({"action": "add_text", "target": {"type": "slide", "slide": 5}, "text": "Inserted second",
                    "position": {"where": "after", "anchor": {"type": "bullet", "index": 1, "slide": 5}}})
        self.apply({"action": "delete_text", "target": {"type": "paragraph", "text": "Company-wide rollout", "slide": 5}})
        bullets = [text_of(p) for _, p in PptxDocument(self.pkg).bullets(5)]
        self.assertEqual(bullets, ["Two-week discovery workshop", "Inserted second", "Pilot with the proposals team"])

    def test_move_to_corner_stays_on_slide(self):
        self.apply({"action": "move_image", "target": {"type": "logo", "slide": 2}, "move": {"to": "bottom-left"}})
        self.apply({"action": "move_image", "target": {"type": "logo", "slide": 3}, "move": {"dx_inches": 20, "dy_inches": 0}})
        doc = PptxDocument(self.pkg)
        width, height = doc.slide_size()
        moved = doc.pictures(2)[0]
        self.assertEqual((moved.x, moved.y + moved.cy), (int(0.3 * 914400), height - int(0.3 * 914400)))
        pushed = doc.pictures(3)[0]
        self.assertEqual(pushed.x + pushed.cx, width)

    def test_errors(self):
        with self.assertRaises(EditError):
            self.apply({"action": "delete_slide", "target": {"type": "slide", "slide": 9}})
        with self.assertRaises(EditError):
            self.apply({"action": "delete_text", "target": {"type": "bullet", "index": 9, "slide": 2}})
        with self.assertRaises(EditError):
            self.apply({"action": "resize_image", "target": {"type": "logo", "slide": 2}, "scale": 0.05})
        for _ in range(4):
            self.apply({"action": "delete_slide", "target": {"type": "slide", "slide": 1}})
        with self.assertRaises(EditError):
            self.apply({"action": "delete_slide", "target": {"type": "slide", "slide": 1}})


if __name__ == "__main__":
    unittest.main()
