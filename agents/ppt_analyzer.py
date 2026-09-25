"""
PPT Template Analysis Agent
Reads a PowerPoint (.pptx) template and picks up its theme colours and font.
"""
from typing import Any, Dict

from agents.document_analyzer import brand_colors
from core.models import PresentationStyle
from core.ooxml_pptx import PptxReader


class PptAnalysisAgent:
    def __init__(self):
        self.name = "PPT Analysis Agent"

    def analyze(self, path: str) -> Dict[str, Any]:
        structure = PptxReader(path).extract_structure()
        style = PresentationStyle()

        colors = brand_colors(structure["detected_colors"])
        if colors:
            style.primary_color = colors[0]
        if len(colors) > 1:
            style.secondary_color = colors[1]
        if len(colors) > 2:
            style.accent_color = colors[2]

        if structure["detected_fonts"]:
            style.primary_font = structure["detected_fonts"][0]

        return {
            "style_object": style,
            "slide_count": structure["slide_count"],
            "sample_titles": structure["titles"][:5],
        }
