"""
Data models shared by the agents.
"""
from dataclasses import dataclass, field
from typing import Any, Dict
import time


@dataclass
class DocumentStyle:
    """Defaults used when a Word template has no fonts/colours of its own."""
    primary_font: str = "Georgia"
    heading_font: str = "Arial"
    primary_color: str = "1B365D"       # navy
    secondary_color: str = "00A3E0"     # cyan
    tone: str = "Executive, Strategic, Analytical, Formal"


@dataclass
class PresentationStyle:
    """Defaults used when a PowerPoint template has no fonts/colours of its own."""
    primary_font: str = "Arial"
    primary_color: str = "0F2D59"       # navy
    secondary_color: str = "2563EB"     # blue
    accent_color: str = "10B981"        # green
    bg_color: str = "F8FAFC"            # off-white


@dataclass
class WebSearchResult:
    id: str                            # citation id, e.g. "[Web-1]"
    title: str
    url: str
    summary: str                       # Gemini's research summary shared by all sources of one search


@dataclass
class RAGChunk:
    id: str
    source_doc: str
    title: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    id: str                            # e.g. "[Web-1]" or "[RAG-1]"
    source_type: str                   # "web" or "rag"
    title: str
    reference: str                     # URL or uploaded file name
    snippet: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
