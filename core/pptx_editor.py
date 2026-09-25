"""
Deterministic PPTX editor: applies one validated edit command to the presentation in memory.
Slide layout is preserved: text is changed inside the existing shapes and new bullets are
cloned from an existing bullet, so they inherit its formatting.
"""
import copy
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from core.docx_model import phrase_pattern, replace_range
from core.edit_describe import describe_changes, describe_target, plural, snippet
from core.edit_schema import ClarificationNeeded, EditError, EditOutcome
from core.ooxml_package import OoxmlPackage
from core.pptx_images import apply_image_command
from core.pptx_model import A, P, R_ID, PptxDocument, ShapeRef, paragraphs_of, shape_text, text_of

RPR_ORDER = ["ln", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill", "effectLst", "effectDag",
             "highlight", "uLnTx", "uLn", "uFillTx", "uFill", "latin", "ea", "cs", "sym", "hlinkClick",
             "hlinkMouseOver", "rtl", "extLst"]
FILL_TAGS = {"noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill"}
ALIGN = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}
SLIDE_REL_TYPE_SUFFIX = "/slide"


def insert_ordered(rpr: ET.Element, element: ET.Element) -> None:
    rank = RPR_ORDER.index(element.tag.split("}")[-1])
    for i, child in enumerate(rpr):
        name = child.tag.split("}")[-1]
        if name in RPR_ORDER and RPR_ORDER.index(name) > rank:
            rpr.insert(i, element)
            return
    rpr.append(element)


def apply_run_changes(rpr: ET.Element, changes: Dict[str, Any]) -> None:
    if "font_size" in changes:
        rpr.set("sz", str(int(round(changes["font_size"] * 100))))
    for key, attr in (("bold", "b"), ("italic", "i")):
        if key in changes:
            rpr.set(attr, "1" if changes[key] else "0")
    if "underline" in changes:
        rpr.set("u", "sng" if changes["underline"] else "none")
    if "color" in changes:
        for child in list(rpr):
            if child.tag.split("}")[-1] in FILL_TAGS:
                rpr.remove(child)
        fill = ET.Element(A + "solidFill")
        ET.SubElement(fill, A + "srgbClr", {"val": changes["color"]})
        insert_ordered(rpr, fill)
    if "font_family" in changes:
        for tag in ("latin", "cs"):
            for old in rpr.findall(A + tag):
                rpr.remove(old)
            insert_ordered(rpr, ET.Element(A + tag, {"typeface": changes["font_family"]}))


def style_paragraph(p: ET.Element, changes: Dict[str, Any]) -> None:
    run_changes = {k: v for k, v in changes.items() if k != "align"}
    if run_changes:
        for run in list(p.findall(A + "r")) + list(p.findall(A + "fld")):
            rpr = run.find(A + "rPr")
            if rpr is None:
                rpr = ET.Element(A + "rPr", {"lang": "en-US", "dirty": "0"})
                run.insert(0, rpr)
            apply_run_changes(rpr, run_changes)
        end = p.find(A + "endParaRPr")
        if end is not None:
            apply_run_changes(end, run_changes)
    if "align" in changes:
        ppr = p.find(A + "pPr")
        if ppr is None:
            ppr = ET.Element(A + "pPr")
            p.insert(0, ppr)
        ppr.set("algn", ALIGN[changes["align"]])


class PptxEditor:
    def __init__(self, pkg: OoxmlPackage, current_slide: int = 1):
        self.pkg = pkg
        self.doc = PptxDocument(pkg)
        self.current_slide = current_slide

    def apply(self, cmd: Dict[str, Any], image_bytes: Optional[bytes] = None) -> EditOutcome:
        action = cmd["action"]
        if action in ("replace_image", "resize_image", "move_image"):
            return apply_image_command(self.doc, cmd, image_bytes)
        if action == "delete_slide":
            return self.delete_slide(cmd["target"]["slide"])
        if action == "update_style":
            return self.update_style(cmd)
        if action == "update_text":
            return self.update_text(cmd)
        if action == "replace_text":
            return self.replace_text(cmd, cmd["target_text"], cmd["replacement_text"])
        if action == "delete_text":
            if "target_text" in cmd:
                return self.replace_text(cmd, cmd["target_text"], "")
            return self.delete_paragraph(cmd)
        if action == "add_text":
            return self.add_text(cmd)
        raise EditError(f"'{action}' is not supported for presentations.")

    # ---------- targets ----------
    def slide_of(self, target: Optional[Dict[str, Any]]) -> int:
        return (target or {}).get("slide") or self.current_slide

    def resolve(self, target: Dict[str, Any]) -> List[Tuple[ShapeRef, List[ET.Element]]]:
        """(shape, paragraphs) pairs the target points at, with the target's slide as default."""
        kind, number = target["type"], self.slide_of(target)
        if kind == "document":
            numbers = range(1, len(self.doc.slide_parts()) + 1)
            return [(s, paragraphs_of(s.el)) for n in numbers for s in self.doc.shapes(n) if s.kind == "text"]
        if kind in ("title", "subtitle"):
            shape = self.doc.title_shape(number) if kind == "title" else self._subtitle(number)
            if shape is None:
                raise EditError(f"I couldn't find a {kind} on slide {number}.")
            return [(shape, paragraphs_of(shape.el))]
        if kind == "shape":
            matches = [s for s in self.doc.shapes(number) if s.id == target.get("shape_id") and s.kind == "text"]
            if not matches:
                raise EditError("The selected box has no text. Select a text box in the preview.")
            return [(matches[0], paragraphs_of(matches[0].el))]
        if kind in ("body", "slide", "paragraph", "text", "heading", "headings"):
            shapes = self.doc.body_shapes(number)
            if kind == "slide":
                title = self.doc.title_shape(number)
                shapes = ([title] if title else []) + shapes
            if target.get("text") and kind != "slide":
                pattern = phrase_pattern(target["text"])
                return [(s, [p for p in paragraphs_of(s.el) if pattern.search(text_of(p))])
                        for n in self._slides_for(target) for s in self.doc.shapes(n)
                        if s.kind == "text" and any(pattern.search(text_of(p)) for p in paragraphs_of(s.el))]
            if target.get("index") and kind != "slide":
                return [self._bullet(number, target["index"])]
            return [(s, paragraphs_of(s.el)) for s in shapes]
        if kind == "bullet":
            if not target.get("index"):
                bullets = self.doc.bullets(number)
                return [(s, [p]) for s, p in bullets]
            return [self._bullet(number, target["index"])]
        raise EditError(f"I can't use {describe_target(target)} as a text target.")

    def _slides_for(self, target: Dict[str, Any]) -> List[int]:
        return [target["slide"]] if target.get("slide") else list(range(1, len(self.doc.slide_parts()) + 1))

    def _subtitle(self, number: int) -> Optional[ShapeRef]:
        for shape in self.doc.shapes(number):
            if shape.kind == "text" and (shape.ph_type == "subTitle" or shape.name.lower().startswith("subtitle")):
                return shape
        return None

    def _bullet(self, number: int, index: int) -> Tuple[ShapeRef, List[ET.Element]]:
        bullets = self.doc.bullets(number)
        if index == -1 and bullets:
            index = len(bullets)
        if not 1 <= index <= len(bullets):
            raise EditError(f"Slide {number} has {plural(len(bullets), 'bullet')}, so there is no bullet {index}.")
        shape, p = bullets[index - 1]
        return shape, [p]

    # ---------- operations ----------
    def update_style(self, cmd: Dict[str, Any]) -> EditOutcome:
        target, changes = cmd["target"], cmd["changes"]
        resolved = self.resolve(target)
        if not resolved:
            raise EditError(f"I couldn't find {describe_target(target)}.")
        for _, paragraphs in resolved:
            for p in paragraphs:
                style_paragraph(p, changes)
        return self._outcome(f"formatted {self._where(target)}: {describe_changes(changes)}", resolved)

    def update_text(self, cmd: Dict[str, Any]) -> EditOutcome:
        target = cmd["target"]
        resolved = self.resolve(target)
        if len(resolved) != 1 or not resolved[0][1]:
            raise ClarificationNeeded("Which text box should I change? Click it in the preview or name it (e.g. the title).")
        shape, paragraphs = resolved[0]
        old = "\n".join(text_of(p) for p in paragraphs)
        first = paragraphs[0]
        if first.find(f".//{A}t") is None:
            run = ET.Element(A + "r")
            ET.SubElement(run, A + "t").text = ""
            first.insert(1 if first.find(A + "pPr") is not None else 0, run)
        replace_range(first, 0, len(text_of(first)), cmd["text"], ns=A)
        body = shape.el.find(P + "txBody")
        if target["type"] not in ("bullet", "paragraph") and body is not None:
            for extra in paragraphs[1:]:
                body.remove(extra)
        return self._outcome(f"changed {self._where(target)} from “{snippet(old)}” to “{snippet(cmd['text'])}”",
                             [(shape, [first])])

    def replace_text(self, cmd: Dict[str, Any], find: str, replacement: str) -> EditOutcome:
        pattern, count = phrase_pattern(find), 0
        touched: List[Tuple[ShapeRef, List[ET.Element]]] = []
        scope = self.resolve(cmd.get("target") or {"type": "document"})
        for shape, paragraphs in scope:
            for p in paragraphs:
                matches = list(pattern.finditer(text_of(p)))
                for match in reversed(matches):
                    start, end = match.start(), match.end()
                    text = text_of(p)
                    if not replacement and end < len(text) and text[end] == " ":
                        end += 1
                    replace_range(p, start, end, replacement, ns=A)
                if matches:
                    count += len(matches)
                    touched.append((shape, [p]))
        if not count:
            raise EditError(f"I couldn't find “{snippet(find)}” in the presentation.")
        where = f" ({plural(count, 'place')})" if count > 1 else ""
        verb = f"replaced “{snippet(find)}” with “{snippet(replacement)}”" if replacement else f"deleted “{snippet(find)}”"
        return self._outcome(verb + where, touched)

    def delete_paragraph(self, cmd: Dict[str, Any]) -> EditOutcome:
        target = cmd["target"]
        resolved = self.resolve(target)
        pairs = [(s, p) for s, paragraphs in resolved for p in paragraphs]
        if len(pairs) != 1:
            if not pairs:
                raise EditError(f"I couldn't find {describe_target(target)}.")
            raise ClarificationNeeded(f"That matches {len(pairs)} lines. Which bullet number should I remove?")
        shape, p = pairs[0]
        body = shape.el.find(P + "txBody")
        if body is None:
            raise EditError("That text box can't be edited.")
        removed = text_of(p)
        body.remove(p)
        if not body.findall(A + "p"):
            ET.SubElement(body, A + "p")  # a text body must keep at least one paragraph
        return self._outcome(f"removed {self._where(target)} (“{snippet(removed)}”)", [(shape, [])])

    def add_text(self, cmd: Dict[str, Any]) -> EditOutcome:
        target = cmd.get("target") or {"type": "slide"}
        number = self.slide_of(target)
        bullets = self.doc.bullets(number)
        if target.get("shape_id"):
            bullets = [(s, p) for s, p in bullets if s.id == target["shape_id"]] or bullets
        if not bullets:
            raise EditError(f"Slide {number} has no text box with bullets to add to.")
        anchor_index = len(bullets)
        position = cmd.get("position")
        if position and position.get("anchor", {}).get("index"):
            anchor_index = min(max(position["anchor"]["index"], 1), len(bullets))
            if position["where"] == "before":
                anchor_index -= 1
        shape, template = bullets[max(anchor_index, 1) - 1]
        body = shape.el.find(P + "txBody")
        if body is None:
            raise EditError("That text box can't be edited.")
        new_p = copy.deepcopy(template)
        replace_range(new_p, 0, len(text_of(new_p)), cmd["text"], ns=A)
        siblings = list(body)
        insert_at = siblings.index(template) + (0 if anchor_index == 0 else 1)
        body.insert(insert_at, new_p)
        return self._outcome(f"added a bullet to slide {number}: “{snippet(cmd['text'])}”", [(shape, [new_p])])

    def delete_slide(self, number: int) -> EditOutcome:
        parts = self.doc.slide_parts()
        if len(parts) <= 1:
            raise EditError("A presentation needs at least one slide, so I can't delete the last one.")
        part = self.doc.slide_part(number)
        title = self.doc.title_shape(number)
        id_list = self.doc.root.find(P + "sldIdLst")
        if id_list is None:
            raise EditError("This presentation has no slide list, so I can't delete slides from it.")
        for sld in list(id_list):
            if self.pkg.rel_target(self.doc.part, sld.get(R_ID, "")) == part:
                id_list.remove(sld)
                self.pkg.remove_rel(self.doc.part, sld.get(R_ID, ""))
        # Notes pages belong to the slide; pictures may be shared with other slides, so they stay
        for _, notes in self.pkg.rels_of_type(part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"):
            for name in (notes, self.pkg.rels_name(notes)):
                self.pkg.remove_override(name)
                self.pkg.remove(name)
        for name in (part, self.pkg.rels_name(part)):
            self.pkg.remove_override(name)
            self.pkg.remove(name)
        label = f" (“{snippet(shape_text(title.el), 40)}”)" if title else ""
        return EditOutcome(f"deleted slide {number}{label}", slides=[min(number, len(parts) - 1)])

    # ---------- helpers ----------
    def _where(self, target: Dict[str, Any]) -> str:
        if target["type"] in ("title", "subtitle", "body", "bullet") and not target.get("slide"):
            return describe_target({**target, "slide": self.current_slide})
        return describe_target(target)

    @staticmethod
    def _outcome(summary: str, touched: List[Tuple[ShapeRef, List[ET.Element]]]) -> EditOutcome:
        return EditOutcome(summary, slides=sorted({s.slide for s, _ in touched}),
                           shapes=[f"{s.slide}:{s.id}" for s, _ in touched])
