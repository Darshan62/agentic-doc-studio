"""
Citation Provenance & End-to-End Traceability Tracker
Maps document sections, slide items, and statistical claims to verified Web & RAG sources.
"""
from typing import List, Dict, Any, Optional
import time
from core.models import Citation

class CitationTracker:
    def __init__(self):
        self.citations: List[Citation] = []
        self.claim_mappings: List[Dict[str, Any]] = []

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

    def link_claim(self, target_artifact: str, target_location: str, claim_text: str, citation_ids: List[str]):
        """Records traceability from an artifact location (e.g. 'Slide 3: Market Size' or 'Doc: Section 2') to sources."""
        self.claim_mappings.append({
            "target_artifact": target_artifact,
            "target_location": target_location,
            "claim_text": claim_text,
            "citations": citation_ids,
            "timestamp": time.time()
        })

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

    def get_traceability_matrix(self) -> List[Dict[str, Any]]:
        return self.claim_mappings
