"""
Pure-Python PDF Document Parser
Extracts text streams, font declarations, and structural metadata from PDF files.
"""
import re
from typing import Dict, Any, List

class PdfParser:
    def __init__(self, file_source):
        if isinstance(file_source, str):
            with open(file_source, "rb") as f:
                self.data = f.read()
        else:
            self.data = file_source

    def parse(self) -> Dict[str, Any]:
        text_content = []
        raw_str = self.data.decode("latin1", errors="ignore")

        # Find stream objects containing text
        # Simple extraction of text inside BT ... ET operators or (string) Tj / TJ
        # Also extract raw text within parentheses (text) Tj
        tj_matches = re.findall(r'\((.*?)\)\s*Tj', raw_str)
        if tj_matches:
            clean_texts = [m.replace('\\n', ' ').replace('\\r', '').replace('\\', '').strip() for m in tj_matches if len(m.strip()) > 1]
            text_content.extend(clean_texts)

        # Array TJ matches: [(part1) 12 (part2)] TJ
        array_tj = re.findall(r'\[(.*?)\]\s*TJ', raw_str)
        for arr in array_tj:
            parts = re.findall(r'\((.*?)\)', arr)
            if parts:
                text_content.append("".join(parts).strip())

        # Fallback if no standard Tj found: check for plain text streams
        if not text_content:
            streams = re.findall(r'stream[\r\n]+(.*?)[\r\n]+endstream', raw_str, re.DOTALL)
            for s in streams:
                words = re.findall(r'[A-Za-z0-9\.,;\-\s]{4,}', s)
                if words:
                    text_content.extend([w.strip() for w in words if len(w.strip()) > 10])

        combined_text = "\n".join(text_content)
        pages_count = len(re.findall(r'/Type\s*/Page\b', raw_str)) or 1

        # Detect potential headings
        headings = []
        for line in text_content:
            if len(line) < 80 and any(line.lower().startswith(prefix) for prefix in ["section", "chapter", "1.", "2.", "3.", "executive", "overview", "architecture"]):
                headings.append(line)

        return {
            "format": "PDF",
            "page_count": pages_count,
            "text": combined_text,
            "headings": headings,
            "word_count": len(combined_text.split()),
            "status": "parsed"
        }
