"""
Structured edit commands.

The language model (or the rule parser) only ever produces a JSON command. Nothing it returns
is executed: `validate_command` whitelists the action, the target and every parameter, and the
deterministic editors in core/docx_editor.py and core/pptx_editor.py apply the result.

Command shape (all keys except `action` are optional; each action requires its own subset):
{
  "document_type": "docx" | "pptx",
  "action": "update_style",
  "target": {"type": "title", "text": null, "index": null, "slide": 1, "shape_id": null},
  "changes": {"font_family": "Arial", "font_size": 24, "bold": true, "italic": null,
              "underline": null, "color": "0070C0", "align": null},
  "text": "...",                       # new text (update_text / insert_* / add_text)
  "target_text": "...",                # text to find (replace_text / delete_text)
  "replacement_text": "...",           # replace_text
  "position": {"where": "after", "anchor": {<target>}},   # insert_paragraph / insert_text / add_text
  "scale": 0.8,                        # resize_image (relative to the current size)
  "move": {"dx_inches": 0.3, "dy_inches": 0, "to": null}, # move_image
  "image_source": "last_upload"        # replace_image
}
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DOCX_ACTIONS = {"update_style", "update_text", "replace_text", "delete_text", "delete_paragraph",
                "insert_text", "insert_paragraph", "replace_image", "resize_image"}
PPTX_ACTIONS = {"update_style", "update_text", "replace_text", "delete_text", "add_text",
                "delete_slide", "replace_image", "resize_image", "move_image"}
ACTIONS = {"docx": DOCX_ACTIONS, "pptx": PPTX_ACTIONS}

TARGET_TYPES = {"title", "subtitle", "heading", "headings", "body", "document", "paragraph", "text",
                "image", "logo", "bullet", "slide", "shape", "selection"}
IMAGE_TARGETS = {"image", "logo", "selection", "shape"}
POSITIONS = {"after", "before", "start", "end"}
MOVE_TO = {"top-left", "top-right", "bottom-left", "bottom-right", "center", "top", "bottom", "left", "right"}
ALIGNMENTS = {"left", "center", "right", "justify"}

MAX_TEXT = 5000
MAX_FIND = 1000
MIN_FONT_PT, MAX_FONT_PT = 1, 400
MIN_SCALE, MAX_SCALE = 0.05, 10.0
MAX_MOVE_INCHES = 20.0
MAX_INDEX = 100000

# Office's standard palette, so "blue" means the same blue Word/PowerPoint would offer
NAMED_COLORS = {
    "black": "000000", "white": "FFFFFF", "red": "C00000", "dark red": "8B0000", "orange": "ED7D31",
    "yellow": "FFC000", "gold": "BF9000", "green": "00B050", "dark green": "006400", "teal": "008080",
    "blue": "0070C0", "light blue": "00B0F0", "dark blue": "002060", "navy": "1F3864", "purple": "7030A0",
    "violet": "7030A0", "pink": "FF66CC", "magenta": "FF00FF", "brown": "843C0C", "grey": "7F7F7F",
    "gray": "7F7F7F", "dark gray": "404040", "dark grey": "404040", "light gray": "BFBFBF",
    "light grey": "BFBFBF", "cyan": "00B0F0", "maroon": "800000", "olive": "808000", "silver": "C0C0C0",
}
_FONT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,63}$")
_HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")


class EditError(Exception):
    """A user-facing reason why an edit could not be applied. The document is left unchanged."""


class ClarificationNeeded(Exception):
    """The request is ambiguous. `options` (if any) are fully resolved commands the user can pick."""

    def __init__(self, question: str, options: Optional[List[Dict[str, Any]]] = None):
        super().__init__(question)
        self.question = question
        self.options = options or []
        self.command_index = 0  # which command of a multi-command request was ambiguous


@dataclass
class EditOutcome:
    """What an applied command changed: a summary for the chat plus refs for the preview highlight."""
    summary: str
    paragraphs: List[ET.Element] = field(default_factory=list)
    images: List[int] = field(default_factory=list)
    slides: List[int] = field(default_factory=list)
    shapes: List[str] = field(default_factory=list)


def normalize_color(value: Any) -> str:
    text = str(value).strip().lower()
    if text in NAMED_COLORS:
        return NAMED_COLORS[text]
    match = _HEX.match(text)
    if match:
        return match.group(1).upper()
    raise EditError(f"I don't recognise the colour '{value}'. Use a name like blue or a hex code like #1F4E79.")


def _text(value: Any, field: str, max_len: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise EditError(f"The command is missing '{field}'.")
    if not value.strip() and not allow_empty:
        raise EditError(f"The command has an empty '{field}'.")
    if len(value) > max_len:
        raise EditError(f"'{field}' is too long (max {max_len} characters).")
    return value


def _int(value: Any, field: str, minimum: int = 1) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise EditError(f"'{field}' must be a whole number.")
    if not minimum <= int(value) <= MAX_INDEX:
        raise EditError(f"'{field}' is out of range.")
    return int(value)


def _optional_bool(value: Any, field: str) -> Optional[bool]:
    if value is None or isinstance(value, bool):
        return value
    raise EditError(f"'{field}' must be true or false.")


def validate_target(raw: Any, field: str = "target") -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise EditError(f"The command is missing a {field}.")
    target_type = raw.get("type")
    if target_type not in TARGET_TYPES:
        raise EditError(f"Unknown {field} type '{target_type}'.")
    target: Dict[str, Any] = {"type": target_type}
    if raw.get("text") is not None:
        target["text"] = _text(raw["text"], f"{field}.text", MAX_FIND)
    index = raw.get("index")
    if index == -1:
        target["index"] = -1  # -1 means "the last one"
    elif index is not None:
        target["index"] = _int(index, f"{field}.index")
    if raw.get("slide") is not None:
        target["slide"] = _int(raw["slide"], f"{field}.slide")
    if raw.get("shape_id") is not None:
        shape_id = str(raw["shape_id"])
        if not shape_id.isdigit():
            raise EditError(f"'{field}.shape_id' must be a number.")
        target["shape_id"] = shape_id
    return target


def validate_changes(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise EditError("The style command has no changes.")
    changes: Dict[str, Any] = {}
    if raw.get("font_family") is not None:
        font = str(raw["font_family"]).strip()
        if not _FONT_NAME.match(font):
            raise EditError(f"'{font}' is not a valid font name.")
        changes["font_family"] = font
    if raw.get("font_size") is not None:
        size = raw["font_size"]
        if isinstance(size, bool) or not isinstance(size, (int, float)) or not MIN_FONT_PT <= size <= MAX_FONT_PT:
            raise EditError(f"Font size must be between {MIN_FONT_PT} and {MAX_FONT_PT} points.")
        changes["font_size"] = round(float(size) * 2) / 2  # Word stores half-points
    for key in ("bold", "italic", "underline"):
        value = _optional_bool(raw.get(key), key)
        if value is not None:
            changes[key] = value
    if raw.get("color") is not None:
        changes["color"] = normalize_color(raw["color"])
    if raw.get("align") is not None:
        align = str(raw["align"]).lower().replace("centre", "center")
        if align not in ALIGNMENTS:
            raise EditError(f"Alignment must be one of: {', '.join(sorted(ALIGNMENTS))}.")
        changes["align"] = align
    if not changes:
        raise EditError("The style command has no changes.")
    return changes


def validate_position(raw: Any, required: bool) -> Optional[Dict[str, Any]]:
    if raw is None:
        if required:
            raise EditError("The command needs a position (for example: after the executive summary).")
        return None
    if not isinstance(raw, dict) or raw.get("where") not in POSITIONS:
        raise EditError("Position must say where: after, before, start or end.")
    position: Dict[str, Any] = {"where": raw["where"]}
    if raw.get("anchor") is not None:
        position["anchor"] = validate_target(raw["anchor"], "anchor")
    elif raw["where"] in ("after", "before"):
        raise EditError(f"Insert {raw['where']} what? The command has no anchor.")
    return position


def validate_command(raw: Any, doc_type: str) -> Dict[str, Any]:
    """Returns a clean copy of the command with only known keys, or raises EditError."""
    if doc_type not in ACTIONS:
        raise EditError(f"Unsupported document type '{doc_type}'.")
    if not isinstance(raw, dict):
        raise EditError("The edit command must be a JSON object.")
    declared = raw.get("document_type")
    if declared is not None and declared != doc_type:
        raise EditError(f"That command is for a {declared} file, but the open file is a {doc_type}.")
    action = raw.get("action")
    if action not in ACTIONS[doc_type]:
        raise EditError(f"'{action}' is not available for {doc_type.upper()} files.")

    cmd: Dict[str, Any] = {"document_type": doc_type, "action": action}
    if raw.get("target") is not None:
        cmd["target"] = validate_target(raw["target"])

    if action == "update_style":
        cmd["changes"] = validate_changes(raw.get("changes"))
    elif action == "update_text":
        cmd["text"] = _text(raw.get("text"), "text", MAX_TEXT)
    elif action == "replace_text":
        cmd["target_text"] = _text(raw.get("target_text"), "target_text", MAX_FIND)
        cmd["replacement_text"] = _text(raw.get("replacement_text"), "replacement_text", MAX_TEXT, allow_empty=True)
    elif action == "delete_text":
        if raw.get("target_text") is not None:
            cmd["target_text"] = _text(raw["target_text"], "target_text", MAX_FIND)
    elif action in ("insert_text", "insert_paragraph", "add_text"):
        cmd["text"] = _text(raw.get("text"), "text", MAX_TEXT)
        position = validate_position(raw.get("position"), required=action == "insert_paragraph")
        if position:
            cmd["position"] = position
    elif action == "resize_image":
        scale = raw.get("scale")
        if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not MIN_SCALE <= scale <= MAX_SCALE:
            raise EditError(f"Resize scale must be between {int(MIN_SCALE * 100)}% and {int(MAX_SCALE * 100)}%.")
        cmd["scale"] = float(scale)
    elif action == "move_image":
        cmd["move"] = _validate_move(raw.get("move"))
    elif action == "replace_image":
        if raw.get("image_source", "last_upload") != "last_upload":
            raise EditError("Images can only be replaced with an image you uploaded in this chat.")
        cmd["image_source"] = "last_upload"

    _check_target_requirements(cmd)
    return cmd


def _validate_move(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise EditError("The move command needs a direction or a position.")
    if raw.get("to") is not None:
        if raw["to"] not in MOVE_TO:
            raise EditError(f"Move position must be one of: {', '.join(sorted(MOVE_TO))}.")
        return {"to": raw["to"]}
    move = {}
    for key in ("dx_inches", "dy_inches"):
        value = raw.get(key) or 0
        if isinstance(value, bool) or not isinstance(value, (int, float)) or abs(value) > MAX_MOVE_INCHES:
            raise EditError("Move distance is out of range.")
        move[key] = float(value)
    if not move["dx_inches"] and not move["dy_inches"]:
        raise EditError("The move command has no direction.")
    return move


def _check_target_requirements(cmd: Dict[str, Any]) -> None:
    action, target = cmd["action"], cmd.get("target")
    needs_target = {"update_style", "update_text", "delete_paragraph", "insert_text",
                    "replace_image", "resize_image", "move_image", "delete_slide"}
    if target is None:
        if action in needs_target:
            raise EditError("The command does not say what to change.")
        if action == "delete_text" and "target_text" not in cmd:
            raise EditError("The command does not say what to delete.")
        if action == "add_text" and "position" not in cmd:
            raise EditError("Which slide should I add the text to?")
        return
    if action in ("replace_image", "resize_image", "move_image") and target["type"] not in IMAGE_TARGETS:
        raise EditError("Image commands must target an image or the logo.")
    if action == "delete_slide" and not target.get("slide") and target["type"] != "selection":
        raise EditError("Which slide should I delete?")
