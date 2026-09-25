"""Plain-English descriptions of targets and style changes, used in chat replies and version notes."""
from typing import Any, Dict, List

from core.edit_schema import NAMED_COLORS

SNIPPET_CHARS = 60
_COLOR_NAMES = {}
for _name, _hex in NAMED_COLORS.items():
    _COLOR_NAMES.setdefault(_hex, _name)


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def describe_target(target: Dict[str, Any]) -> str:
    kind = target.get("type")
    text, index, slide = target.get("text"), target.get("index"), target.get("slide")
    on_slide = f" on slide {slide}" if slide else ""
    if kind == "title":
        return f"the title{on_slide}"
    if kind == "subtitle":
        return f"the subtitle{on_slide}"
    if kind in ("heading", "headings"):
        if text:
            return f"the “{snippet(text)}” heading"
        return f"heading {index}" if index else "all headings"
    if kind == "body":
        return f"the body text{on_slide}"
    if kind == "document":
        return "all text in the document"
    if kind == "paragraph":
        if index:
            return "the last paragraph" if index == -1 else f"paragraph {index}"
        return f"the paragraph about “{snippet(text or '')}”"
    if kind == "text":
        return f"“{snippet(text or '')}”"
    if kind == "bullet":
        which = "the last bullet" if index == -1 else f"bullet {index}"
        return f"{which}{on_slide}"
    if kind == "slide":
        return f"all text on slide {slide}" if slide else "the slide"
    if kind == "shape":
        return f"the selected box{on_slide}"
    if kind == "logo":
        return f"the logo{on_slide}"
    if kind == "image":
        return f"image {index}{on_slide}" if index else f"the image{on_slide}"
    return "the selection"


def color_label(hex_value: str) -> str:
    name = _COLOR_NAMES.get(hex_value.upper())
    return f"{name} (#{hex_value})" if name else f"#{hex_value}"


def describe_changes(changes: Dict[str, Any]) -> str:
    parts: List[str] = []
    if "font_family" in changes:
        parts.append(f"font {changes['font_family']}")
    if "font_size" in changes:
        size = changes["font_size"]
        parts.append(f"{int(size) if size == int(size) else size} pt")
    if "color" in changes:
        parts.append(f"colour {color_label(changes['color'])}")
    for key, on_word, off_word in (("bold", "bold", "not bold"), ("italic", "italic", "not italic"),
                                   ("underline", "underlined", "no underline")):
        if key in changes:
            parts.append(on_word if changes[key] else off_word)
    if "align" in changes:
        parts.append(f"aligned {changes['align']}")
    return ", ".join(parts)


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")
