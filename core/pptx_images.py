"""
Logo / picture operations for .pptx.

Scope rule: "the logo on slide 1" changes that slide only; "the logo" / "the presentation logo"
changes every slide's logo so the branding stays consistent.
"""
import copy
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from core.docx_images import inches
from core.edit_schema import ClarificationNeeded, EditError, EditOutcome
from core.ooxml_package import image_info
from core.pptx_model import A, P, PptxDocument, ShapeRef, picture_is_logo

MIN_PICTURE_EMU = 91440                 # 0.1 inch
EDGE_MARGIN_EMU = int(0.3 * 914400)     # distance from the slide edge for "move to the top right"


def resolve_pictures(doc: PptxDocument, cmd: Dict[str, Any]) -> List[ShapeRef]:
    target = cmd["target"]
    slide = target.get("slide")
    pictures = doc.pictures(slide)
    where = f"on slide {slide}" if slide else "in this presentation"
    if not pictures:
        raise EditError(f"There are no pictures {where}.")
    if target.get("shape_id"):
        chosen = [p for p in pictures if p.id == target["shape_id"]]
        if not chosen:
            raise EditError("The selected item is not a picture. Click the logo in the preview to select it.")
        return chosen
    if target.get("index"):
        index = len(pictures) if target["index"] == -1 else target["index"]
        if not 1 <= index <= len(pictures):
            raise EditError(f"There are {len(pictures)} pictures {where}, so there is no picture {index}.")
        return [pictures[index - 1]]
    logos = [p for p in pictures if picture_is_logo(p, doc.picture_media(p)[1])]
    if logos and (not slide or len(logos) == 1):
        return logos
    if len(pictures) == 1:
        return pictures
    media = {doc.picture_media(p)[1] for p in pictures}
    if not slide and len(media) == 1:
        return pictures  # the same image on every slide is the deck's logo
    options = []
    for picture in pictures[:6]:
        option = copy.deepcopy(cmd)
        option["target"] = {"type": "image", "slide": picture.slide, "shape_id": picture.id}
        options.append({"label": f"Slide {picture.slide}: {picture.name or 'picture'} "
                                 f"({inches(picture.cx)} × {inches(picture.cy)} in)", "command": option})
    raise ClarificationNeeded("I found several pictures and can't tell which one is the logo. Which one? "
                              "(You can also click it in the preview.)", options)


def _xfrm(shape: ShapeRef) -> Tuple[ET.Element, ET.Element]:
    """Returns (a:off, a:ext), creating an explicit transform when the picture inherits one."""
    sp_pr = shape.el.find(P + "spPr")
    if sp_pr is None:
        sp_pr = ET.SubElement(shape.el, P + "spPr")
    xfrm = sp_pr.find(A + "xfrm")
    if xfrm is None:
        xfrm = ET.Element(A + "xfrm")
        sp_pr.insert(0, xfrm)
    off, ext = xfrm.find(A + "off"), xfrm.find(A + "ext")
    if off is None:
        off = ET.SubElement(xfrm, A + "off", {"x": str(shape.x), "y": str(shape.y)})
    if ext is None:
        ext = ET.SubElement(xfrm, A + "ext", {"cx": str(shape.cx), "cy": str(shape.cy)})
    return off, ext


def _place(shape: ShapeRef, x: int, y: int, cx: int, cy: int) -> None:
    off, ext = _xfrm(shape)
    off.set("x", str(x))
    off.set("y", str(y))
    ext.set("cx", str(cx))
    ext.set("cy", str(cy))
    shape.x, shape.y, shape.cx, shape.cy = x, y, cx, cy


def resize(doc: PptxDocument, shape: ShapeRef, scale: float) -> None:
    width, height = doc.slide_size()
    cx, cy = round(shape.cx * scale), round(shape.cy * scale)
    if cx > width or cy > height:
        factor = min(width / cx, height / cy)
        cx, cy = round(cx * factor), round(cy * factor)
    if min(cx, cy) < MIN_PICTURE_EMU:
        raise EditError("That would make the picture too small to see, so I left it unchanged.")
    # Keep the corner nearest the slide edge fixed, so a top-right logo stays in the top-right
    x = shape.x + shape.cx - cx if shape.x + shape.cx / 2 > width / 2 else shape.x
    y = shape.y + shape.cy - cy if shape.y + shape.cy / 2 > height / 2 else shape.y
    _place(shape, max(0, min(x, width - cx)), max(0, min(y, height - cy)), cx, cy)


def move(doc: PptxDocument, shape: ShapeRef, spec: Dict[str, Any]) -> None:
    width, height = doc.slide_size()
    if "to" in spec:
        spot = spec["to"]
        x = {"left": EDGE_MARGIN_EMU, "right": width - shape.cx - EDGE_MARGIN_EMU}
        y = {"top": EDGE_MARGIN_EMU, "bottom": height - shape.cy - EDGE_MARGIN_EMU}
        new_x = next((x[k] for k in x if k in spot), (width - shape.cx) // 2 if spot == "center" else shape.x)
        new_y = next((y[k] for k in y if k in spot), (height - shape.cy) // 2 if spot == "center" else shape.y)
    else:
        new_x = shape.x + round(spec["dx_inches"] * 914400)
        new_y = shape.y + round(spec["dy_inches"] * 914400)
    _place(shape, max(0, min(new_x, width - shape.cx)), max(0, min(new_y, height - shape.cy)), shape.cx, shape.cy)


def replace(doc: PptxDocument, shapes: List[ShapeRef], data: bytes) -> None:
    try:
        _, width_px, height_px = image_info(data)
    except ValueError as e:
        raise EditError(str(e)) from e
    new_part = doc.pkg.add_media("ppt/media", data)
    done = set()
    for shape in shapes:
        rel_id, _ = doc.picture_media(shape)
        if rel_id and (shape.part, rel_id) not in done:
            # A new media part keeps other slides that share the old picture unchanged
            doc.pkg.set_rel_target(shape.part, rel_id, new_part)
            done.add((shape.part, rel_id))
        if width_px and height_px:
            _place(shape, shape.x, shape.y, shape.cx, round(shape.cx * height_px / width_px))


def apply_image_command(doc: PptxDocument, cmd: Dict[str, Any], image_bytes: Optional[bytes]) -> EditOutcome:
    action = cmd["action"]
    if action == "replace_image" and image_bytes is None:
        raise EditError("Upload the new logo first (use the 📎 button), then ask me to replace it.")
    shapes = resolve_pictures(doc, cmd)
    slides = sorted({s.slide for s in shapes})
    where = f"on slide {slides[0]}" if len(slides) == 1 else f"on all {len(slides)} slides"
    label = "the logo" if any(picture_is_logo(s, doc.picture_media(s)[1]) for s in shapes) else "the picture"
    before = f"{inches(shapes[0].cx)} × {inches(shapes[0].cy)} in"
    if action == "resize_image":
        for shape in shapes:
            resize(doc, shape, cmd["scale"])
        after = f"{inches(shapes[0].cx)} × {inches(shapes[0].cy)} in"
        summary = f"resized {label} {where} to {round(cmd['scale'] * 100)}% — {before} → {after}"
    elif action == "move_image":
        for shape in shapes:
            move(doc, shape, cmd["move"])
        summary = f"moved {label} {where}"
    else:
        replace(doc, shapes, image_bytes or b"")
        summary = f"replaced {label} {where} with the uploaded image"
    return EditOutcome(summary, slides=slides, shapes=[f"{s.slide}:{s.id}" for s in shapes])
