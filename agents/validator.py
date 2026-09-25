"""
Validation Agent
Re-opens the generated files and checks they are valid and complete, and that sources are actually cited.
"""
import json
from typing import Any, Dict, List

from core.ooxml_docx import DocxReader
from core.ooxml_pptx import PptxReader

MIN_HEADINGS = 3
MIN_WORDS = 200


def colors_match(expected: str, detected: List[str]) -> bool:
    return expected.upper() in (c.upper() for c in detected)


class ValidationAgent:
    def __init__(self):
        self.name = "Validation Agent"

    def validate_docx(self, docx_path: str, expected_primary_color: str) -> Dict[str, Any]:
        s = DocxReader(docx_path).extract_structure()
        checks = {
            "file_opens": "error" not in s,
            "title_present": bool(s.get("title")),
            "enough_headings": s.get("headings_count", 0) >= MIN_HEADINGS,
            "enough_words": s.get("word_count", 0) >= MIN_WORDS,
            "template_color_used": colors_match(expected_primary_color, s.get("detected_colors", [])),
        }
        return self._scorecard("DOCX", docx_path, checks)

    def validate_pptx(self, pptx_path: str, expected_slides: int, expected_primary_color: str) -> Dict[str, Any]:
        s = PptxReader(pptx_path).extract_structure()
        checks = {
            "file_opens": "error" not in s,
            "slide_count_correct": s.get("slide_count") == expected_slides,
            "every_slide_has_title": len(s.get("titles", [])) == s.get("slide_count"),
            "template_color_used": colors_match(expected_primary_color, s.get("detected_colors", [])),
        }
        result = self._scorecard("PPTX", pptx_path, checks)
        result["checks"]["actual_slides"] = s.get("slide_count", 0)
        return result

    def audit_citations(self, content: Dict[str, Any], citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        text = json.dumps(content)
        cited = [c["id"] for c in citations if c["id"] in text]
        return {
            "status": "PASSED" if cited else "WARNING",
            "total_sources": len(citations),
            "sources_cited_in_text": len(cited),
            "uncited_sources": [c["id"] for c in citations if c["id"] not in cited],
        }

    @staticmethod
    def _scorecard(artifact: str, path: str, checks: Dict[str, bool]) -> Dict[str, Any]:
        passed_count = sum(checks.values())
        return {
            "artifact": artifact,
            "file_path": path,
            "status": "PASSED" if all(checks.values()) else "FAILED",
            "quality_score": round(100 * passed_count / len(checks)),
            "checks": dict(checks),
        }
