"""
Content Writer Agent
Asks Gemini to write the proposal and the slide deck as JSON, grounded in web research
and retrieved knowledge chunks. The DOCX/PPTX generators then turn that JSON into files.
"""
import json
from typing import Any, Dict, List, Tuple

from core.gemini_client import GeminiError, ask_gemini_json
from core.models import RAGChunk, WebSearchResult

CONTENT_SLIDES = 10  # + title slide + sources slide = 12 slides

CONTENT_FORMAT = f"""
Return JSON with exactly this shape:
{{
  "document": {{
    "title": str, "subtitle": str, "executive_summary": str,
    "sections": [{{"heading": str, "paragraphs": [str], "bullets": [str],
                   "table": {{"headers": [str], "rows": [[str]]}} or null}}]
  }},
  "deck": {{
    "title": str, "subtitle": str,
    "slides": [ exactly {CONTENT_SLIDES} slides, each one of these layouts:
      {{"layout": "bullets", "title": str, "summary": str, "points": [str]}},
      {{"layout": "two_column", "title": str, "left_title": str, "left_points": [str], "right_title": str, "right_points": [str]}},
      {{"layout": "three_pillar", "title": str, "subtitle": str, "pillars": [{{"title": str, "desc": str, "metric": str}}]}},
      {{"layout": "metrics", "title": str, "metrics": [{{"value": str, "label": str, "desc": str}}]}},
      {{"layout": "table", "title": str, "headers": [str], "rows": [[str]]}}
    ]
  }}
}}
Use 4-6 document sections. Keep slide text short (max ~15 words per point, max 3 pillars, max 4 metrics).
"""


def format_sources(web_results: List[WebSearchResult], rag_chunks: List[RAGChunk]) -> str:
    lines = []
    if web_results:
        lines.append("WEB RESEARCH SUMMARY:\n" + web_results[0].summary)
        lines.append("WEB SOURCES: " + ", ".join(f"{r.id} {r.title}" for r in web_results if r.id))
    for chunk in rag_chunks:
        lines.append(f"{chunk.metadata.get('citation_id', '')} From {chunk.source_doc}:\n{chunk.content}")
    return "\n\n".join(lines)


class ContentWriterAgent:
    def __init__(self):
        self.name = "Content Writer Agent"

    def write(self, request: str, tone: str, web_results: List[WebSearchResult],
              rag_chunks: List[RAGChunk]) -> Dict[str, Any]:
        prompt = (
            f"You write business proposals and slide decks. Tone: {tone}.\n\n"
            f"USER REQUEST:\n{request}\n\n"
            # Separate brackets per id, so "[RAG-2]" can be found in the text by the validator and UI
            f"SOURCES (only use facts and numbers from these; cite them inline with their ids, "
            f"each id in its own brackets like [Web-1][RAG-2], never grouped like [Web-1, RAG-2]):\n"
            f"{format_sources(web_results, rag_chunks)}\n\n"
            f"{CONTENT_FORMAT}"
        )
        content = ask_gemini_json(prompt)
        check_content(content)
        return content

    def revise(self, content: Dict[str, Any], instruction: str) -> Tuple[Dict[str, Any], List[str]]:
        prompt = (
            "Here is the current proposal and slide deck as JSON:\n"
            f"{json.dumps(content)}\n\n"
            f"Apply this edit request: {instruction}\n"
            "Change only what the request asks for and keep existing citations.\n"
            'Return JSON: {"content": <the full updated JSON in the same shape>, "changes": [short description of each change]}'
        )
        answer = ask_gemini_json(prompt)
        check_content(answer.get("content", {}))
        return answer["content"], answer.get("changes", [])


def check_content(content: Dict[str, Any]) -> None:
    if not content.get("document", {}).get("sections") or not content.get("deck", {}).get("slides"):
        raise GeminiError("Gemini's answer was missing the document sections or the slides.")
