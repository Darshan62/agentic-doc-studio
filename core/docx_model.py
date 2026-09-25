"""
Read-side model of a .docx used by the editor and the preview:
paragraph roles (title / subtitle / heading / body), numbered content paragraphs, text search
across runs, and the pictures in the header, body and footer.
"""
import copy
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.docx_styles import W, StyleSheet
from core.ooxml_package import DOC_REL_NS, OoxmlPackage, PackageError

WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_EMBED = f"{{{DOC_REL_NS}}}embed"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MAX_TITLE_CHARS = 200

# Word rejects rPr/pPr children in the wrong order, so new children are inserted by this order
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
             "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
             "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]
PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange"]


@dataclass
class ParaRef:
    p: ET.Element
    block: ET.Element      # the top-level body element holding it (the paragraph itself, or a table)
    in_table: bool
    pid: Optional[int]     # 1-based number among non-empty paragraphs, None when empty


@dataclass
class ImageRef:
    index: int             # 1-based, header images first, then body, then footer
    part: str
    drawing: ET.Element
    rel_id: str
    media_part: Optional[str]
    name: str
    location: str          # "header" | "body" | "footer"
    cx: int
    cy: int


def local(tag: str) -> str:
    return tag.split("}")[-1]


def set_ordered(parent: ET.Element, name: str, order: List[str], attrs: Optional[Dict[str, str]] = None) -> ET.Element:
    """Replaces child w:<name> with a fresh element placed where the schema expects it."""
    for old in parent.findall(W + name):
        parent.remove(old)
    element = ET.Element(W + name, attrs or {})
    rank = order.index(name)
    position = len(parent)
    for i, child in enumerate(parent):
        child_name = local(child.tag)
        if child.tag.startswith(W) and child_name in order and order.index(child_name) > rank:
            position = i
            break
    parent.insert(position, element)
    return element


def ensure_first(parent: ET.Element, name: str) -> ET.Element:
    """w:rPr must be the first child of w:r and w:pPr the first child of w:p."""
    found = parent.find(W + name)
    if found is None:
        found = ET.Element(W + name)
        parent.insert(0, found)
    return found


def paragraph_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def phrase_pattern(phrase: str) -> re.Pattern:
    """Case-insensitive pattern that tolerates extra spaces and curly vs straight quotes/dashes."""
    parts = []
    for ch in phrase.strip():
        if ch.isspace():
            if parts and parts[-1] != r"\s+":
                parts.append(r"\s+")
        elif ch in "'‘’":
            parts.append("['‘’]")
        elif ch in '"“”':
            parts.append('["“”]')
        elif ch in "-–—":
            parts.append("[-–—]")
        else:
            parts.append(re.escape(ch))
    return re.compile("".join(parts), re.IGNORECASE)


def preserve_space(t: ET.Element) -> None:
    text = t.text or ""
    if text != text.strip():
        t.set(XML_SPACE, "preserve")


def replace_range(p: ET.Element, start: int, end: int, replacement: str, ns: str = W) -> None:
    """Replaces characters [start, end) of the paragraph text, keeping the first run's formatting.
    Works for Word (w:r/w:t) and DrawingML (a:r/a:t) paragraphs: `ns` picks the namespace."""
    position, written = 0, False
    for t in list(p.iter(ns + "t")):
        text = t.text or ""
        t_start, t_end = position, position + len(text)
        position = t_end
        if t_end <= start or t_start >= end:
            continue
        cut_from, cut_to = max(start, t_start) - t_start, min(end, t_end) - t_start
        t.text = text[:cut_from] + ("" if written else replacement) + text[cut_to:]
        written = True
        if ns == W:
            preserve_space(t)
    remove_empty_runs(p, ns)


def remove_empty_runs(p: ET.Element, ns: str = W) -> None:
    parents = {child: parent for parent in p.iter() for child in parent}
    for run in list(p.iter(ns + "r")):
        content = [c for c in run if c.tag != ns + "rPr"]
        if content and all(c.tag == ns + "t" and not c.text for c in content):
            parents[run].remove(run)


def isolate_runs(p: ET.Element, start: int, end: int) -> List[ET.Element]:
    """Splits runs at `start` and `end` so the range is covered by whole runs, and returns them."""
    for cut in (end, start):
        parents = {child: parent for parent in p.iter() for child in parent}
        position = 0
        for run in list(p.iter(W + "r")):
            texts = run.findall(W + "t")
            length = sum(len(t.text or "") for t in texts)
            if position < cut < position + length and len(texts) == 1:
                offset = cut - position
                clone = copy.deepcopy(run)
                clone_t = clone.findall(W + "t")[0]
                full = texts[0].text or ""
                texts[0].text, clone_t.text = full[:offset], full[offset:]
                preserve_space(texts[0])
                preserve_space(clone_t)
                parent = parents[run]
                parent.insert(list(parent).index(run) + 1, clone)
                break
            position += length
    runs, position = [], 0
    for run in p.iter(W + "r"):
        length = sum(len(t.text or "") for t in run.findall(W + "t"))
        if length and position < end and position + length > start:
            runs.append(run)
        position += length
    return runs


class DocxDocument:
    def __init__(self, pkg: OoxmlPackage):
        self.pkg = pkg
        self.part = pkg.main_part()
        self.root = pkg.xml(self.part)
        body = self.root.find(W + "body")
        if body is None:
            raise PackageError("The document has no body, so it cannot be edited.")
        self.body = body
        self.styles = StyleSheet(pkg, self.part)

    # ---------- paragraphs ----------
    def blocks(self) -> List[ET.Element]:
        return [c for c in self.body if c.tag != W + "sectPr"]

    def paragraphs(self) -> List[ParaRef]:
        refs: List[ParaRef] = []
        pid = 0
        for block in self.blocks():
            paras = [block] if block.tag == W + "p" else list(block.iter(W + "p"))
            for p in paras:
                has_text = bool(paragraph_text(p).strip())
                pid += 1 if has_text else 0
                refs.append(ParaRef(p, block, block.tag == W + "tbl", pid if has_text else None))
        return refs

    def content_paragraphs(self) -> List[ParaRef]:
        return [r for r in self.paragraphs() if r.pid is not None]

    def parent_of(self, element: ET.Element) -> ET.Element:
        for parent in self.body.iter():
            if element in list(parent):
                return parent
        raise PackageError("Could not locate the paragraph in the document.")

    def title(self) -> Optional[ParaRef]:
        content = self.content_paragraphs()
        styled = [r for r in content if self.styles.has_style_name(r.p, "title")]
        if styled:
            return styled[0]
        # No Title style: the first short top-level paragraph before any heading is the title
        for ref in content:
            if ref.in_table or self.styles.outline_level(ref.p) is not None:
                return None
            return ref if len(paragraph_text(ref.p)) <= MAX_TITLE_CHARS else None
        return None

    def subtitle(self) -> Optional[ParaRef]:
        content = self.content_paragraphs()
        styled = [r for r in content if self.styles.has_style_name(r.p, "subtitle")]
        if styled:
            return styled[0]
        title = self.title()
        if title is None or title.pid is None or title.pid >= len(content):
            return None
        candidate = content[title.pid]  # pid is 1-based, so this is the next paragraph
        is_centered = self.styles.alignment(candidate.p) == "center"
        if not candidate.in_table and is_centered and self.styles.outline_level(candidate.p) is None:
            return candidate
        return None

    def role(self, ref: ParaRef) -> str:
        title, subtitle = self.title(), self.subtitle()
        if title is not None and ref.p is title.p:
            return "title"
        if subtitle is not None and ref.p is subtitle.p:
            return "subtitle"
        if self.styles.outline_level(ref.p) is not None:
            return "heading"
        return "body"

    def find_paragraphs(self, phrase: str, refs: Optional[List[ParaRef]] = None) -> List[ParaRef]:
        """Paragraphs containing the phrase; falls back to paragraphs containing all its keywords."""
        refs = refs if refs is not None else self.content_paragraphs()
        pattern = phrase_pattern(phrase)
        exact = [r for r in refs if pattern.search(paragraph_text(r.p))]
        if exact:
            return exact
        words = [w for w in re.findall(r"[a-z0-9]+", phrase.lower()) if len(w) > 2 and w not in STOPWORDS]
        if not words:
            return []
        return [r for r in refs if all(re.search(rf"\b{re.escape(w)}", paragraph_text(r.p).lower()) for w in words)]

    # ---------- images ----------
    def image_parts(self) -> List[Tuple[str, str]]:
        headers = [("header", t) for _, t in self.pkg.rels_of_type(self.part, DOC_REL_NS + "/header")]
        footers = [("footer", t) for _, t in self.pkg.rels_of_type(self.part, DOC_REL_NS + "/footer")]
        return sorted(headers) + [("body", self.part)] + sorted(footers)

    def images(self) -> List[ImageRef]:
        images: List[ImageRef] = []
        for location, part in self.image_parts():
            if not self.pkg.has(part):
                continue
            for drawing in self.pkg.xml(part).iter(W + "drawing"):
                blip = next(drawing.iter(A + "blip"), None)
                extent = next(drawing.iter(WP + "extent"), None)
                props = next(drawing.iter(WP + "docPr"), None)
                if blip is None or extent is None:
                    continue
                rel_id = blip.get(R_EMBED, "")
                media = self.pkg.rel_target(part, rel_id)
                name = " ".join(filter(None, [props.get("name") if props is not None else "",
                                              props.get("descr") if props is not None else ""]))
                images.append(ImageRef(len(images) + 1, part, drawing, rel_id, media, name.strip(), location,
                                       int(extent.get("cx", "0")), int(extent.get("cy", "0"))))
        return images


STOPWORDS = {"the", "and", "about", "that", "this", "with", "for", "from", "which", "paragraph", "line",
             "sentence", "section", "text", "mentions", "mentioning", "talks", "regarding"}
