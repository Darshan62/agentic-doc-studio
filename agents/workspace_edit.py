"""
Applies parsed commands to the workspace file safely:
resolve "this/selected" -> validate -> apply all commands in memory -> re-read the result to
prove it is still a valid document -> atomically replace the working file.
If any step fails, the file on disk is untouched.
"""
import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.docx_editor import DocxEditor
from core.docx_model import DocxDocument
from core.docx_preview import docx_outline, docx_preview
from core.edit_schema import ClarificationNeeded, EditError, EditOutcome, validate_command
from core.ooxml_package import OoxmlPackage
from core.pptx_editor import PptxEditor
from core.pptx_preview import pptx_outline, pptx_preview

SLIDE_SCOPED_TARGETS = {"title", "subtitle", "body", "bullet", "shape"}


def build_preview(data: bytes, doc_type: str, changed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pkg = OoxmlPackage(data)
    changed = changed or {}
    if doc_type == "docx":
        marks: Set[int] = set(changed.get("paragraphs", [])) | {-i for i in changed.get("images", [])}
        return docx_preview(pkg, marks)
    return pptx_preview(pkg, set(changed.get("shapes", [])), set(changed.get("slides", [])))


def outline(data: bytes, doc_type: str) -> str:
    pkg = OoxmlPackage(data)
    return docx_outline(pkg) if doc_type == "docx" else pptx_outline(pkg)


def validate_selection(selection: Any) -> Optional[Dict[str, Any]]:
    """The selection comes from the browser, so only whitelisted, typed fields survive."""
    if not isinstance(selection, dict) or selection.get("kind") not in ("paragraph", "image", "shape"):
        return None
    clean: Dict[str, Any] = {"kind": selection["kind"]}
    for key in ("pid", "index", "slide"):
        value = selection.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 < value < 100000:
            clean[key] = value
    shape_id = selection.get("shape_id")
    if isinstance(shape_id, str) and shape_id.isdigit():
        clean["shape_id"] = shape_id
    return clean


def selection_target(selection: Optional[Dict[str, Any]], doc_type: str) -> Dict[str, Any]:
    if not selection:
        raise EditError("Nothing is selected. Click a paragraph, text box or the logo in the preview first.")
    kind = selection["kind"]
    if doc_type == "docx" and kind == "paragraph" and "pid" in selection:
        return {"type": "paragraph", "index": selection["pid"]}
    if doc_type == "docx" and kind == "image" and "index" in selection:
        return {"type": "image", "index": selection["index"]}
    if doc_type == "pptx" and "slide" in selection and "shape_id" in selection:
        return {"type": "image" if kind == "image" else "shape", "slide": selection["slide"], "shape_id": selection["shape_id"]}
    raise EditError("The current selection can't be used for that. Click the item in the preview again.")


def resolve_command(raw: Dict[str, Any], doc_type: str, selection: Optional[Dict[str, Any]],
                    current_slide: int) -> Dict[str, Any]:
    cmd = copy.deepcopy(raw)
    for holder in (cmd, cmd.get("position") or {}):
        key = "target" if holder is cmd else "anchor"
        target = holder.get(key)
        if isinstance(target, dict) and target.get("type") == "selection":
            holder[key] = selection_target(selection, doc_type)
    target = cmd.get("target")
    if doc_type == "pptx" and isinstance(target, dict) and not target.get("slide"):
        needs_slide = target.get("type") in SLIDE_SCOPED_TARGETS or (target.get("type") == "paragraph" and target.get("index"))
        if needs_slide or (cmd.get("action") == "add_text" and target.get("type") == "slide"):
            target["slide"] = current_slide
    if doc_type == "pptx" and cmd.get("action") == "add_text" and not target:
        cmd["target"] = {"type": "slide", "slide": current_slide}
    return validate_command(cmd, doc_type)


def changed_refs(pkg: OoxmlPackage, doc_type: str, outcomes: List[EditOutcome]) -> Dict[str, Any]:
    if doc_type == "docx":
        touched = {id(p) for o in outcomes for p in o.paragraphs}
        pids = [ref.pid for ref in DocxDocument(pkg).paragraphs() if id(ref.p) in touched and ref.pid]
        return {"paragraphs": pids, "images": sorted({i for o in outcomes for i in o.images})}
    return {"slides": sorted({s for o in outcomes for s in o.slides}),
            "shapes": sorted({s for o in outcomes for s in o.shapes})}


def apply_commands(path: Path, doc_type: str, commands: List[Dict[str, Any]], selection: Optional[Dict[str, Any]],
                   current_slide: int, image_bytes: Optional[bytes]) -> Tuple[List[Dict[str, Any]], List[EditOutcome], Dict[str, Any], Dict[str, Any]]:
    """Returns (validated commands, outcomes, changed refs, preview of the saved file)."""
    pkg = OoxmlPackage(path.read_bytes())
    editor = DocxEditor(pkg) if doc_type == "docx" else PptxEditor(pkg, current_slide)
    validated, outcomes = [], []
    for index, raw in enumerate(commands):
        cmd = resolve_command(raw, doc_type, selection, current_slide)
        try:
            outcomes.append(editor.apply(cmd, image_bytes))
        except ClarificationNeeded as e:
            e.command_index = index  # lets each answer option rebuild the full command list
            raise
        validated.append(cmd)
    changed = changed_refs(pkg, doc_type, outcomes)
    data = pkg.to_bytes()
    preview = build_preview(data, doc_type, changed)  # re-reads the new file: proves it is still valid
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return validated, outcomes, changed, preview
