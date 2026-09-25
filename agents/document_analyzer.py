"""
Document Analysis Agent
Reads a Word (.docx) template and picks up its fonts and brand colours.
"""
from typing import Any, Dict, List

from core.models import DocumentStyle
from core.ooxml_docx import DocxReader

def is_grey(hex_color: str) -> bool:
    """White, black and greys (R == G == B) are text/background colours, not brand colours."""
    return hex_color[0:2] == hex_color[2:4] == hex_color[4:6]


def brand_colors(colors: List[str]) -> List[str]:
    return [c.upper() for c in colors if not is_grey(c.upper())]


class DocumentAnalysisAgent:
    def __init__(self):
        self.name = "Document Analysis Agent"

    def analyze(self, path: str) -> Dict[str, Any]:
        structure = DocxReader(path).extract_structure()
        style = DocumentStyle()

        fonts = structure["detected_fonts"]
        if fonts:
            style.primary_font = fonts[0]
            style.heading_font = fonts[1] if len(fonts) > 1 else fonts[0]

        colors = brand_colors(structure["detected_colors"])
        if colors:
            style.primary_color = colors[0]
        if len(colors) > 1:
            style.secondary_color = colors[1]

        return {
            "style_object": style,
            "headings": [text for _, text in structure["headings"][:6]],
            "word_count": structure["word_count"],
        }
