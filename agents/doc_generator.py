"""
Document Generation Agent
Turns the writer's JSON into an editable Word (.docx) file styled like the template.
"""
import os
from typing import Any, Dict, List

from core.models import DocumentStyle
from core.ooxml_docx import DocxBuilder

# The company logo goes on the first page, so it can later be replaced/resized from the editor chat
LOGO_PATH = "templates_and_samples/demo/acme_logo.png"
LOGO_WIDTH_EMU = int(1.6 * 914400)


class DocumentGenerationAgent:
    def __init__(self):
        self.name = "Document Generation Agent"

    def generate(self, doc: Dict[str, Any], style: DocumentStyle, citations: List[Dict[str, Any]],
                 output_path: str) -> str:
        builder = DocxBuilder(
            title=doc["title"],
            primary_font=style.primary_font,
            heading_font=style.heading_font,
            primary_color=style.primary_color,
            secondary_color=style.secondary_color,
        )
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                builder.add_image(f.read(), LOGO_WIDTH_EMU, name="Company Logo")
        builder.add_title_block(title=doc["title"], subtitle=doc.get("subtitle"))

        if doc.get("executive_summary"):
            builder.add_callout(title="Executive Summary", body=doc["executive_summary"],
                                border_color=style.primary_color)

        for number, section in enumerate(doc["sections"], start=1):
            builder.add_heading_1(f"{number}. {section['heading']}")
            for paragraph in section.get("paragraphs", []):
                builder.add_paragraph(paragraph)
            for bullet in section.get("bullets", []):
                builder.add_bullet(bullet)
            table = section.get("table")
            if table and table.get("headers") and table.get("rows"):
                builder.add_table(table["headers"], table["rows"])

        if citations:
            builder.add_heading_1("Sources")
            for c in citations:
                builder.add_paragraph(f"{c['id']} {c['title']} — {c['reference']}", italic=True, color="475569")

        builder.save(output_path)
        return output_path
