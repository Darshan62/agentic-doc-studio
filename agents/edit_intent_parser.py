"""
Edit Intent Parser Agent: natural language -> structured edit commands.

Gemini only translates the request into JSON that follows core/edit_schema.py; it never sees
or touches the file itself. Its answer is validated, and if Gemini is unavailable, slow, or
returns anything invalid, the deterministic rule parser takes over.

EDIT_PARSER=auto (default: Gemini, falling back to rules) | gemini | rules
"""
import copy
import json
import os
from typing import Any, Dict, List

from agents.edit_rule_parser import ParseContext, ParseResult, parse_rules
from core.edit_schema import ACTIONS, EditError, validate_command
from core.gemini_client import GeminiError, ask_gemini_json

PARSE_TIMEOUT_SECONDS = 25
HISTORY_TURNS = 4
MAX_COMMANDS = 6

SCHEMA_HELP = """Each command is a JSON object:
{"action": <action>, "target": {"type": <type>, "text": str|null, "index": int|null, "slide": int|null},
 "changes": {"font_family": str|null, "font_size": number|null, "bold": bool|null, "italic": bool|null,
             "underline": bool|null, "color": "blue"|"#1F4E79"|null, "align": "left"|"center"|"right"|"justify"|null},
 "text": str, "target_text": str, "replacement_text": str,
 "position": {"where": "after"|"before"|"start"|"end", "anchor": <target>},
 "scale": number, "move": {"dx_inches": number, "dy_inches": number} or {"to": "top-left"|"top-right"|"bottom-left"|"bottom-right"|"center"},
 "image_source": "last_upload"}
Target types: title, subtitle, heading (with text or index), headings (all), body, document (all text),
paragraph (index = the ¶ number in the outline, or text = words it contains), text (an exact phrase),
bullet (pptx: index within the slide, -1 = last), slide (pptx: all text on a slide), logo, image (index),
selection (whatever the user clicked in the preview; use for "this"/"selected").
Action rules:
- update_style: needs target + changes (only the properties the user asked for; others null).
- update_text: replace the whole text of the target with "text".
- replace_text: "target_text" -> "replacement_text" (optional target to limit the scope).
- delete_text: remove "target_text", or (pptx) remove the target bullet/paragraph.
- delete_paragraph (docx): remove the target paragraph.
- insert_paragraph (docx): "text" + "position" (anchor = the heading/paragraph to insert after/before).
- insert_text (docx): append "text" to the target paragraph (position where start/end).
- add_text (pptx): add a bullet with "text" to target {"type":"slide","slide":N}.
- delete_slide (pptx): target {"type":"slide","slide":N}.
- replace_image: target logo/image; the new picture is the one the user uploaded ("image_source":"last_upload").
- resize_image: "scale" relative to the current size (80% -> 0.8, smaller -> 0.8, bigger -> 1.25).
- move_image (pptx only): dx/dy in inches (right/down positive; "slightly" = 0.25).
Font sizes are in points."""

EXAMPLES = """Examples:
"Change the title font to Arial and make it bold" -> {"commands":[{"action":"update_style","target":{"type":"title"},"changes":{"font_family":"Arial","bold":true}}],"clarification":null}
"Remove the paragraph about pricing" -> {"commands":[{"action":"delete_paragraph","target":{"type":"paragraph","text":"pricing"}}],"clarification":null}
"Add this after the executive summary: We deliver in 12 weeks." -> {"commands":[{"action":"insert_paragraph","text":"We deliver in 12 weeks.","position":{"where":"after","anchor":{"type":"heading","text":"Executive Summary"}}}],"clarification":null}
"Remove the third bullet from slide 2" -> {"commands":[{"action":"delete_text","target":{"type":"bullet","index":3,"slide":2}}],"clarification":null}
"Resize the logo on slide 1 to 80%" -> {"commands":[{"action":"resize_image","target":{"type":"logo","slide":1},"scale":0.8}],"clarification":null}
"Change the font" -> {"commands":[],"clarification":"Which text would you like to change: the title, headings, body text, or the entire document?"}"""


def build_prompt(message: str, ctx: ParseContext) -> str:
    doc_label = "Word document (docx)" if ctx.doc_type == "docx" else "PowerPoint presentation (pptx)"
    history = "\n".join(f"{m['role']}: {m['text'][:300]}" for m in ctx.history[-HISTORY_TURNS:]) or "(none)"
    selection = f"The user has selected a {ctx.selection_kind} in the preview." if ctx.selection_kind else "Nothing is selected."
    return (
        f"You convert a user's request to edit the open {doc_label} into JSON edit commands.\n"
        "Never write code. Only output JSON. Use only the actions allowed for this document type: "
        f"{', '.join(sorted(ACTIONS[ctx.doc_type]))}.\n"
        "If the request is ambiguous (missing target, missing value, or several things could match), "
        "return no commands and ask ONE short clarification question instead of guessing.\n"
        "If the request is not about editing the document, return no commands and a short helpful answer "
        "in \"clarification\".\n\n"
        f"{SCHEMA_HELP}\n\n{EXAMPLES}\n\n"
        f"DOCUMENT OUTLINE:\n{ctx.outline[:6000]}\n\n"
        f"CONTEXT: current slide = {ctx.current_slide}. {selection} "
        f"Previous edit target (for 'it'): {json.dumps(ctx.last_target)}.\n"
        f"RECENT CONVERSATION:\n{history}\n\n"
        f"USER REQUEST: {message}\n\n"
        'Return JSON: {"commands": [...], "clarification": null or "question"}'
    )


def check_commands(raw: Any, doc_type: str) -> List[Dict[str, Any]]:
    """Structural check of Gemini's commands; the workspace validates again after resolving selections."""
    if not isinstance(raw, list) or len(raw) > MAX_COMMANDS:
        raise EditError("Gemini returned an unexpected command list.")
    commands = []
    for item in raw:
        if not isinstance(item, dict):
            raise EditError("Gemini returned a malformed command.")
        cmd = {k: v for k, v in item.items() if v is not None}
        if isinstance(cmd.get("target"), dict):
            cmd["target"] = {k: v for k, v in cmd["target"].items() if v is not None}
        if isinstance(cmd.get("changes"), dict):
            cmd["changes"] = {k: v for k, v in cmd["changes"].items() if v is not None}
        validate_command(copy.deepcopy(cmd), doc_type)
        commands.append(cmd)
    return commands


def parse_with_gemini(message: str, ctx: ParseContext) -> ParseResult:
    answer = ask_gemini_json(build_prompt(message, ctx), timeout=PARSE_TIMEOUT_SECONDS, fast=True)
    if not isinstance(answer, dict):
        raise EditError("Gemini returned an unexpected answer.")
    commands = check_commands(answer.get("commands") or [], ctx.doc_type)
    question = answer.get("clarification")
    if not commands:
        if not isinstance(question, str) or not question.strip():
            raise EditError("Gemini returned neither commands nor a question.")
        return ParseResult([], clarification=question.strip()[:500], parser="gemini")
    return ParseResult(commands, parser="gemini")


def parse_edit_request(message: str, ctx: ParseContext) -> ParseResult:
    mode = os.environ.get("EDIT_PARSER", "auto").strip().lower()
    has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    if mode == "rules" or not has_key:
        result = parse_rules(message, ctx)
        if mode != "rules":
            result.note = "Gemini is not configured, so the built-in parser handled this request."
        return result
    try:
        result = parse_with_gemini(message, ctx)
    except (GeminiError, EditError, ValueError, KeyError, TypeError) as e:
        if mode == "gemini":
            return ParseResult([], clarification=f"Gemini could not interpret that request ({e}).", parser="gemini")
        fallback = parse_rules(message, ctx)
        fallback.note = f"Gemini was unavailable or returned an invalid command ({e}); the built-in parser was used."
        return fallback
    if result.clarification and mode == "auto":
        # The rule parser never guesses, so if it is certain we can act instead of asking
        rules = parse_rules(message, ctx)
        if rules.commands:
            rules.note = "Gemini asked for clarification, but the request matched a known pattern exactly."
            return rules
    return result
