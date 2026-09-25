"""
Turns a .pptx into a JSON preview model (slides -> positioned shapes with resolved text styles,
pictures as data URLs), plus a compact outline for the intent parser.
Text size/colour/font are resolved like PowerPoint does: master text styles -> inherited
placeholder list styles -> the shape's list style -> the run's own properties.
"""
import base64
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

from core.docx_styles import read_theme
from core.ooxml_package import DOC_REL_NS, IMAGE_TYPES, OoxmlPackage, image_info
from core.pptx_model import (A, P, PptxDocument, ShapeRef, is_bullet, paragraphs_of, picture_is_logo, shape_text,
                             text_of)

MAX_PREVIEW_IMAGE_BYTES = 3 * 1024 * 1024
OUTLINE_SLIDES = 25
OUTLINE_BULLETS = 10
DEFAULT_CLR_MAP = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
PRESET_COLORS = {"black": "000000", "white": "FFFFFF", "red": "FF0000", "blue": "0000FF", "green": "008000"}


class PptxPreviewBuilder:
    def __init__(self, pkg: OoxmlPackage, changed_shapes: Optional[Set[str]] = None,
                 changed_slides: Optional[Set[int]] = None):
        self.pkg = pkg
        self.doc = PptxDocument(pkg)
        self.changed_shapes = changed_shapes or set()
        self.changed_slides = changed_slides or set()
        self.media: Dict[str, str] = {}
        parts = self.doc.slide_parts()
        self.master = self.doc.master_of(self.doc.layout_of(parts[0])) if parts else None
        theme_part = next((t for _, t in pkg.rels_of_type(self.master, DOC_REL_NS + "/theme")), None) if self.master else None
        self.theme = read_theme(pkg, theme_part)
        master_root = pkg.xml(self.master) if self.master and pkg.has(self.master) else None
        clr_map = master_root.find(P + "clrMap") if master_root is not None else None
        self.clr_map = dict(clr_map.attrib) if clr_map is not None else DEFAULT_CLR_MAP
        self.tx_styles = master_root.find(P + "txStyles") if master_root is not None else None

    # ---------- colours ----------
    def color(self, parent: Optional[ET.Element]) -> Optional[str]:
        fill = parent.find(A + "solidFill") if parent is not None else None
        if fill is None or not len(fill):
            return None
        value = fill[0]
        name = value.tag.split("}")[-1]
        if name == "srgbClr":
            return "#" + value.get("val", "000000").upper()
        if name == "schemeClr":
            slot = value.get("val", "")
            slot = self.clr_map.get(slot, slot)
            return "#" + self.theme["colors"][slot] if slot in self.theme["colors"] else None
        if name == "sysClr":
            return "#" + value.get("lastClr", "000000")
        if name == "prstClr":
            return "#" + PRESET_COLORS.get(value.get("val", ""), "000000")
        return None

    # ---------- text ----------
    def _style_layers(self, shape: ShapeRef, level: int) -> List[ET.Element]:
        """defRPr elements that apply to a paragraph at `level`, from least to most specific."""
        lvl = f"lvl{level + 1}pPr"
        layers: List[ET.Element] = []
        if self.tx_styles is not None:
            kind = "titleStyle" if shape.ph_type in ("title", "ctrTitle") else (
                "bodyStyle" if shape.is_placeholder else "otherStyle")
            found = self.tx_styles.find(f"{P}{kind}/{A}{lvl}/{A}defRPr")
            if found is not None:
                layers.append(found)
        inherited = self.doc.inherited_placeholder(shape.part, shape.ph_type, shape.ph_idx) if shape.is_placeholder else []
        for source in list(reversed(inherited)) + [shape.el]:
            found = source.find(f"{P}txBody/{A}lstStyle/{A}{lvl}/{A}defRPr")
            if found is not None:
                layers.append(found)
        return layers

    def run_style(self, layers: List[ET.Element], rpr: Optional[ET.Element], is_title: bool) -> Dict[str, Any]:
        style: Dict[str, Any] = {"size": 18.0, "bold": False, "italic": False, "underline": False,
                                 "color": None, "font": self.theme["major" if is_title else "minor"]}
        for layer in layers + ([rpr] if rpr is not None else []):
            if layer.get("sz", "").isdigit():
                style["size"] = int(layer.get("sz", "1800")) / 100
            for key, attr in (("bold", "b"), ("italic", "i")):
                if layer.get(attr) is not None:
                    style[key] = layer.get(attr) in ("1", "true")
            if layer.get("u") is not None:
                style["underline"] = layer.get("u") != "none"
            style["color"] = self.color(layer) or style["color"]
            latin = layer.find(A + "latin")
            if latin is not None and latin.get("typeface"):
                face = latin.get("typeface", "")
                style["font"] = {"+mj-lt": self.theme["major"], "+mn-lt": self.theme["minor"]}.get(face, face)
        return style

    def paragraph(self, shape: ShapeRef, p: ET.Element, is_title: bool, number: int) -> Dict[str, Any]:
        ppr = p.find(A + "pPr")
        level = int(ppr.get("lvl", "0")) if ppr is not None and ppr.get("lvl", "0").isdigit() else 0
        layers = self._style_layers(shape, level)
        runs = []
        for child in p:
            if child.tag in (A + "r", A + "fld"):
                runs.append({"text": text_of(child), **self.run_style(layers, child.find(A + "rPr"), is_title)})
            elif child.tag == A + "br":
                runs.append({"text": "\n", **self.run_style(layers, None, is_title)})
        bullet = None
        if text_of(p).strip() and is_bullet(shape, p):
            char = ppr.find(A + "buChar") if ppr is not None else None
            auto = ppr.find(A + "buAutoNum") if ppr is not None else None
            bullet = char.get("char", "•") if char is not None else (f"{number}." if auto is not None else "•")
        end = self.run_style(layers, p.find(A + "endParaRPr"), is_title)
        spacing = ppr.find(f"{A}spcBef/{A}spcPts") if ppr is not None else None
        return {"align": ppr.get("algn", "l") if ppr is not None else "l", "level": level, "bullet": bullet,
                "runs": runs, "size": end["size"],
                "space_before": int(spacing.get("val", "0")) / 100 if spacing is not None else 0}

    # ---------- slides ----------
    def background(self, part: str) -> str:
        layout = self.doc.layout_of(part)
        for source in (part, layout, self.doc.master_of(layout)):
            if source and self.pkg.has(source):
                color = self.color(self.pkg.xml(source).find(f"{P}cSld/{P}bg/{P}bgPr"))
                if color:
                    return color
        return "#FFFFFF"

    def picture_src(self, media: Optional[str]) -> Optional[str]:
        if not media or not self.pkg.has(media):
            return None
        if media not in self.media:
            data = self.pkg.read(media)
            try:
                extension = image_info(data)[0]
            except ValueError:
                return None
            if len(data) > MAX_PREVIEW_IMAGE_BYTES:
                return None
            self.media[media] = f"data:{IMAGE_TYPES[extension]};base64,{base64.b64encode(data).decode()}"
        return media

    def shape(self, s: ShapeRef, title: Optional[ShapeRef]) -> Dict[str, Any]:
        item: Dict[str, Any] = {"id": s.id, "name": s.name, "kind": s.kind, "x": s.x, "y": s.y, "cx": s.cx, "cy": s.cy,
                                "changed": f"{s.slide}:{s.id}" in self.changed_shapes,
                                "is_title": title is not None and s.el is title.el}
        if s.kind == "picture":
            _, media = self.doc.picture_media(s)
            item.update({"media": self.picture_src(media), "is_logo": picture_is_logo(s, media)})
            return item
        sp_pr = s.el.find(P + "spPr")
        geometry = sp_pr.find(A + "prstGeom") if sp_pr is not None else None
        line = sp_pr.find(A + "ln") if sp_pr is not None else None
        item.update({"fill": self.color(sp_pr), "geometry": geometry.get("prst") if geometry is not None else "rect",
                     "line": self.color(line), "line_width": int(line.get("w", "12700")) if line is not None else 0})
        body_pr = s.el.find(f"{P}txBody/{A}bodyPr")
        if s.kind == "text":
            numbered = 0
            paragraphs = []
            for p in paragraphs_of(s.el):
                numbered += 1
                paragraphs.append(self.paragraph(s, p, item["is_title"], numbered))
            item.update({"paragraphs": paragraphs,
                         "anchor": body_pr.get("anchor", "t") if body_pr is not None else "t",
                         "inset": [int(body_pr.get(k, d)) if body_pr is not None else d
                                   for k, d in (("lIns", 91440), ("tIns", 45720), ("rIns", 91440), ("bIns", 45720))]})
        return item

    def build(self) -> Dict[str, Any]:
        width, height = self.doc.slide_size()
        slides = []
        for number in range(1, len(self.doc.slide_parts()) + 1):
            title = self.doc.title_shape(number)
            slides.append({"index": number, "background": self.background(self.doc.slide_part(number)),
                           "title": shape_text(title.el) if title else "",
                           "changed": number in self.changed_slides,
                           "shapes": [self.shape(s, title) for s in self.doc.shapes(number)]})
        return {"type": "pptx", "width": width, "height": height, "slides": slides, "media": self.media}


def pptx_preview(pkg: OoxmlPackage, changed_shapes: Optional[Set[str]] = None,
                 changed_slides: Optional[Set[int]] = None) -> Dict[str, Any]:
    return PptxPreviewBuilder(pkg, changed_shapes, changed_slides).build()


def pptx_outline(pkg: OoxmlPackage) -> str:
    doc = PptxDocument(pkg)
    lines = []
    for number in range(1, min(len(doc.slide_parts()), OUTLINE_SLIDES) + 1):
        title = doc.title_shape(number)
        lines.append(f"Slide {number}: title “{shape_text(title.el).strip() if title else ''}”")
        for index, (_, p) in enumerate(doc.bullets(number)[:OUTLINE_BULLETS], start=1):
            lines.append(f"  bullet {index}: {text_of(p).strip()[:90]}")
        for picture in doc.pictures(number):
            media = doc.picture_media(picture)[1]
            logo = " (logo)" if picture_is_logo(picture, media) else ""
            lines.append(f"  picture: {picture.name or 'unnamed'}{logo}")
    return "\n".join(lines)
