"""
Enterprise RAG (Retrieval-Augmented Generation) Agent
Finds the knowledge-base chunks (sample docs + your uploads) most relevant to the request.
"""
from typing import List, Optional

from core.citation_tracker import CitationTracker
from core.models import RAGChunk
from core.vector_store import EnterpriseVectorStore


FOCUS_CHUNKS_PER_DOC = 10


class EnterpriseRagAgent:
    def __init__(self, vector_store: EnterpriseVectorStore):
        self.name = "Enterprise RAG Agent"
        self.vector_store = vector_store

    def retrieve(self, query: str, citation_tracker: CitationTracker, top_k: int = 6,
                 focus_docs: Optional[List[str]] = None) -> List[RAGChunk]:
        """With focus_docs (files the user just uploaded), those files come first, so requests like
        "summarise my presentation" use its content even when the wording doesn't match it."""
        chunks: List[RAGChunk] = []
        for doc in focus_docs or []:
            chunks += self.vector_store.search(query, top_k=FOCUS_CHUNKS_PER_DOC, filter_source=doc)
        if len(chunks) < top_k:
            seen = {c.id for c in chunks}
            chunks += [c for c in self.vector_store.search(query, top_k=top_k) if c.id not in seen][:top_k - len(chunks)]
        for chunk in chunks:
            chunk.metadata["citation_id"] = citation_tracker.add_citation(
                source_type="rag",
                title=chunk.title,
                reference=chunk.source_doc,
                snippet=chunk.content[:240],
                confidence=chunk.similarity_score,
            )
        return chunks
