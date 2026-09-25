"""
Read-side model of a .pptx: slides in presentation order, shapes with their real position
(placeholders inherit it from the slide layout / master), the title, the bullets and pictures.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.edit_schema import EditError
from core.ooxml_package import DOC_REL_NS, OoxmlPackage, PackageError

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = f"{{{P_NS}}}"
A = f"{{{A_NS}}}"
R_ID = f"{{{DOC_REL_NS}}}id"
R_EMBED = f"{{{DOC_REL_NS}}}embed"
TITLE_TYPES = {"title", "ctrTitle"}
BODY_PH_TYPES = {"body", "obj", None}  # a placeholder with an idx but no type is a content placeholder
FURNITURE_PH_TYPES = {"dt", "ftr", "sldNum", "hdr"}
FURNITURE_NAMES = ("category", "footer", "slide number", "date")
DEFAULT_SLIDE_SIZE = (12192000, 6858000)


@dataclass
class ShapeRef:
    el: ET.Element
    slide: int                  # 1-based slide number
    part: str
    id: str
    name: str
    kind: str                   # "text" | "picture" | "shape"
    ph_type: Optional[str]
    ph_idx: Optional[str]
    is_placeholder: bool
    x: int
    y: int
    cx: int
    cy: int


def text_of(p: ET.Element) -> str:
    return "".join((t.text or "") for t in p.iter(A + "t"))


def paragraphs_of(shape: ET.Element) -> List[ET.Element]:
    body = shape.find(P + "txBody")
    return body.findall(A + "p") if body is not None else []


def shape_text(shape: ET.Element) -> str:
    return "\n".join(text_of(p) for p in paragraphs_of(shape))


def _placeholder(el: ET.Element) -> Tuple[bool, Optional[str], Optional[str]]:
    ph = next(el.iter(P + "ph"), None)
    if ph is None:
        return False, None, None
    return True, ph.get("type"), ph.get("idx")


def _read_xfrm(el: ET.Element) -> Optional[Tuple[int, int, int, int]]:
    sp_pr = el.find(P + "spPr")
    xfrm = sp_pr.find(A + "xfrm") if sp_pr is not None else None
    if xfrm is None:
        return None
    off, ext = xfrm.find(A + "off"), xfrm.find(A + "ext")
    if off is None or ext is None:
        return None
    return int(off.get("x", 0)), int(off.get("y", 0)), int(ext.get("cx", 0)), int(ext.get("cy", 0))


class PptxDocument:
    def __init__(self, pkg: OoxmlPackage):
        self.pkg = pkg
        self.part = pkg.main_part()
        self.root = pkg.xml(self.part)
        if self.root.find(P + "sldIdLst") is None and not self.slide_parts():
            raise PackageError("This presentation has no slides.")

    # ---------- slides ----------
    def slide_parts(self) -> List[str]:
        parts = []
        id_list = self.root.find(P + "sldIdLst")
        for sld in list(id_list) if id_list is not None else []:
            target = self.pkg.rel_target(self.part, sld.get(R_ID, ""))
            if target and self.pkg.has(target):
                parts.append(target)
        return parts

    def slide_size(self) -> Tuple[int, int]:
        size = self.root.find(P + "sldSz")
        if size is None:
            return DEFAULT_SLIDE_SIZE
        return int(size.get("cx", DEFAULT_SLIDE_SIZE[0])), int(size.get("cy", DEFAULT_SLIDE_SIZE[1]))

    def slide_part(self, number: int) -> str:
        parts = self.slide_parts()
        if not 1 <= number <= len(parts):
            count = len(parts)
            raise EditError(f"There is no slide {number}; the presentation has {count} slide{'s' if count != 1 else ''}.")
        return parts[number - 1]

    def layout_of(self, part: str) -> Optional[str]:
        return next((t for _, t in self.pkg.rels_of_type(part, DOC_REL_NS + "/slideLayout")), None)

    def master_of(self, layout: Optional[str]) -> Optional[str]:
        if not layout:
            return None
        return next((t for _, t in self.pkg.rels_of_type(layout, DOC_REL_NS + "/slideMaster")), None)

    def inherited_placeholder(self, part: str, ph_type: Optional[str], ph_idx: Optional[str]) -> List[ET.Element]:
        """The matching placeholder shape on the slide layout, then on the master."""
        found: List[ET.Element] = []
        layout = self.layout_of(part)
        for source in (layout, self.master_of(layout)):
            if not source or not self.pkg.has(source):
                continue
            for el in self.pkg.xml(source).iter(P + "sp"):
                is_ph, other_type, other_idx = _placeholder(el)
                if not is_ph:
                    continue
                same_idx = ph_idx is not None and other_idx == ph_idx
                same_type = (other_type or "body") == (ph_type or "body") or (ph_type in TITLE_TYPES and other_type in TITLE_TYPES)
                if same_idx or (source != layout and same_type) or (ph_idx is None and same_type):
                    found.append(el)
                    break
        return found

    # ---------- shapes ----------
    def shapes(self, number: int) -> List[ShapeRef]:
        part = self.slide_part(number)
        tree = self.pkg.xml(part).find(f"{P}cSld/{P}spTree")
        shapes: List[ShapeRef] = []
        for el in tree.iter() if tree is not None else []:
            kind = {P + "sp": "shape", P + "pic": "picture"}.get(el.tag)
            if kind is None:
                continue
            props = next(el.iter(P + "cNvPr"), None)
            is_ph, ph_type, ph_idx = _placeholder(el)
            box = _read_xfrm(el)
            if box is None and is_ph:
                box = next((b for b in map(_read_xfrm, self.inherited_placeholder(part, ph_type, ph_idx)) if b), None)
            if kind == "shape" and el.find(P + "txBody") is not None and (shape_text(el).strip() or is_ph):
                kind = "text"
            x, y, cx, cy = box or (0, 0, 0, 0)
            shapes.append(ShapeRef(el, number, part, props.get("id", "") if props is not None else "",
                                   props.get("name", "") if props is not None else "", kind,
                                   ph_type, ph_idx, is_ph, x, y, cx, cy))
        return shapes

    def title_shape(self, number: int) -> Optional[ShapeRef]:
        texts = [s for s in self.shapes(number) if s.kind == "text"]
        for shape in texts:
            if shape.ph_type in TITLE_TYPES:
                return shape
        named = [s for s in texts if s.name.lower().startswith("title") and shape_text(s.el).strip()]
        if named:
            return named[0]
        # No title placeholder: the biggest text in the top 40% of the slide
        height = self.slide_size()[1]
        candidates = [s for s in texts if s.y < height * 0.4 and shape_text(s.el).strip() and not is_furniture(s)]
        return max(candidates, key=lambda s: (max_font_size(s.el), -s.y), default=None)

    def body_shapes(self, number: int) -> List[ShapeRef]:
        title = self.title_shape(number)
        shapes = [s for s in self.shapes(number)
                  if s.kind == "text" and (title is None or s.el is not title.el) and not is_furniture(s)]
        return sorted(shapes, key=lambda s: (s.y, s.x))

    def bullets(self, number: int) -> List[Tuple[ShapeRef, ET.Element]]:
        """Bullet paragraphs in reading order. Falls back to all body paragraphs if none are bullets."""
        body = [(s, p) for s in self.body_shapes(number) for p in paragraphs_of(s.el) if text_of(p).strip()]
        bullets = [(s, p) for s, p in body if is_bullet(s, p)]
        return bullets or body

    def pictures(self, number: Optional[int] = None) -> List[ShapeRef]:
        numbers = [number] if number else range(1, len(self.slide_parts()) + 1)
        return [s for n in numbers for s in self.shapes(n) if s.kind == "picture"]

    def picture_media(self, shape: ShapeRef) -> Tuple[Optional[str], Optional[str]]:
        blip = next(shape.el.iter(A + "blip"), None)
        rel_id = blip.get(R_EMBED) if blip is not None else None
        return rel_id, self.pkg.rel_target(shape.part, rel_id) if rel_id else None


def is_furniture(shape: ShapeRef) -> bool:
    return shape.ph_type in FURNITURE_PH_TYPES or shape.name.lower().startswith(FURNITURE_NAMES)


def is_bullet(shape: ShapeRef, p: ET.Element) -> bool:
    ppr = p.find(A + "pPr")
    if ppr is not None:
        if ppr.find(A + "buNone") is not None:
            return False
        if ppr.find(A + "buChar") is not None or ppr.find(A + "buAutoNum") is not None:
            return True
    return shape.is_placeholder and shape.ph_type in BODY_PH_TYPES


def max_font_size(shape: ET.Element) -> int:
    sizes = [int(r.get("sz", "0")) for r in shape.iter(A + "rPr") if r.get("sz", "").isdigit()]
    return max(sizes, default=1800)


def picture_is_logo(shape: ShapeRef, media: Optional[str]) -> bool:
    props = next(shape.el.iter(P + "cNvPr"), None)
    descr = props.get("descr", "") if props is not None else ""
    return "logo" in f"{shape.name} {descr} {media or ''}".lower()


def shape_map(shapes: List[ShapeRef]) -> Dict[str, ShapeRef]:
    return {s.id: s for s in shapes}
