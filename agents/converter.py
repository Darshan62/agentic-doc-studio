"""
Bidirectional Conversion Agent
Converts the current proposal into a slide deck, or the current deck into a proposal,
by reshaping the content JSON and rendering it with the normal generators.
"""
from typing import Any, Dict, List

from agents.doc_generator import DocumentGenerationAgent
from agents.ppt_generator import PptGenerationAgent
from core.models import DocumentStyle, PresentationStyle

MAX_POINTS_PER_SLIDE = 5


def document_to_deck(doc: Dict[str, Any]) -> Dict[str, Any]:
    slides = []
    for section in doc["sections"]:
        paragraphs = section.get("paragraphs", [])
        slides.append({
            "layout": "bullets",
            "title": section["heading"],
            "summary": paragraphs[0] if paragraphs else "",
            "points": (section.get("bullets") or paragraphs[1:])[:MAX_POINTS_PER_SLIDE],
        })
    return {"title": doc["title"], "subtitle": doc.get("subtitle", ""), "slides": slides}


def slide_text(slide: Dict[str, Any]) -> List[str]:
    """Flattens any slide layout into plain bullet lines."""
    lines = list(slide.get("points", []))
    lines += slide.get("left_points", []) + slide.get("right_points", [])
    lines += [f"{p.get('title', '')}: {p.get('desc', '')}" for p in slide.get("pillars", [])]
    lines += [f"{m.get('value', '')} {m.get('label', '')} — {m.get('desc', '')}" for m in slide.get("metrics", [])]
    lines += [" | ".join(row) for row in slide.get("rows", [])]
    return lines


def deck_to_document(deck: Dict[str, Any]) -> Dict[str, Any]:
    sections = []
    for slide in deck["slides"]:
        summary = slide.get("summary") or slide.get("subtitle")
        sections.append({
            "heading": slide.get("title", ""),
            "paragraphs": [summary] if summary else [],
            "bullets": slide_text(slide),
            "table": None,
        })
    return {"title": deck["title"], "subtitle": deck.get("subtitle", ""), "executive_summary": "", "sections": sections}


class BidirectionalConverterAgent:
    def __init__(self):
        self.name = "Bidirectional Conversion Agent"

    def docx_to_pptx(self, content: Dict[str, Any], citations: List[Dict[str, Any]],
                     output_path: str = "output/Converted_From_Proposal.pptx") -> str:
        deck = document_to_deck(content["document"])
        return PptGenerationAgent().generate(deck, PresentationStyle(), citations, output_path)

    def pptx_to_docx(self, content: Dict[str, Any], citations: List[Dict[str, Any]],
                     output_path: str = "output/Converted_From_Presentation.docx") -> str:
        doc = deck_to_document(content["deck"])
        return DocumentGenerationAgent().generate(doc, DocumentStyle(), citations, output_path)
