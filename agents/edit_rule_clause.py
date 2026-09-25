"""
Clause model for the rule-based edit parser: shared patterns, the parse context/result types,
and `Clause`, which finds the target ("the title", "bullet 3 on slide 2", "this", "it") of one instruction.
"""
import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.edit_rules_vocab import ordinal_before, slide_number

QUOTE_RE = re.compile(r'"([^"]+)"|“([^”]+)”|‘([^’]+)’|(?<![\w])\'([^\']+)\'(?![\w])')
VERBS = r"(?:make|set|change|remove|delete|add|insert|replace|move|resize|scale|put|increase|decrease|center|align|use|shrink|enlarge)"
CLAUSE_SPLIT = re.compile(rf"\s*(?:;|\.\s+|,?\s+and\s+(?=(?:then\s+|also\s+)?{VERBS}\b)|,?\s+then\s+|,\s+(?={VERBS}\b))\s*", re.I)
ABOUT_RE = re.compile(r"\b(?:paragraph|line|sentence|text|bullet|point|section)\s+(?:about|containing|mentioning|regarding|"
                      r"on|that\s+(?:says|mentions|talks\s+about|starts\s+with|contains|begins\s+with)|with|saying)\s+(.+)$", re.I)
PAYLOAD_VERBS = re.compile(r"\b(add|insert|append|replace|change|rename|set|write|put|update)\b", re.I)


class Clarify(Exception):
    def __init__(self, question: str):
        super().__init__(question)
        self.question = question


@dataclass
class ParseContext:
    doc_type: str
    selection_kind: Optional[str] = None      # "paragraph" | "shape" | "image" when something is selected
    current_slide: int = 1
    last_target: Optional[Dict[str, Any]] = None
    outline: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ParseResult:
    commands: List[Dict[str, Any]]
    clarification: Optional[str] = None
    parser: str = "rules"
    note: Optional[str] = None


def unquote(text: str, keep_period: bool = False) -> str:
    """Strips surrounding quotes. A trailing full stop is sentence punctuation, unless it is the payload."""
    text = text.strip()
    if not keep_period and text.endswith(".") and not text.endswith(".."):
        text = text[:-1].strip()
    match = QUOTE_RE.fullmatch(text)
    return next(g for g in match.groups() if g) if match else text


def which_text_question(doc_type: str) -> str:
    if doc_type == "pptx":
        return "Which text would you like to change: the title on this slide, the bullets, or all text in the presentation?"
    return "Which text would you like to change: the title, headings, body text, or the entire document?"


class Clause:
    """One instruction, with quoted strings masked (⟦0⟧) so they don't confuse keyword matching."""

    def __init__(self, masked: str, quotes: List[str], payload: Optional[str], ctx: ParseContext,
                 prev_target: Optional[Dict[str, Any]]):
        self.masked = masked.strip(" .!?\n")
        self.low = self.masked.lower()
        self.quotes = [quotes[int(i)] for i in re.findall(r"⟦(\d+)⟧", masked)]
        self.raw = re.sub(r"⟦(\d+)⟧", lambda m: f"“{quotes[int(m.group(1))]}”", self.masked)
        self.payload, self.ctx, self.prev_target = payload, ctx, prev_target
        self.slide = slide_number(self.low)
        self.pptx = ctx.doc_type == "pptx"

    def has(self, pattern: str) -> bool:
        return re.search(pattern, self.low) is not None

    def text_value(self) -> Optional[str]:
        if self.payload:
            return self.payload
        match = re.search(r"\b(?:saying|that says|reading|with the text|with text)\s+(.+)$", self.raw, re.I)
        if match:
            return unquote(match.group(1))
        return self.quotes[-1] if self.quotes else None

    def with_slide(self, target: Dict[str, Any]) -> Dict[str, Any]:
        if self.pptx and self.slide and target.get("type") not in ("selection", "document"):
            return {**target, "slide": self.slide}
        return target

    def target(self) -> Optional[Dict[str, Any]]:
        low = self.low
        if self.ctx.selection_kind and self.has(r"\b(this|selected|highlighted)\b"):
            return {"type": "selection"}
        if self.has(r"\b(it|them|its)\b") and self.prev_target:
            return copy.deepcopy(self.prev_target)
        about = ABOUT_RE.search(self.raw)
        if about:
            phrase = unquote(re.sub(r"\s+(section|paragraph|part)$", "", about.group(1).strip(" .")))
            return self.with_slide({"type": "paragraph", "text": phrase})
        if self.has(r"\bsub-?title\b"):
            return self.with_slide({"type": "subtitle"})
        if self.has(r"\btitle\b") and not self.has(r"\bsection titles?\b"):
            return self.with_slide({"type": "title"})
        named = re.search(r"\bthe\s+((?:(?!the\b|first\b|second\b|third\b|last\b|main\b|all\b)[a-z0-9&\-]+\s+){1,5}?)(?:heading|section)\b", low)
        if named:
            return {"type": "heading", "text": named.group(1).strip()}
        if self.quotes and self.has(r"⟦\d+⟧\s+(heading|section)"):
            return {"type": "heading", "text": self.quotes[0]}
        if self.has(r"\b(headings?|section titles?)\b"):
            index = ordinal_before(low, "headings?")
            return {"type": "heading", "index": index} if index else {"type": "headings"}
        if self.has(r"\b(bullets?|points?|items?)\b") and self.pptx:
            index = ordinal_before(low, r"(?:bullet|point|item)s?")
            return self.with_slide({"type": "bullet", "index": index} if index else {"type": "bullet"})
        if self.has(r"\bparagraphs?\b") and ordinal_before(low, "paragraph"):
            return self.with_slide({"type": "paragraph", "index": ordinal_before(low, "paragraph")})
        if self.has(r"\b(entire|whole|all)\s+(?:the\s+)?(document|text|presentation|deck|slides)\b|\beverything\b|\ball text\b"):
            return {"type": "document"}
        if self.has(r"\b(body|body text|normal text|paragraphs)\b"):
            return self.with_slide({"type": "body"})
        if self.pptx and self.slide and self.has(r"\b(text|font|everything)\b"):
            return {"type": "slide", "slide": self.slide}
        if self.quotes:
            return {"type": "text", "text": self.quotes[0]}
        return None
