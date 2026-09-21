"""
Enterprise RAG (Retrieval-Augmented Generation) Agent
Interfaces with the Enterprise Vector Database to ground generation in verified corporate policies, SLAs, and data.
"""
from typing import List, Dict, Any
from core.models import RAGChunk
from core.vector_store import EnterpriseVectorStore
from core.citation_tracker import CitationTracker

class EnterpriseRagAgent:
    def __init__(self, vector_store: EnterpriseVectorStore):
        self.name = "Enterprise RAG Agent"
        self.vector_store = vector_store

    def retrieve(self, query: str, citation_tracker: CitationTracker, top_k: int = 4) -> List[RAGChunk]:
        chunks = self.vector_store.search(query, top_k=top_k)

        # Register citations for retrieved chunks
        for c in chunks:
            cid = citation_tracker.add_citation(
                source_type="rag",
                title=f"Enterprise Knowledge: {c.source_doc}",
                reference=c.source_doc,
                snippet=c.content[:240] + "...",
                confidence=c.similarity_score
            )

        return chunks
