"""
Deterministic DOCX editor. Applies one validated edit command to the parsed document in memory;
nothing is written to disk here (the workspace agent saves only after every command succeeded).
"""
import copy
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from core.docx_images import resize_image, resolve_image, replace_image
from core.docx_model import (PPR_ORDER, RPR_ORDER, W, DocxDocument, ParaRef, ensure_first, isolate_runs,
                             paragraph_text, phrase_pattern, preserve_space, replace_range, set_ordered)
from core.edit_describe import describe_changes, describe_target, plural, snippet
from core.edit_schema import ClarificationNeeded, EditError, EditOutcome
from core.ooxml_package import OoxmlPackage

JC_VALUES = {"left": "left", "center": "center", "right": "right", "justify": "both"}


def apply_run_changes(rpr: ET.Element, changes: Dict[str, Any]) -> None:
    if "font_family" in changes:
        font = changes["font_family"]
        # Explicit names only: a leftover w:asciiTheme would override w:ascii
        set_ordered(rpr, "rFonts", RPR_ORDER, {W + "ascii": font, W + "hAnsi": font, W + "cs": font, W + "eastAsia": font})
    for key, tags in (("bold", ("b", "bCs")), ("italic", ("i", "iCs"))):
        if key in changes:
            for tag in tags:
                set_ordered(rpr, tag, RPR_ORDER, {} if changes[key] else {W + "val": "0"})
    if "color" in changes:
        set_ordered(rpr, "color", RPR_ORDER, {W + "val": changes["color"]})
    if "font_size" in changes:
        half_points = str(int(round(changes["font_size"] * 2)))
        set_ordered(rpr, "sz", RPR_ORDER, {W + "val": half_points})
        set_ordered(rpr, "szCs", RPR_ORDER, {W + "val": half_points})
    if "underline" in changes:
        set_ordered(rpr, "u", RPR_ORDER, {W + "val": "single" if changes["underline"] else "none"})


class DocxEditor:
    def __init__(self, pkg: OoxmlPackage):
        self.pkg = pkg
        self.doc = DocxDocument(pkg)

    def apply(self, cmd: Dict[str, Any], image_bytes: Optional[bytes] = None) -> EditOutcome:
        action = cmd["action"]
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
        if action == "delete_paragraph":
            return self.delete_paragraph(cmd)
        if action == "insert_paragraph":
            return self.insert_paragraph(cmd)
        if action == "insert_text":
            return self.insert_text(cmd)
        if action in ("replace_image", "resize_image"):
            image = resolve_image(self.doc, cmd)
            if action == "resize_image":
                return EditOutcome(resize_image(self.doc, image, cmd["scale"]), images=[image.index])
            if image_bytes is None:
                raise EditError("Upload the new image first (use the 📎 button), then ask me to replace the logo.")
            return EditOutcome(replace_image(self.doc, image, image_bytes), images=[image.index])
        raise EditError(f"'{action}' is not supported for Word documents.")

    # ---------- targets ----------
    def resolve(self, target: Dict[str, Any]) -> List[ParaRef]:
        doc, kind = self.doc, target["type"]
        content = doc.content_paragraphs()
        if kind in ("title", "subtitle"):
            ref = doc.title() if kind == "title" else doc.subtitle()
            if ref is None:
                raise EditError(f"I couldn't find a {kind} in this document.")
            return [ref]
        if kind in ("heading", "headings"):
            headings = [r for r in content if doc.role(r) == "heading"]
            if target.get("index"):
                return self._pick(headings, target["index"], "heading")
            if target.get("text"):
                # "the Executive Summary heading" may be a bold paragraph rather than a real heading
                return doc.find_paragraphs(target["text"], headings) or doc.find_paragraphs(target["text"])
            if not headings:
                raise EditError("This document has no headings.")
            return headings
        if kind == "body":
            return [r for r in content if doc.role(r) == "body"]
        if kind == "document":
            return content
        if kind in ("paragraph", "text"):
            if target.get("index"):
                return self._pick(content, target["index"], "paragraph")
            if target.get("text"):
                return doc.find_paragraphs(target["text"])
        raise EditError(f"I can't use {describe_target(target)} as a text target.")

    @staticmethod
    def _pick(refs: List[ParaRef], index: int, word: str) -> List[ParaRef]:
        if index == -1 and refs:
            return [refs[-1]]
        if not 1 <= index <= len(refs):
            raise EditError(f"There is no {word} {index}; the document has {plural(len(refs), word)}.")
        return [refs[index - 1]]

    def resolve_one(self, cmd: Dict[str, Any], target: Dict[str, Any], verb: str) -> ParaRef:
        refs = self.resolve(target)
        if not refs:
            raise EditError(f"I couldn't find {describe_target(target)}. Quote a few words from it, or click it in the preview.")
        if len(refs) > 1:
            headings = [r for r in refs if self.doc.role(r) == "heading"]
            if len(headings) == 1 and target["type"] != "paragraph":
                return headings[0]
            options = []
            for ref in refs[:6]:
                option = copy.deepcopy(cmd)
                if verb == "insert":
                    option["position"]["anchor"] = {"type": "paragraph", "index": ref.pid}
                else:
                    option["target"] = {"type": "paragraph", "index": ref.pid}
                options.append({"label": f"¶{ref.pid}: {snippet(paragraph_text(ref.p))}", "command": option})
            raise ClarificationNeeded(f"{len(refs)} paragraphs match. Which one should I {verb}?", options)
        return refs[0]

    # ---------- style ----------
    def update_style(self, cmd: Dict[str, Any]) -> EditOutcome:
        target, changes = cmd["target"], cmd["changes"]
        touched: List[ET.Element] = []
        if target["type"] == "text" and target.get("text"):
            pattern = phrase_pattern(target["text"])
            for ref in self.doc.find_paragraphs(target["text"]):
                for match in reversed(list(pattern.finditer(paragraph_text(ref.p)))):
                    for run in isolate_runs(ref.p, match.start(), match.end()):
                        apply_run_changes(ensure_first(run, "rPr"), changes)
                touched.append(ref.p)
        else:
            for ref in self.resolve(target):
                self._style_paragraph(ref.p, changes)
                touched.append(ref.p)
        if not touched:
            raise EditError(f"I couldn't find {describe_target(target)}.")
        return EditOutcome(f"formatted {describe_target(target)}: {describe_changes(changes)}", paragraphs=touched)

    def _style_paragraph(self, p: ET.Element, changes: Dict[str, Any]) -> None:
        run_changes = {k: v for k, v in changes.items() if k != "align"}
        if run_changes:
            for run in p.iter(W + "r"):
                if run.find(W + "t") is not None:
                    apply_run_changes(ensure_first(run, "rPr"), run_changes)
            # Also format the paragraph mark, so text typed at the end in Word matches
            ppr = ensure_first(p, "pPr")
            mark = ppr.find(W + "rPr")
            if mark is None:
                mark = set_ordered(ppr, "rPr", PPR_ORDER)
            apply_run_changes(mark, run_changes)
        if "align" in changes:
            set_ordered(ensure_first(p, "pPr"), "jc", PPR_ORDER, {W + "val": JC_VALUES[changes["align"]]})

    # ---------- text ----------
    def update_text(self, cmd: Dict[str, Any]) -> EditOutcome:
        ref = self.resolve_one(cmd, cmd["target"], "change")
        old = paragraph_text(ref.p)
        if ref.p.find(f".//{W}t") is None:
            ET.SubElement(ET.SubElement(ref.p, W + "r"), W + "t").text = ""
        replace_range(ref.p, 0, len(old), cmd["text"])
        return EditOutcome(f"changed {describe_target(cmd['target'])} from “{snippet(old)}” to “{snippet(cmd['text'])}”",
                           paragraphs=[ref.p])

    def replace_text(self, cmd: Dict[str, Any], find: str, replacement: str) -> EditOutcome:
        refs = self.resolve(cmd["target"]) if cmd.get("target") else self.doc.content_paragraphs()
        pattern, count, touched = phrase_pattern(find), 0, []
        for ref in refs:
            text = paragraph_text(ref.p)
            matches = list(pattern.finditer(text))
            for match in reversed(matches):
                start, end = match.start(), match.end()
                if not replacement:  # deleting: also drop one neighbouring space
                    if end < len(text) and text[end] == " ":
                        end += 1
                    elif start > 0 and text[start - 1] == " ":
                        start -= 1
                replace_range(ref.p, start, end, replacement)
            if matches:
                count += len(matches)
                touched.append(ref.p)
        if not count:
            raise EditError(f"I couldn't find “{snippet(find)}” in the document.")
        where = f" ({plural(count, 'place')})" if count > 1 else ""
        if replacement:
            return EditOutcome(f"replaced “{snippet(find)}” with “{snippet(replacement)}”{where}", paragraphs=touched)
        return EditOutcome(f"deleted “{snippet(find)}”{where}", paragraphs=touched)

    def delete_paragraph(self, cmd: Dict[str, Any]) -> EditOutcome:
        ref = self.resolve_one(cmd, cmd["target"], "remove")
        if ref.p.find(f"{W}pPr/{W}sectPr") is not None:
            raise EditError("That paragraph holds a section break, so I left it in place to protect the layout.")
        text = paragraph_text(ref.p)
        parent = self.doc.parent_of(ref.p)
        if parent.tag == W + "tc" and len(parent.findall(W + "p")) == 1:
            for run in list(ref.p):  # a table cell must keep one paragraph, so empty it instead
                if run.tag != W + "pPr":
                    ref.p.remove(run)
        else:
            parent.remove(ref.p)
        return EditOutcome(f"removed paragraph {ref.pid} (“{snippet(text)}”)")

    def insert_text(self, cmd: Dict[str, Any]) -> EditOutcome:
        ref = self.resolve_one(cmd, cmd["target"], "add to")
        texts = list(ref.p.iter(W + "t"))
        if not texts:
            raise EditError("That paragraph has no text to add to.")
        at_start = cmd.get("position", {}).get("where") == "start"
        t = texts[0] if at_start else texts[-1]
        t.text = f"{cmd['text']} {t.text or ''}" if at_start else f"{(t.text or '').rstrip()} {cmd['text']}"
        preserve_space(t)
        return EditOutcome(f"added “{snippet(cmd['text'])}” to {describe_target(cmd['target'])}", paragraphs=[ref.p])

    def insert_paragraph(self, cmd: Dict[str, Any]) -> EditOutcome:
        position = cmd["position"]
        where, blocks = position["where"], self.doc.blocks()
        anchor_ref: Optional[ParaRef] = None
        if where in ("after", "before"):
            found = self.resolve_one(cmd, position["anchor"], "insert")
            anchor_ref = found
            anchor_index = blocks.index(found.block)
            if where == "before":
                insert_at = anchor_index
            else:
                insert_at = self._section_end(blocks, anchor_index) if self.doc.role(found) == "heading" else anchor_index + 1
        else:
            insert_at = 0 if where == "start" else len(blocks)
        # Body index = block index, because sectPr is always the last body child
        template = self._template_paragraph(blocks, insert_at)
        new_paragraphs = []
        for offset, line in enumerate(l for l in cmd["text"].split("\n") if l.strip()):
            p = self._new_paragraph(template, line.strip())
            self.doc.body.insert(insert_at + offset, p)
            new_paragraphs.append(p)
        if anchor_ref is None:
            where_text = "at the start" if where == "start" else "at the end"
        elif self.doc.role(anchor_ref) == "heading" and where == "after":
            where_text = f"at the end of the “{snippet(paragraph_text(anchor_ref.p), 40)}” section"
        else:
            where_text = f"{where} “{snippet(paragraph_text(anchor_ref.p), 40)}”"
        return EditOutcome(f"added a paragraph {where_text}: “{snippet(cmd['text'])}”", paragraphs=new_paragraphs)

    def _section_end(self, blocks: List[ET.Element], heading_index: int) -> int:
        level = self.doc.styles.outline_level(blocks[heading_index])
        for i in range(heading_index + 1, len(blocks)):
            other = self.doc.styles.outline_level(blocks[i]) if blocks[i].tag == W + "p" else None
            if other is not None and level is not None and other <= level:
                # Skip back over trailing empty paragraphs so the new text sits right after the content
                while i - 1 > heading_index and blocks[i - 1].tag == W + "p" and not paragraph_text(blocks[i - 1]).strip():
                    i -= 1
                return i
        return len(blocks)

    def _template_paragraph(self, blocks: List[ET.Element], index: int) -> Optional[ET.Element]:
        """The nearest plain body paragraph, so inserted text matches the surrounding formatting."""
        candidates = [b for b in blocks[:index][::-1] + blocks[index:] if b.tag == W + "p"]
        for block in candidates:
            ref = ParaRef(block, block, False, 0)
            if paragraph_text(block).strip() and self.doc.role(ref) == "body" and not paragraph_text(block).startswith("•"):
                return block
        return None

    @staticmethod
    def _new_paragraph(template: Optional[ET.Element], text: str) -> ET.Element:
        p = ET.Element(W + "p")
        ppr = template.find(W + "pPr") if template is not None else None
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        run = ET.SubElement(p, W + "r")
        first_run = template.find(f".//{W}r") if template is not None else None
        rpr = first_run.find(W + "rPr") if first_run is not None else None
        if rpr is not None:
            run.append(copy.deepcopy(rpr))
        t = ET.SubElement(run, W + "t")
        t.text = text
        preserve_space(t)
        return p
