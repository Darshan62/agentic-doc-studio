"""Finding, resizing and replacing pictures (e.g. the company logo) in a .docx."""
import copy
import posixpath
from typing import Any, Dict, List

from core.docx_model import A, W, WP, DocxDocument, ImageRef
from core.edit_schema import ClarificationNeeded, EditError
from core.ooxml_package import image_info

EMU_PER_INCH = 914400
EMU_PER_TWIP = 635
MIN_IMAGE_EMU = 91440          # 0.1 inch: smaller than this is invisible in practice
DEFAULT_TEXT_WIDTH_EMU = 5943600  # 6.5 inches (Letter with 1 inch margins)


def inches(emu: int) -> str:
    return f"{emu / EMU_PER_INCH:.2f}".rstrip("0").rstrip(".")


def image_label(image: ImageRef) -> str:
    return "the logo" if "logo" in image.name.lower() else f"image {image.index}"


def is_logo(image: ImageRef) -> bool:
    return "logo" in f"{image.name} {image.media_part or ''}".lower()


def resolve_image(doc: DocxDocument, cmd: Dict[str, Any]) -> ImageRef:
    target, images = cmd["target"], doc.images()
    if not images:
        raise EditError("This document has no images, so there is no logo to change.")
    index = target.get("index")
    if index:
        if index == -1:
            return images[-1]
        if not 1 <= index <= len(images):
            raise EditError(f"There is no image {index}; the document has {len(images)}.")
        return images[index - 1]
    if target.get("text"):
        named = [i for i in images if target["text"].lower() in i.name.lower()]
        if len(named) == 1:
            return named[0]
    logos = [i for i in images if is_logo(i)]
    if len(logos) == 1:
        return logos[0]
    if len(images) == 1:
        return images[0]
    headers = [i for i in images if i.location == "header"]
    if target["type"] == "logo" and len(headers) == 1:
        return headers[0]
    options: List[Dict[str, Any]] = []
    for image in (logos or images)[:6]:
        option = copy.deepcopy(cmd)
        option["target"] = {"type": "image", "index": image.index}
        label = f"Image {image.index} ({image.location}, {inches(image.cx)} × {inches(image.cy)} in)"
        options.append({"label": label + (f" — {image.name}" if image.name else ""), "command": option})
    raise ClarificationNeeded("I found several images and can't tell which is the logo. Which one? "
                              "(You can also click it in the preview.)", options)


def _set_size(image: ImageRef, cx: int, cy: int) -> None:
    for extent in image.drawing.iter(WP + "extent"):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
    for xfrm in image.drawing.iter(A + "xfrm"):
        ext = xfrm.find(A + "ext")
        if ext is not None:
            ext.set("cx", str(cx))
            ext.set("cy", str(cy))
    image.cx, image.cy = cx, cy


def text_width(doc: DocxDocument) -> int:
    sect = doc.body.find(W + "sectPr")
    size = sect.find(W + "pgSz") if sect is not None else None
    margins = sect.find(W + "pgMar") if sect is not None else None
    try:
        width = int(size.get(W + "w", "0")) if size is not None else 0
        left = int(margins.get(W + "left", "0")) if margins is not None else 0
        right = int(margins.get(W + "right", "0")) if margins is not None else 0
    except ValueError:
        return DEFAULT_TEXT_WIDTH_EMU
    return (width - left - right) * EMU_PER_TWIP if width > left + right else DEFAULT_TEXT_WIDTH_EMU


def resize_image(doc: DocxDocument, image: ImageRef, scale: float) -> str:
    cx, cy = round(image.cx * scale), round(image.cy * scale)
    note = ""
    limit = text_width(doc)
    if cx > limit:
        cy, cx = round(cy * limit / cx), limit
        note = " (capped at the page width)"
    if min(cx, cy) < MIN_IMAGE_EMU:
        raise EditError("That would make the image too small to see, so I left it unchanged.")
    old = f"{inches(image.cx)} × {inches(image.cy)} in"
    _set_size(image, cx, cy)
    return f"resized {image_label(image)} to {round(scale * 100)}% — {old} → {inches(cx)} × {inches(cy)} in{note}"


def replace_image(doc: DocxDocument, image: ImageRef, data: bytes) -> str:
    try:
        _, width_px, height_px = image_info(data)
    except ValueError as e:
        raise EditError(str(e)) from e
    folder = posixpath.dirname(image.media_part) if image.media_part else "word/media"
    new_part = doc.pkg.add_media(folder, data)
    doc.pkg.set_rel_target(image.part, image.rel_id, new_part)
    # Keep the displayed width but follow the new picture's proportions, so it is never stretched
    if width_px and height_px:
        _set_size(image, image.cx, round(image.cx * height_px / width_px))
    return f"replaced {image_label(image)} with the uploaded image"
