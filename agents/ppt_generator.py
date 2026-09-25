"""
PowerPoint Generation Agent
Turns the writer's JSON into an editable 16:9 PowerPoint (.pptx) using the template colours.
Deck = title slide + the writer's content slides + a sources slide.
"""
import os
from typing import Any, Dict, List

from core.models import PresentationStyle
from core.ooxml_pptx import PptxBuilder

MAX_SOURCES_ON_SLIDE = 6
LOGO_PATH = "templates_and_samples/demo/acme_logo.png"  # shown on every slide; editable from the chat


def add_content_slide(builder: PptxBuilder, slide: Dict[str, Any]) -> None:
    layout = slide.get("layout")
    title = slide.get("title", "")

    if layout == "two_column":
        builder.add_two_column_slide(title, "", slide.get("left_title", ""), slide.get("left_points", []),
                                     slide.get("right_title", ""), slide.get("right_points", []))
    elif layout == "three_pillar":
        builder.add_three_pillar_slide(title, slide.get("subtitle", ""), slide.get("pillars", []))
    elif layout == "metrics":
        builder.add_metrics_slide(title, slide.get("metrics", []))
    elif layout == "table":
        builder.add_table_slide(title, "", slide.get("headers", []), slide.get("rows", []))
    else:
        # "bullets", and the fallback if Gemini invents a layout name
        builder.add_executive_summary_slide(title, slide.get("summary", ""), slide.get("points", []))


class PptGenerationAgent:
    def __init__(self):
        self.name = "PPT Generation Agent"

    def generate(self, deck: Dict[str, Any], style: PresentationStyle, citations: List[Dict[str, Any]],
                 output_path: str) -> str:
        builder = PptxBuilder(
            title=deck["title"],
            primary_color=style.primary_color,
            secondary_color=style.secondary_color,
            accent_color=style.accent_color,
            bg_color=style.bg_color,
            primary_font=style.primary_font,
        )
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                builder.set_logo(f.read())
        builder.add_title_slide(title=deck["title"], subtitle=deck.get("subtitle", ""), metadata="")

        for slide in deck["slides"]:
            add_content_slide(builder, slide)

        builder.add_citations_slide(
            title="Sources",
            citations=[{"id": c["id"], "title": c["title"], "url": c["reference"]} for c in citations[:MAX_SOURCES_ON_SLIDE]],
        )
        builder.save(output_path)
        return output_path
