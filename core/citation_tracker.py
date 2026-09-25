"""
Citation Tracker
Gives every source an id like [Web-1] or [RAG-2] so the writer can cite it in the text.
"""
from typing import Any, Dict, List
import time
from core.models import Citation

class CitationTracker:
    def __init__(self):
        self.citations: List[Citation] = []

    def add_citation(self, source_type: str, title: str, reference: str, snippet: str, confidence: float = 0.95) -> str:
        cid_prefix = "Web" if source_type == "web" else "RAG"
        count = len([c for c in self.citations if c.source_type == source_type]) + 1
        cid = f"[{cid_prefix}-{count}]"

        cit = Citation(
            id=cid,
            source_type=source_type,
            title=title,
            reference=reference,
            snippet=snippet,
            confidence=confidence,
            timestamp=time.time()
        )
        self.citations.append(cit)
        return cid

    def get_citations_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": c.id,
                "source_type": c.source_type,
                "title": c.title,
                "reference": c.reference,
                "snippet": c.snippet,
                "confidence": c.confidence,
                "timestamp": c.timestamp
            }
            for c in self.citations
        ]

