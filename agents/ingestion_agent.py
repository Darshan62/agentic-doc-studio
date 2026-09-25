"""
Ingestion Agent
Reads an uploaded file (PDF, DOCX, PPTX, TXT, image) and indexes its text into the vector store,
so later requests can retrieve it through RAG.
"""
import os

from core.ocr_vision import read_image_text
from core.ooxml_package import OoxmlPackage
from core.ooxml_docx import DocxReader
from core.pdf_parser import read_pdf_text
from core.pptx_model import PptxDocument, shape_text
from core.vector_store import EnterpriseVectorStore


def read_file_text(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    if extension == ".pdf":
        return read_pdf_text(path)
    if extension == ".docx":
        return "\n".join(DocxReader(path).extract_structure()["paragraphs"])
    if extension == ".pptx":
        return read_pptx_text(path)
    if extension in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    if extension in (".png", ".jpg", ".jpeg"):
        return read_image_text(path)
    raise ValueError(f"Unsupported file type: {extension}")


def read_pptx_text(path: str) -> str:
    """Slide-by-slide text, so a presentation can be summarised or used as a source."""
    doc = PptxDocument(OoxmlPackage.from_file(path))
    slides = []
    for number in range(1, len(doc.slide_parts()) + 1):
        texts = [shape_text(s.el).strip() for s in doc.shapes(number) if s.kind == "text"]
        slides.append(f"Slide {number}: " + "\n".join(t for t in texts if t))
    return "\n\n".join(slides)


class IngestionAgent:
    def __init__(self, vector_store: EnterpriseVectorStore):
        self.name = "Ingestion Agent"
        self.vector_store = vector_store

    def ingest(self, path: str) -> dict:
        filename = os.path.basename(path)
        text = read_file_text(path)
        if not text.strip():
            return {"filename": filename, "chunks_indexed": 0, "words": 0,
                    "warning": "No readable text found (a scanned PDF needs to be uploaded as an image)."}

        chunks = self.vector_store.index_document(doc_id=filename, title=filename, text=text)
        return {"filename": filename, "chunks_indexed": chunks, "words": len(text.split())}
