"""
Deterministic natural-language -> edit command parser.

Used when Gemini is not configured or fails, and as a guaranteed baseline for the common
requests (fonts, sizes, colours, deleting/adding paragraphs and bullets, logo operations).
It never guesses: anything it cannot pin down becomes a clarification question.
"""
import re
from typing import Any, Dict, List, Optional

from agents.edit_rule_clause import (ABOUT_RE, CLAUSE_SPLIT, PAYLOAD_VERBS, QUOTE_RE, Clarify, Clause, ParseContext,
                                     ParseResult, unquote, which_text_question)
from agents.edit_rules_vocab import (find_align, find_color, find_font, find_move, find_scale, find_size,
                                     find_toggle, ordinal_before)
from core.edit_describe import describe_target

__all__ = ["ParseContext", "ParseResult", "parse_rules"]

HELP = ("I'm not sure what to change. Try for example “Change the title font to Arial”, "
        "“Remove the paragraph about pricing” or “Resize the logo to 80%”.")


def parse_rules(message: str, ctx: ParseContext) -> ParseResult:
    text = message.strip()
    payload = None
    split = re.match(r"^(?P<head>[^:]{3,240}?)\s*:\s*(?P<body>.+)$", text, re.S)
    if split and PAYLOAD_VERBS.search(split.group("head")):
        text, payload = split.group("head"), unquote(split.group("body"), keep_period=True)
    quotes: List[str] = []

    def mask(match: re.Match) -> str:
        quotes.append(next(g for g in match.groups() if g))
        return f"⟦{len(quotes) - 1}⟧"

    masked = QUOTE_RE.sub(mask, text)
    pieces = [p for p in CLAUSE_SPLIT.split(masked) if p and p.strip(" .")]
    commands: List[Dict[str, Any]] = []
    prev_target = ctx.last_target
    try:
        for index, piece in enumerate(pieces):
            clause = Clause(piece, quotes, payload if index == len(pieces) - 1 else None, ctx, prev_target)
            command = parse_clause(clause)
            if command:
                commands.append(command)
                prev_target = command.get("target") or prev_target
    except Clarify as c:
        return ParseResult([], clarification=c.question)
    if not commands:
        return ParseResult([], clarification=HELP)
    return ParseResult(merge_styles(commands))


def merge_styles(commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for cmd in commands:
        last = merged[-1] if merged else None
        if last and cmd["action"] == last["action"] == "update_style" and cmd["target"] == last["target"]:
            last["changes"].update(cmd["changes"])
        else:
            merged.append(cmd)
    return merged


def parse_clause(c: Clause) -> Optional[Dict[str, Any]]:
    removal = c.has(r"\b(remove|delete|drop|erase|get rid of|take out|cut)\b")
    if c.has(r"\b(logo|image|picture|photo|graphic)\b") or (c.has(r"\b(it|its)\b") and (c.prev_target or {}).get("type") in ("logo", "image")):
        return image_command(c, removal)
    if removal and c.pptx and c.has(r"\bslide\b") and not c.has(r"\b(bullet|text|title|line|paragraph|point|word|sentence)\b"):
        number = c.slide or (c.ctx.current_slide if c.has(r"\b(this|current)\s+slide\b") else None)
        if not number:
            raise Clarify("Which slide should I delete? For example “Delete slide 5”.")
        return {"action": "delete_slide", "target": {"type": "slide", "slide": number}}
    if c.has(r"\b(replace|swap|substitute)\b") or (c.has(r"\bchange\b") and len(c.quotes) >= 2):
        return replace_command(c)
    if removal:
        return removal_command(c)
    if c.has(r"\b(add|insert|append|include|write)\b"):
        return add_command(c)
    return text_update_command(c) or style_command(c)


def image_command(c: Clause, removal: bool) -> Dict[str, Any]:
    if c.ctx.selection_kind == "image" and c.has(r"\b(this|selected)\b"):
        target: Dict[str, Any] = {"type": "selection"}
    else:
        index = ordinal_before(c.low, r"(?:image|picture)")
        target = c.with_slide({"type": "image", "index": index} if index else {"type": "logo" if c.has(r"\blogo\b") else "image"})
    if c.has(r"\b(move|shift|nudge|push|drag|reposition)\b"):
        if not c.pptx:
            raise Clarify("Moving pictures isn't supported in Word documents yet. I can resize or replace the logo instead.")
        move = find_move(c.low)
        if move is None:
            raise Clarify("Which way should I move it? For example “slightly to the right” or “to the top-left corner”.")
        return {"action": "move_image", "target": target, "move": move}
    if c.has(r"\b(resize|scale|size|smaller|bigger|larger|shrink|enlarge|reduce|increase|decrease|half|double|twice)\b|%|\bpercent\b"):
        scale = find_scale(c.low)
        if scale is None:
            raise Clarify("How much should I resize it? For example “80%”, “50% smaller” or “make it bigger”.")
        return {"action": "resize_image", "target": target, "scale": scale}
    what = "the logo" if target.get("type") == "logo" else "a picture"
    abilities = "replace it with an image you upload (📎), resize it" + (" or move it." if c.pptx else ".")
    if removal:
        raise Clarify(f"Removing pictures isn't supported yet. For {what} that's already in the file I can {abilities}")
    adding = c.has(r"\b(add|put|insert|place|include|generate|find|background)\b")
    if adding and not c.has(r"\b(replace|swap|substitute)\b"):
        raise Clarify("Adding new pictures or backgrounds isn't supported yet. I can only change pictures that are "
                      f"already in the file: {abilities}")
    if c.has(r"\b(replace|change|swap|update|use|new|different|switch)\b"):
        return {"action": "replace_image", "target": target, "image_source": "last_upload"}
    raise Clarify(f"What should I do with {what}? I can {abilities}")


def replace_command(c: Clause) -> Dict[str, Any]:
    scope = {"target": {"type": "slide", "slide": c.slide}} if c.pptx and c.slide else {}
    if len(c.quotes) >= 2:
        return {"action": "replace_text", "target_text": c.quotes[0], "replacement_text": c.quotes[1], **scope}
    if c.payload and c.ctx.selection_kind and c.has(r"\b(this|selected)\b"):
        return {"action": "update_text", "target": {"type": "selection"}, "text": c.payload}
    match = re.search(r"\breplace\s+(?:the\s+)?(?:words?|text|phrase|sentence)?\s*(.+?)\s+with\s*(.*)$", c.raw, re.I)
    if match and re.fullmatch(r"(this|that|the selected)\s*(sentence|paragraph|text|line|bullet)?|it", match.group(1).strip().lower()):
        raise Clarify("Click the sentence or paragraph in the preview first, then ask me again to replace it.")
    if match and (match.group(2).strip() or c.payload):
        replacement = unquote(match.group(2)) if match.group(2).strip() else c.payload or ""
        return {"action": "replace_text", "target_text": unquote(match.group(1)), "replacement_text": replacement, **scope}
    if c.has(r"\b(this|selected)\b"):
        raise Clarify("What should I replace it with? Select the text in the preview, then write for example "
                      "“Replace this sentence with: …”.")
    raise Clarify("What should I replace, and with what? For example “Replace 'old text' with 'new text'”.")


def removal_command(c: Clause) -> Dict[str, Any]:
    about = ABOUT_RE.search(c.raw)
    if c.quotes and not about and not c.has(r"⟦\d+⟧\s+(heading|section|paragraph)"):
        return {"action": "delete_text", "target_text": c.quotes[0]}
    words = re.search(r"\bthe\s+words?\s+(.+)$", c.raw, re.I)
    if words:
        return {"action": "delete_text", "target_text": unquote(words.group(1))}
    target = c.target()
    if target is None:
        raise Clarify("What should I remove? Quote the text, describe the paragraph (e.g. “the paragraph about pricing”), "
                      "or click it in the preview.")
    if c.pptx:
        return {"action": "delete_text", "target": target}
    if target["type"] == "bullet":
        raise Clarify("In Word documents, tell me which paragraph to remove by quoting a few of its words.")
    return {"action": "delete_paragraph", "target": target}


def _anchor(phrase: str) -> Dict[str, Any]:
    phrase = unquote(re.sub(r"\s+(section|heading|paragraph|part)$", "", phrase.strip(" .")))
    number = re.fullmatch(r"(?:paragraph\s*)?(\d+)", phrase)
    if number:
        return {"type": "paragraph", "index": int(number.group(1))}
    if phrase.lower() in ("title", "the title"):
        return {"type": "title"}
    about = ABOUT_RE.search(phrase)
    if about:
        return {"type": "paragraph", "text": unquote(about.group(1))}
    return {"type": "heading", "text": phrase}


def add_command(c: Clause) -> Dict[str, Any]:
    text = c.text_value()
    head = c.raw
    said = re.search(r"\s+(?:saying|that says|reading|with the text|with text)\s+.+$", head, re.I)
    if said:
        head = head[:said.start()]
    head = re.sub(r"\s*“[^”]*”\s*$", "", head) if not c.payload else head
    if c.pptx:
        if not text:
            raise Clarify("What should the new bullet say? For example “Add a bullet to slide 3: Faster onboarding”.")
        command: Dict[str, Any] = {"action": "add_text", "target": {"type": "slide", "slide": c.slide or c.ctx.current_slide}, "text": text}
        after = re.search(r"\b(after|before)\s+(?:the\s+)?(\w+)\s+(?:bullet|point)", head.lower())
        index = ordinal_before(head.lower(), "(?:bullet|point)") if after else None
        if after and index:
            command["position"] = {"where": after.group(1), "anchor": {"type": "bullet", "index": index, "slide": command["target"]["slide"]}}
        return command
    if not text:
        raise Clarify("What text should I add? For example “Add this paragraph after the executive summary: …”.")
    into = re.search(r"\bto\s+(?:the\s+)?(end|start|beginning)?\s*(?:of\s+(?:the\s+)?)?(title|subtitle|paragraph\s+\d+)\b", head.lower())
    if into:
        kind = into.group(2)
        target = {"type": "paragraph", "index": int(kind.split()[-1])} if kind.startswith("paragraph") else {"type": kind}
        where = "start" if into.group(1) in ("start", "beginning") else "end"
        return {"action": "insert_text", "target": target, "text": text, "position": {"where": where}}
    anchor = re.search(r"\b(after|below|under|following|before|above)\s+(?:the\s+)?(.+?)$", head, re.I)
    if anchor:
        where = "before" if anchor.group(1).lower() in ("before", "above") else "after"
        return {"action": "insert_paragraph", "text": text, "position": {"where": where, "anchor": _anchor(anchor.group(2))}}
    where = "start" if re.search(r"\b(start|beginning|top)\b", head.lower()) else "end"
    return {"action": "insert_paragraph", "text": text, "position": {"where": where}}


def _looks_like_style(value: str) -> bool:
    """'Arial, 32 points' or 'blue' are formatting; 'Quarterly Review' is new title text."""
    low = value.lower()
    if find_font(value) or find_size(value) or re.search(r"\b(bold|italic|underlined?|bigger|smaller)\b", low):
        return True
    return bool(find_color(value)) and len(low.split()) <= 3


def text_update_command(c: Clause) -> Optional[Dict[str, Any]]:
    match = re.search(r"\b(?:change|rename|set|update|make)\s+(?:the\s+)?(?:text\s+of\s+(?:the\s+)?)?(title|subtitle)"
                      r"(?:\s+(?:text|on\s+slide\s*\d+|of\s+slide\s*\d+|of\s+the\s+\w+))*\s+(?:text\s+)?to\s+(.+)$", c.raw, re.I)
    if c.payload and c.has(r"\b(change|rename|set|update)\b") and c.has(r"\b(title|subtitle)\b"):
        value, quoted = c.payload, True
    elif match:
        value = unquote(match.group(2))
        quoted = match.group(2).strip().startswith(("“", '"', "'"))
    else:
        return None
    if not quoted and _looks_like_style(value):
        return None
    kind = "subtitle" if c.has(r"\bsub-?title\b") else "title"
    return {"action": "update_text", "target": c.with_slide({"type": kind}), "text": value}


def style_command(c: Clause) -> Optional[Dict[str, Any]]:
    masked = c.masked
    changes: Dict[str, Any] = {}
    font, size, color = find_font(masked), find_size(masked), find_color(masked)
    if font:
        changes["font_family"] = font
    if size:
        changes["font_size"] = size
    if color:
        changes["color"] = color
    for key in ("bold", "italic", "underline"):
        value = find_toggle(c.low, key)
        if value is not None:
            changes[key] = value
    align = find_align(c.low)
    if align:
        changes["align"] = align
    target = c.target()
    if not changes:
        about = f" for {describe_target(target)}" if target else ""
        if c.has(r"\bfont\s+size\b|\bsize\b|\bbigger\b|\bsmaller\b"):
            raise Clarify(f"What size (in points) should I use{about}? For example “24 pt”.")
        if c.has(r"\bcolou?r\b"):
            raise Clarify(f"Which colour should I use{about}? For example blue, dark red or #1F4E79.")
        if c.has(r"\b(font|typeface)\b"):
            if target is None:
                raise Clarify(which_text_question(c.ctx.doc_type))
            raise Clarify(f"Which font should I use{about}? For example Arial, Georgia or Calibri.")
        return None
    if target is None:
        raise Clarify(which_text_question(c.ctx.doc_type))
    return {"action": "update_style", "target": target, "changes": changes}

