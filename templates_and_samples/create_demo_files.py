"""
Creates the demo files for the AI editor workspace:
  templates_and_samples/demo/Acme_Proposal_Demo.docx   (logo, title, executive summary, table)
  templates_and_samples/demo/Acme_Pitch_Deck_Demo.pptx (5 slides, logo on every slide)
  templates_and_samples/demo/acme_logo.png             (the original logo)
  templates_and_samples/demo/nova_logo.png             (a different logo to test "replace the logo")
Run from the repo root:  python -m templates_and_samples.create_demo_files
"""
import os
import struct
import zlib
from typing import List, Tuple

from core.ooxml_docx import DocxBuilder
from core.ooxml_pptx import PptxBuilder

DEMO_DIR = os.path.join("templates_and_samples", "demo")
EMU_PER_INCH = 914400
Color = Tuple[int, int, int, int]

# 5x7 bitmap letters, enough for the two logo word marks
GLYPHS = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
}


class Canvas:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.pixels: List[List[Color]] = [[(0, 0, 0, 0)] * width for _ in range(height)]

    def fill(self, inside, color: Color) -> None:
        for y in range(self.height):
            row = self.pixels[y]
            for x in range(self.width):
                if inside(x + 0.5, y + 0.5):
                    row[x] = color

    def rounded_rect(self, x0: int, y0: int, x1: int, y1: int, radius: int, color: Color) -> None:
        def inside(x: float, y: float) -> bool:
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                return False
            cx = min(max(x, x0 + radius), x1 - radius)
            cy = min(max(y, y0 + radius), y1 - radius)
            return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2
        self.fill(inside, color)

    def circle(self, cx: int, cy: int, radius: int, color: Color) -> None:
        self.fill(lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2, color)

    def triangle(self, a: Tuple[int, int], b: Tuple[int, int], c: Tuple[int, int], color: Color) -> None:
        def edge(p, q, x, y):
            return (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0])

        def inside(x: float, y: float) -> bool:
            d1, d2, d3 = edge(a, b, x, y), edge(b, c, x, y), edge(c, a, x, y)
            return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
        self.fill(inside, color)

    def text(self, word: str, x: int, y: int, scale: int, color: Color) -> None:
        for letter in word:
            for row, line in enumerate(GLYPHS[letter]):
                for col, cell in enumerate(line):
                    if cell == "#":
                        for dy in range(scale):
                            for dx in range(scale):
                                self.pixels[y + row * scale + dy][x + col * scale + dx] = color
            x += 6 * scale

    def png(self) -> bytes:
        raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in self.pixels)

        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def acme_logo() -> bytes:
    navy, cyan, white = (27, 54, 93, 255), (0, 163, 224, 255), (255, 255, 255, 255)
    canvas = Canvas(420, 140)
    canvas.rounded_rect(10, 10, 130, 130, 22, navy)
    canvas.triangle((70, 30), (32, 112), (108, 112), white)
    canvas.triangle((70, 72), (55, 112), (85, 112), navy)
    canvas.rounded_rect(28, 116, 112, 122, 3, cyan)
    canvas.text("ACME", 152, 35, 10, navy)
    return canvas.png()


def nova_logo() -> bytes:
    orange, dark, white = (237, 125, 49, 255), (64, 64, 64, 255), (255, 255, 255, 255)
    canvas = Canvas(420, 140)
    canvas.circle(70, 70, 60, orange)
    canvas.circle(70, 70, 32, white)
    canvas.circle(70, 70, 14, orange)
    canvas.text("NOVA", 152, 35, 10, dark)
    return canvas.png()


def build_docx(logo: bytes, path: str) -> None:
    doc = DocxBuilder(title="Acme Intelligent Document Platform", primary_font="Georgia", heading_font="Arial",
                      primary_color="1B365D", secondary_color="00A3E0")
    doc.add_image(logo, int(1.6 * EMU_PER_INCH), name="Company Logo")
    doc.add_title_block("Acme Intelligent Document Platform",
                        "Proposal for Globex Corporation — Document Automation Program",
                        {"Prepared by": "Acme Solutions", "Date": "September 2025"})
    doc.add_heading_1("Executive Summary")
    doc.add_paragraph("Acme proposes a secure, AI-assisted document platform that helps Globex create, review and "
                      "approve proposals and presentations up to 60% faster, while keeping every change traceable.")
    doc.add_heading_1("Solution Overview")
    doc.add_paragraph("The platform combines a conversational editor, retrieval-augmented generation over approved "
                      "company knowledge, and deterministic OpenXML editing, so every change lands in real Word and "
                      "PowerPoint files.")
    doc.add_paragraph("Our enterprise architecture follows a zero-trust model: every service authenticates with "
                      "short-lived tokens, all documents are encrypted at rest, and audit logs are kept for seven years.")
    doc.add_paragraph("Teams keep working in the tools they already know. Files open natively in Microsoft Word and "
                      "PowerPoint, with the corporate template applied automatically.")
    doc.add_heading_1("Implementation Plan")
    doc.add_bullet("Weeks 1-4: connect the knowledge base and import the corporate templates.")
    doc.add_bullet("Weeks 5-8: pilot the editor with the proposals team.")
    doc.add_bullet("Weeks 9-12: roll out to sales and marketing with governance controls.")
    doc.add_table(["Phase", "Scope", "Duration"], [
        ["Discovery", "Templates, knowledge sources, security review", "4 weeks"],
        ["Pilot", "Proposals team, 25 users", "4 weeks"],
        ["Rollout", "Sales and marketing, 400 users", "4 weeks"],
    ])
    doc.add_heading_1("Investment and ROI")
    doc.add_paragraph("The first-year investment is USD 240,000, with an expected payback period of under nine "
                      "months based on reduced drafting and review effort.")
    doc.add_heading_1("Next Steps")
    doc.add_paragraph("We recommend a two-week discovery workshop to confirm scope, success metrics and the pilot team.")
    doc.save(path)


def build_pptx(logo: bytes, path: str) -> None:
    deck = PptxBuilder(title="Acme Intelligent Document Platform", primary_color="1B365D",
                       secondary_color="00A3E0", accent_color="10B981", bg_color="FFFFFF", primary_font="Arial")
    deck.set_logo(logo)
    deck.add_title_slide("Acme Intelligent Document Platform", "Board Briefing — Q3 2025",
                         metadata="Confidential | Prepared for Globex Corporation")
    deck.add_bullet_slide("Market Opportunity", "Why now", [
        "Knowledge workers spend 30% of their week creating and formatting documents",
        "Enterprises maintain thousands of proposal and slide templates",
        "Manual edits introduce brand and compliance errors",
        "Enterprise adoption of generative AI doubled in two years",
    ])
    deck.add_bullet_slide("Our Solution", "Platform", [
        "Chat with your document: plain-English edits applied to real DOCX and PPTX files",
        "Every change is validated, versioned and reversible",
        "Grounded in approved company knowledge with citations",
    ])
    deck.add_metrics_slide("Business Impact", [
        {"value": "60%", "label": "Faster drafting", "desc": "Proposal turnaround in the pilot"},
        {"value": "9 mo", "label": "Payback", "desc": "Based on reduced review effort"},
        {"value": "100%", "label": "Traceable", "desc": "Every edit has a version"},
        {"value": "0", "label": "Template drift", "desc": "Brand styles applied automatically"},
    ])
    deck.add_bullet_slide("Next Steps", "Roadmap", [
        "Two-week discovery workshop",
        "Pilot with the proposals team",
        "Company-wide rollout in Q1",
    ])
    deck.save(path)


def create_demo_files() -> None:
    os.makedirs(DEMO_DIR, exist_ok=True)
    logo = acme_logo()
    with open(os.path.join(DEMO_DIR, "acme_logo.png"), "wb") as f:
        f.write(logo)
    with open(os.path.join(DEMO_DIR, "nova_logo.png"), "wb") as f:
        f.write(nova_logo())
    build_docx(logo, os.path.join(DEMO_DIR, "Acme_Proposal_Demo.docx"))
    build_pptx(logo, os.path.join(DEMO_DIR, "Acme_Pitch_Deck_Demo.pptx"))


if __name__ == "__main__":
    create_demo_files()
    print(f"Demo files written to {DEMO_DIR}")
