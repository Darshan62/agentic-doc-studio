"""
Data models for Multi-Agent AI System (Documents, Presentations, Research, Citations, Versioning)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class DocumentStyle:
    primary_font: str = "Georgia"
    heading_font: str = "Arial"
    primary_color: str = "1B365D"       # Deep Navy
    secondary_color: str = "00A3E0"     # Cyan
    accent_color: str = "E05A47"        # Coral/Accent
    text_color: str = "222222"          # Dark Charcoal
    bg_color: str = "FFFFFF"
    margin_top_inches: float = 1.0
    margin_bottom_inches: float = 1.0
    margin_left_inches: float = 1.0
    margin_right_inches: float = 1.0
    line_spacing: float = 1.15
    tone: str = "Executive, Strategic, Analytical, Formal"
    tone_score: float = 0.95
    heading_styles: Dict[str, Any] = field(default_factory=lambda: {
        "h1_size_pt": 22,
        "h2_size_pt": 16,
        "h3_size_pt": 13,
        "body_size_pt": 11
    })

@dataclass
class PresentationStyle:
    aspect_ratio: str = "16:9"
    width_emu: int = 12192000          # 16:9 standard: 13.333 inches
    height_emu: int = 6858000          # 16:9 standard: 7.5 inches
    primary_font: str = "Arial"
    header_font: str = "Arial Bold"
    primary_color: str = "0F2D59"       # Enterprise Navy
    secondary_color: str = "2563EB"     # Royal Blue
    accent_color: str = "10B981"        # Emerald/Green accent
    text_color: str = "1E293B"          # Slate 800
    bg_color: str = "F8FAFC"            # Soft Slate 50
    card_bg_color: str = "FFFFFF"
    card_border_color: str = "E2E8F0"
    slide_count: int = 12
    tone: str = "Boardroom, Modern, High-Impact"

@dataclass
class WebSearchResult:
    id: str
    title: str
    url: str
    snippet: str
    key_points: List[str]
    published_year: int
    confidence: float
    source_name: str

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
    id: str                            # e.g., "[Web-1]" or "[RAG-1]"
    source_type: str                   # "web" or "rag"
    title: str
    reference: str                     # URL or Internal document name
    snippet: str
    confidence: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class AgentStepLog:
    step_num: int
    agent_name: str
    action: str
    detail: str
    status: str                        # "running", "completed", "verified"
    timestamp: float = field(default_factory=time.time)
    artifacts: List[str] = field(default_factory=list)

@dataclass
class VersionRecord:
    version: str                       # e.g. "v1.0", "v1.1", "v2.0"
    timestamp: float
    author: str
    instruction: str
    doc_path: Optional[str]
    ppt_path: Optional[str]
    diff_summary: List[str]
    changes_count: int
