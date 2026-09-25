"""
Enterprise RAG (Retrieval-Augmented Generation) Agent
Finds the knowledge-base chunks (sample docs + your uploads) most relevant to the request.
"""
from typing import List

from core.citation_tracker import CitationTracker
from core.models import RAGChunk
from core.vector_store import EnterpriseVectorStore


class EnterpriseRagAgent:
    def __init__(self, vector_store: EnterpriseVectorStore):
        self.name = "Enterprise RAG Agent"
        self.vector_store = vector_store

    def retrieve(self, query: str, citation_tracker: CitationTracker, top_k: int = 6) -> List[RAGChunk]:
        chunks = self.vector_store.search(query, top_k=top_k)
        for chunk in chunks:
            chunk.metadata["citation_id"] = citation_tracker.add_citation(
                source_type="rag",
                title=chunk.title,
                reference=chunk.source_doc,
                snippet=chunk.content[:240],
                confidence=chunk.similarity_score,
            )
        return chunks
