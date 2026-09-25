"""
Turns a .docx into a JSON preview model for the browser (paragraph runs with their *effective*
formatting, tables, header pictures), plus a compact text outline for the intent parser.
The preview is derived from the saved file, so it shows exactly what the download contains.
"""
import base64
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

from core.docx_images import image_label, inches
from core.docx_model import W, DocxDocument, ImageRef, paragraph_text
from core.ooxml_package import IMAGE_TYPES, OoxmlPackage, image_info

EMU_PER_PX = 9525
MAX_PREVIEW_IMAGE_BYTES = 3 * 1024 * 1024
OUTLINE_PARAGRAPHS = 60
OUTLINE_CHARS = 90


class DocxPreviewBuilder:
    def __init__(self, pkg: OoxmlPackage, changed: Optional[Set[int]] = None):
        self.pkg = pkg
        self.doc = DocxDocument(pkg)
        self.changed = changed or set()
        self.media: Dict[str, str] = {}
        self.images = {id(i.drawing): i for i in self.doc.images()}
        self.roles = {}
        for ref in self.doc.paragraphs():
            if ref.pid is not None:
                self.roles[id(ref.p)] = (ref.pid, self.doc.role(ref))

    def build(self) -> Dict[str, Any]:
        header: List[Dict[str, Any]] = []
        footer: List[Dict[str, Any]] = []
        for location, part in self.doc.image_parts():
            if location != "body" and self.pkg.has(part):
                target = header if location == "header" else footer
                target.extend(self.paragraph(p) for p in self.pkg.xml(part).iter(W + "p"))
        return {
            "type": "docx",
            "page": self.page(),
            "header": [p for p in header if p["items"]],
            "footer": [p for p in footer if p["items"]],
            "blocks": [self.block(b) for b in self.doc.blocks()],
            "media": self.media,
            "images": [{"index": i.index, "name": i.name, "location": i.location, "label": image_label(i),
                        "width_in": inches(i.cx), "height_in": inches(i.cy)} for i in self.doc.images()],
        }

    def page(self) -> Dict[str, int]:
        sect = self.doc.body.find(W + "sectPr")
        size = sect.find(W + "pgSz") if sect is not None else None
        margins = sect.find(W + "pgMar") if sect is not None else None

        def read(el: Optional[ET.Element], key: str, default: int) -> int:
            value = el.get(W + key) if el is not None else None
            return int(value) if value and value.lstrip("-").isdigit() else default

        return {"width": read(size, "w", 12240), "height": read(size, "h", 15840),
                "margin_left": read(margins, "left", 1440), "margin_right": read(margins, "right", 1440),
                "margin_top": read(margins, "top", 1440)}

    def block(self, block: ET.Element) -> Dict[str, Any]:
        if block.tag == W + "tbl":
            rows = []
            for tr in block.findall(W + "tr"):
                cells = []
                for tc in tr.findall(W + "tc"):
                    shade = tc.find(f"{W}tcPr/{W}shd")
                    fill = shade.get(W + "fill") if shade is not None else None
                    cells.append({"fill": f"#{fill}" if fill and fill != "auto" else None,
                                  "paragraphs": [self.paragraph(p) for p in tc.findall(W + "p")]})
                rows.append(cells)
            return {"kind": "table", "rows": rows}
        if block.tag == W + "p":
            return self.paragraph(block)
        return {"kind": "p", "items": [{"text": paragraph_text(block)}], "role": "body", "pid": None}

    def paragraph(self, p: ET.Element) -> Dict[str, Any]:
        styles = self.doc.styles
        pid, role = self.roles.get(id(p), (None, "body"))
        items: List[Dict[str, Any]] = []
        for run in p.iter(W + "r"):
            props = styles.run_props(p, run)
            for child in run:
                if child.tag == W + "t" and child.text:
                    self._add_text(items, child.text, props)
                elif child.tag == W + "tab":
                    self._add_text(items, "\t", props)
                elif child.tag in (W + "br", W + "cr"):
                    self._add_text(items, "\n", props)
                elif child.tag == W + "drawing" and id(child) in self.images:
                    items.append(self._image_item(self.images[id(child)]))
        mark = styles.run_props(p, None)
        return {"kind": "p", "pid": pid, "role": role, "align": styles.alignment(p),
                "level": styles.outline_level(p), "list": p.find(f"{W}pPr/{W}numPr") is not None,
                "changed": pid in self.changed if pid else False, "items": items, "size": mark["size"]}

    @staticmethod
    def _add_text(items: List[Dict[str, Any]], text: str, props: Dict[str, Any]) -> None:
        style = {"font": props["font"], "size": props["size"], "bold": props["bold"], "italic": props["italic"],
                 "underline": props["underline"], "color": f"#{props['color']}" if props["color"] else None}
        if items and "text" in items[-1] and all(items[-1].get(k) == v for k, v in style.items()):
            items[-1]["text"] += text
        else:
            items.append({"text": text, **style})

    def _image_item(self, image: ImageRef) -> Dict[str, Any]:
        key = image.media_part or ""
        if key and key not in self.media and self.pkg.has(key):
            data = self.pkg.read(key)
            try:
                extension = image_info(data)[0]
            except ValueError:
                extension = None
            if extension and len(data) <= MAX_PREVIEW_IMAGE_BYTES:
                self.media[key] = f"data:{IMAGE_TYPES[extension]};base64,{base64.b64encode(data).decode()}"
        return {"image": image.index, "media": key if key in self.media else None, "name": image.name,
                "width": round(image.cx / EMU_PER_PX), "height": round(image.cy / EMU_PER_PX),
                "changed": -image.index in self.changed}


def docx_preview(pkg: OoxmlPackage, changed: Optional[Set[int]] = None) -> Dict[str, Any]:
    """`changed` holds paragraph numbers, and negative numbers for changed image indexes."""
    return DocxPreviewBuilder(pkg, changed).build()


def docx_outline(pkg: OoxmlPackage) -> str:
    """Numbered outline the intent parser can use to resolve 'the paragraph about X'."""
    doc = DocxDocument(pkg)
    lines = []
    for ref in doc.content_paragraphs()[:OUTLINE_PARAGRAPHS]:
        text = " ".join(paragraph_text(ref.p).split())
        where = ", in a table" if ref.in_table else ""
        lines.append(f"¶{ref.pid} [{doc.role(ref)}{where}] {text[:OUTLINE_CHARS]}")
    for image in doc.images():
        lines.append(f"Image {image.index} [{image.location}] {image.name or 'unnamed'} "
                     f"{inches(image.cx)}x{inches(image.cy)} in")
    return "\n".join(lines)
