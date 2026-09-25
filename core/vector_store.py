"""
Enterprise Vector Store & Semantic RAG Engine
Provides Pinecone-compatible vector database indexing, semantic embeddings, and cosine similarity search.
"""
import math
import sqlite3
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from core.models import RAGChunk

VECTOR_DIM = 128

def compute_dense_embedding(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """Generates a normalized dense vector embedding using character n-grams and hashing."""
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vec

    # Word unigrams and bigrams
    for i, w in enumerate(words):
        # Hash word
        h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(1 + len(w)))

        # Bigram
        if i < len(words) - 1:
            bg = f"{w}_{words[i+1]}"
            h_bg = int(hashlib.sha256(bg.encode('utf-8')).hexdigest(), 16)
            idx_bg = h_bg % dim
            sign_bg = 1.0 if (h_bg // dim) % 2 == 0 else -1.0
            vec[idx_bg] += sign_bg * 1.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return max(0.0, min(1.0, dot))


class EnterpriseVectorStore:
    def __init__(self, db_path: str = "knowledge_store.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_chunks (
                    id TEXT PRIMARY KEY,
                    source_doc TEXT,
                    title TEXT,
                    content TEXT,
                    embedding_json TEXT,
                    metadata_json TEXT,
                    created_at REAL
                )
            """)

    def index_document(self, doc_id: str, title: str, text: str, chunk_size: int = 350, overlap: int = 60) -> int:
        """Splits document into sliding windows and stores embeddings."""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)
            if current_len + p_len > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep last paragraph for overlap
                current_chunk = [current_chunk[-1]] if len(current_chunk) > 1 else []
                current_len = sum(len(x) for x in current_chunk)

            current_chunk.append(p)
            current_len += p_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        count = 0
        with self.conn:
            # Re-uploading a file replaces its old chunks instead of mixing old and new text
            self.conn.execute("DELETE FROM vector_chunks WHERE source_doc = ?", (doc_id,))
            for idx, c_text in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{idx}"
                emb = compute_dense_embedding(c_text)
                meta = {"chunk_index": idx, "total_chunks": len(chunks)}
                self.conn.execute("""
                    INSERT OR REPLACE INTO vector_chunks (id, source_doc, title, content, embedding_json, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (chunk_id, doc_id, f"{title} (Part {idx+1})", c_text, json.dumps(emb), json.dumps(meta), time.time()))
                count += 1

        return count

    def search(self, query: str, top_k: int = 4, filter_source: Optional[str] = None) -> List[RAGChunk]:
        """Performs cosine similarity search against indexed vector chunks."""
        q_vec = compute_dense_embedding(query)
        cursor = self.conn.cursor()
        
        if filter_source:
            cursor.execute("SELECT id, source_doc, title, content, embedding_json, metadata_json FROM vector_chunks WHERE source_doc = ?", (filter_source,))
        else:
            cursor.execute("SELECT id, source_doc, title, content, embedding_json, metadata_json FROM vector_chunks")

        rows = cursor.fetchall()
        scored_chunks = []
        for r in rows:
            cid, s_doc, title, content, emb_json, meta_json = r
            emb = json.loads(emb_json)
            score = cosine_similarity(q_vec, emb)
            meta = json.loads(meta_json) if meta_json else {}
            chunk = RAGChunk(id=cid, source_doc=s_doc, title=title, content=content, similarity_score=round(score, 4), metadata=meta)
            scored_chunks.append(chunk)

        # Sort descending by similarity score
        scored_chunks.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_chunks[:top_k]

    def count_chunks(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vector_chunks")
        return cursor.fetchone()[0]

    def list_indexed_docs(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT source_doc FROM vector_chunks")
        return [r[0] for r in cursor.fetchall()]
