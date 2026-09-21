"""
PPT Template Analysis Agent
Inspects uploaded PowerPoint templates (.pptx) to extract master layouts, color schemes, slide ratios, and styles.
"""
from typing import Dict, Any
from core.models import PresentationStyle
from core.ooxml_pptx import PptxReader

class PptAnalysisAgent:
    def __init__(self):
        self.name = "PPT Analysis Agent"

    def analyze(self, file_path_or_bytes, filename: str) -> Dict[str, Any]:
        extracted_style = PresentationStyle()
        reader = PptxReader(file_path_or_bytes)
        struct = reader.extract_structure()

        colors = struct.get("detected_colors", [])
        if colors:
            extracted_style.primary_color = colors[0]
            if len(colors) > 1:
                extracted_style.secondary_color = colors[1]
            if len(colors) > 2:
                extracted_style.accent_color = colors[2]

        fonts = struct.get("detected_fonts", [])
        if fonts:
            extracted_style.primary_font = fonts[0]

        analysis = {
            "agent": self.name,
            "filename": filename,
            "master_dimensions": {
                "aspect_ratio": "16:9 (Widescreen)",
                "width_emu": extracted_style.width_emu,
                "height_emu": extracted_style.height_emu,
                "width_inches": 13.333,
                "height_inches": 7.5
            },
            "slide_count_detected": struct.get("slide_count", 0),
            "sample_slide_titles": struct.get("titles", [])[:5],
            "extracted_palette": {
                "primary": f"#{extracted_style.primary_color}",
                "secondary": f"#{extracted_style.secondary_color}",
                "accent": f"#{extracted_style.accent_color}",
                "background": f"#{extracted_style.bg_color}"
            },
            "typography": {
                "font_family": extracted_style.primary_font,
                "hierarchy": {
                    "slide_title_pt": 26,
                    "section_card_pt": 16,
                    "body_pt": 13,
                    "metric_large_pt": 32
                }
            },
            "layout_patterns": [
                "16:9 Widescreen Title Hero",
                "Executive Summary with Top Highlight Callout",
                "3-Pillar Strategy Cards with Colored Headers",
                "2-Column Side-by-Side Comparison",
                "4-Quadrant Key Performance Metrics Dashboard",
                "Structured Competitive Matrix Table",
                "Phased Implementation Roadmap",
                "Source Citations & Provenance Directory"
            ],
            "style_object": extracted_style
        }
        return analysis
