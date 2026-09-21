"""
Generates enterprise sample templates and internal knowledge base documents.
"""
import os
import io
import struct
import zlib
from core.ooxml_docx import DocxBuilder
from core.ooxml_pptx import PptxBuilder
from core.vector_store import EnterpriseVectorStore

def make_sample_png_bytes() -> bytes:
    """Creates a valid 100x100 PNG with embedded tEXt metadata simulating a scanned architecture diagram."""
    width, height = 100, 100
    # PNG signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    ihdr_chunk = struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + ihdr_crc

    # tEXt chunks for OCR Vision testing
    def make_text_chunk(keyword: str, text: str) -> bytes:
        data = keyword.encode('latin1') + b'\x00' + text.encode('latin1')
        crc = struct.pack('>I', zlib.crc32(b'tEXt' + data) & 0xffffffff)
        return struct.pack('>I', len(data)) + b'tEXt' + data + crc

    text1 = make_text_chunk("Title", "Enterprise Multi-Agent Architecture Blueprint (Scanned)")
    text2 = make_text_chunk("Pillars", "Pillar 1: Supervisor Orchestration. Pillar 2: Vector RAG. Pillar 3: Zero-trust RBAC.")
    text3 = make_text_chunk("SLA", "Target 99.95% uptime with sub-second generation latency.")

    # Minimal blank image data (IDAT)
    raw_scanlines = b''.join(b'\x00' + b'\xf0\xf4\xf8' * width for _ in range(height))
    idat_compressed = zlib.compress(raw_scanlines)
    idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + idat_compressed) & 0xffffffff)
    idat_chunk = struct.pack('>I', len(idat_compressed)) + b'IDAT' + idat_compressed + idat_crc

    # IEND chunk
    iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    iend_chunk = struct.pack('>I', 0) + b'IEND' + iend_crc

    return png_sig + ihdr_chunk + text1 + text2 + text3 + idat_chunk + iend_chunk

def create_all_samples():
    os.makedirs("templates_and_samples/knowledge_base", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # 1. Company_Proposal.docx template
    doc_path = "templates_and_samples/Company_Proposal.docx"
    doc_builder = DocxBuilder(
        title="Corporate Proposal Template: Acme Technologies",
        primary_font="Georgia",
        heading_font="Arial",
        primary_color="1B365D",
        secondary_color="00A3E0"
    )
    doc_builder.add_title_block(
        title="ACME ENTERPRISE PROPOSAL TEMPLATE",
        subtitle="Standard Corporate Proposal and Technical Specifications Layout",
        metadata={"Organization": "Acme Global Solutions", "Style Standard": "v2.4 Enterprise", "Confidentiality": "Restricted"}
    )
    doc_builder.add_callout(
        title="Corporate Template Directives",
        body="All generated proposals must strictly adhere to Georgia typography for narrative sections, Arial Bold for headings, Deep Navy (#1B365D) for primary branding, and Cyan (#00A3E0) for sub-headers and table banners.",
        bg_color="F0F4F8",
        border_color="1B365D"
    )
    doc_builder.add_heading_1("1. Proposal Scope and Strategic Objectives")
    doc_builder.add_paragraph("This standard template establishes the formatting guidelines for multi-agent system proposals, statements of work, and architecture assessments.")
    doc_builder.add_bullet("Strict adherence to 1.0 inch page margins.")
    doc_builder.add_bullet("Color-coordinated tables with alternating row shading.")
    doc_builder.add_bullet("Executive callouts with left border visual anchors.")
    doc_builder.add_heading_1("2. Technical Specifications & Metric Standards")
    headers = ["Component", "Specification", "Compliance SLA"]
    rows = [
        ["Typography", "Georgia Regular / Arial Bold", "Strict Brand Enforced"],
        ["Primary Palette", "#1B365D Navy & #00A3E0 Cyan", "100% Color Match"],
        ["Table Formatting", "Zebra-Striping Slate #F8FAFC", "Standardized"]
    ]
    doc_builder.add_table(headers, rows)
    doc_builder.save(doc_path)
    print(f"Created template: {doc_path}")

    # 2. Company_Template.pptx presentation template
    ppt_path = "templates_and_samples/Company_Template.pptx"
    ppt_builder = PptxBuilder(
        title="Acme Master Presentation Template",
        primary_color="0F2D59",
        secondary_color="2563EB",
        accent_color="10B981",
        bg_color="F8FAFC",
        primary_font="Arial"
    )
    ppt_builder.add_title_slide(
        title="ACME CORPORATION PRESENTATION MASTER",
        subtitle="16:9 Widescreen Master Template with Executive Visual Guidelines",
        metadata="Template Version 3.0 | Brand Identity & Design System 2025"
    )
    ppt_builder.add_executive_summary_slide(
        title="Presentation Style Guide & Layout Conventions",
        summary_text="This master template enforces 16:9 widescreen layout geometry, high-contrast typography, and structured 3-pillar content cards.",
        highlights=[
            "Primary Palette: Enterprise Navy (#0F2D59) and Royal Blue (#2563EB).",
            "Accent Highlights: Emerald (#10B981) for positive metrics and status indicators.",
            "Typography: Arial and Arial Bold with 26pt title hierarchy."
        ]
    )
    ppt_builder.add_three_pillar_slide(
        title="Master Card Layout Standards",
        subtitle="Three distinct structured visual cards with metric footers",
        pillars=[
            {"title": "Pillar Cards", "desc": "Contrasting white cards with 1px border outlines.", "metric": "Standard 1"},
            {"title": "KPI Blocks", "desc": "32pt bold callout numbers for board metrics.", "metric": "Standard 2"},
            {"title": "Provenance", "desc": "Dedicated bibliography and citation slide.", "metric": "Standard 3"}
        ]
    )
    ppt_builder.save(ppt_path)
    print(f"Created template: {ppt_path}")

    # 3. Scanned_Architecture_Brief.png
    png_path = "templates_and_samples/Scanned_Architecture_Brief.png"
    with open(png_path, "wb") as f:
        f.write(make_sample_png_bytes())
    print(f"Created OCR sample: {png_path}")

    # 4. Knowledge Base Documents for Enterprise Vector RAG
    kb_files = {
        "templates_and_samples/knowledge_base/Acme_Enterprise_AI_Strategy_2025.txt": """
ACME ENTERPRISE AI STRATEGY & GOVERNANCE DIRECTIVE (2025-2027)
Classification: Internal Corporate Policy & Directive
Section 1: Multi-Agent Deployment Architecture
Acme Global Solutions mandates the deployment of specialized multi-agent architectures across all document generation and executive presentation workflows. Monolithic single-prompt large language models are prohibited for customer-facing deliverables due to unconstrained hallucination risks and lack of provenance.

Section 2: Vector Database & RAG Specifications
All generative tasks must be anchored in the Enterprise Knowledge Base via dense vector embeddings. The vector database must support cosine similarity retrieval with a minimum similarity threshold of 0.70. Documents must be indexed using sliding-window chunking (350-character chunks with 60-character overlap) to prevent loss of tabular and numerical context.

Section 3: Native OpenXML Document Integrity
All generated artifacts must output native Microsoft Word (.docx) and Microsoft PowerPoint (.pptx) binary packages strictly adhering to the ECMA-376 OpenXML standard. External desktop office automation dependencies (e.g. headless Word/PowerPoint processes) are forbidden to ensure containerized microservice portability.

Section 4: Performance SLAs
- Proposal synthesis latency: Under 30 seconds for 5-page enterprise proposals.
- Presentation synthesis latency: Under 35 seconds for 12-slide executive slide decks.
- Brand fidelity: 100% programmatic alignment with Acme design system (Georgia/Arial, Navy #1B365D, Cyan #00A3E0).
""",
        "templates_and_samples/knowledge_base/Acme_Security_and_Governance_Standards.txt": """
ACME INFORMATION SECURITY & ZERO-TRUST GOVERNANCE STANDARDS
Standard Ref: SEC-AI-8092 | Compliance: ISO 27001, SOC 2 Type II, EU AI Act
1. Data Ingestion & Isolation:
Customer prompt data, uploaded document templates, and enterprise documents shall remain strictly within dedicated tenant VPC boundaries. No data uploaded or generated shall be used to fine-tune or train external foundational models.

2. Role-Based Access Control (RBAC):
Access to document modification, conversational edits, and vector database embeddings requires cryptographic authentication. Every version modification must log the author, instruction prompt, timestamp, and unified diff summary.

3. Source Traceability & Cryptographic Provenance:
Every generated section, table, and presentation slide must include explicit citation tags referencing either live web intelligence ([Web-X]) or internal vector knowledge chunks ([RAG-X]). Uncited factual claims must be flagged by the Validation Agent.
""",
        "templates_and_samples/knowledge_base/Acme_Market_Expansion_Brief.txt": """
ACME ENTERPRISE MARKET EXPANSION & COMMERCIAL TARGETS
Confidential Strategic Planning Document
1. Addressable Market Size:
The market for automated document intelligence, executive slide deck generation, and enterprise search represents a total addressable market (TAM) of $34.2 Billion by 2027, growing at a CAGR of 38.6%.

2. Competitive Differentiation:
Unlike consumer chatbot applications (ChatGPT, Claude, Gemini web interfaces), our enterprise platform delivers:
- In-place conversational edits without destructive full-document rewrites.
- Exact brand template style extraction from uploaded DOCX and PPTX files.
- Bidirectional document-to-presentation translation.
- Complete version snapshotting with immediate rollback capability.
"""
    }

    for path, text in kb_files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.strip())
        print(f"Created KB document: {path}")

    # Index KB files into the Vector Store
    print("Indexing knowledge base files into Enterprise Vector Store...")
    vs = EnterpriseVectorStore("knowledge_store.db")
    for path, text in kb_files.items():
        doc_name = os.path.basename(path)
        chunks_indexed = vs.index_document(doc_name, doc_name.replace(".txt", "").replace("_", " "), text)
        print(f"  -> Indexed {chunks_indexed} chunks for {doc_name}")

    print("Knowledge store initialized successfully!")

if __name__ == "__main__":
    create_all_samples()
